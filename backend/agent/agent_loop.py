"""
ReAct-style orchestration for ShopWave support tickets.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agent.evaluator import apply_automatic_score_deductions, score_resolution_confidence
from agent.executor import ToolExecutor
from agent.planner import (
    build_escalation_summary,
    detect_customer_conflicts,
    detect_warning_flags,
    extract_order_id,
    is_damaged_defective,
    is_warranty_claim,
    plan_next_agent_action,
    wants_replacement,
)
from core.dead_letter_queue import get_dead_letter_queue
from core.logger import get_audit_logger
from core.state_manager import TicketState, get_state_manager


MAX_REACT_ITERATIONS = 8
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_orders() -> list[dict]:
    with (DATA_DIR / "orders.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _infer_order_id(ticket: dict, customer: dict) -> str | None:
    explicit = extract_order_id(ticket.get("body", ""))
    if explicit:
        return explicit

    if not customer or "error" in str(customer):
        return None

    orders = [entry for entry in _load_orders() if entry["customer_id"] == customer.get("customer_id")]
    if not orders:
        return None

    wants_cancel = "cancel" in f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    if wants_cancel:
        processing = next((entry for entry in orders if entry.get("status") == "processing"), None)
        if processing:
            return processing["order_id"]

    orders.sort(key=lambda entry: entry.get("order_date", ""), reverse=True)
    return orders[0]["order_id"]


async def process_single_ticket_lifecycle(ticket: dict) -> None:
    ticket_id = ticket["ticket_id"]
    logger = get_audit_logger()
    state_mgr = get_state_manager()
    dlq = get_dead_letter_queue()
    executor = ToolExecutor(ticket_id)

    try:
        state_mgr.init_ticket(ticket_id)
        logger.init_ticket(ticket_id, ticket["customer_email"], ticket["subject"])
        state_mgr.set_context(ticket_id, "ticket", ticket)
        logger.log_reasoning(ticket_id, "INGEST", f"Ingested ticket '{ticket['subject']}'.")

        customer_result = await executor.execute_tool_with_retry(
            "get_customer", {"email": ticket["customer_email"]}
        )
        state_mgr.set_context(ticket_id, "customer", customer_result)
        if "error" not in str(customer_result):
            logger.set_refs(ticket_id, customer_ref=customer_result.get("customer_id"))
            logger.log_reasoning(
                ticket_id,
                "CUSTOMER_LOADED",
                f"Loaded customer tier {customer_result.get('tier')} for {customer_result.get('name')}.",
            )
        else:
            logger.log_reasoning(ticket_id, "CUSTOMER_NOT_FOUND", str(customer_result))

        inferred_order_id = _infer_order_id(ticket, customer_result)
        if inferred_order_id and not extract_order_id(ticket.get("body", "")):
            logger.log_reasoning(
                ticket_id,
                "ORDER_INFERRED",
                f"No explicit order ID found; inferred {inferred_order_id} from the registered customer history.",
            )

        order_result = None
        product_result = None
        if inferred_order_id:
            order_result = await executor.execute_tool_with_retry(
                "get_order", {"order_id": inferred_order_id}
            )
            state_mgr.set_context(ticket_id, "order", order_result)
            if "error" not in str(order_result):
                logger.set_refs(ticket_id, order_ref=order_result.get("order_id"))
                if order_result.get("product_id"):
                    product_result = await executor.execute_tool_with_retry(
                        "get_product", {"product_id": order_result["product_id"]}
                    )
                    state_mgr.set_context(ticket_id, "product", product_result)
                    if "error" not in str(product_result):
                        logger.set_refs(ticket_id, product_ref=product_result.get("product_id"))

        policy_result = await executor.execute_tool_with_retry(
            "search_knowledge_base",
            {"query": f"{ticket['subject']} {ticket['body'][:180]}"},
        )
        state_mgr.set_context(ticket_id, "policy_results", policy_result)

        conflicts = detect_customer_conflicts(ticket, customer_result, order_result)
        flags = detect_warning_flags(ticket)
        for item in conflicts:
            state_mgr.add_conflict(ticket_id, item)
        for item in flags:
            state_mgr.add_flag(ticket_id, item)

        state_mgr.transition(ticket_id, TicketState.CONTEXT_LOADED)
        state_mgr.transition(ticket_id, TicketState.PLANNED)
        state_mgr.transition(ticket_id, TicketState.EXECUTING)

        if is_warranty_claim(ticket, order_result, product_result):
            logger.log_reasoning(ticket_id, "WARRANTY", "Policy requires warranty claims to be escalated.")
        if is_damaged_defective(ticket) and wants_replacement(ticket):
            logger.log_reasoning(ticket_id, "REPLACEMENT", "Replacement request detected for a damaged or defective item.")

        for iteration in range(MAX_REACT_ITERATIONS):
            context = state_mgr.get_context(ticket_id)
            context["tool_results"] = executor.get_history()
            plan = await plan_next_agent_action(ticket, context, executor.get_history())
            action = plan.get("action", "DONE")
            args = plan.get("args", {})
            logger.log_reasoning(ticket_id, f"REACT_STEP_{iteration + 1}", plan.get("reasoning", ""))

            if action in {"DONE", "ESCALATE"}:
                if not executor.has_minimum_calls_made():
                    await executor.execute_tool_with_retry(
                        "search_knowledge_base", {"query": ticket["subject"]}
                    )
                if not executor.has_minimum_calls_made():
                    await executor.execute_tool_with_retry(
                        "send_reply",
                        {
                            "ticket_id": ticket_id,
                            "message": "Hi there, we reviewed your request and will follow up shortly.",
                        },
                    )
                break

            result = await executor.execute_tool_with_retry(action, args)

            if action == "get_customer" and "error" not in str(result):
                state_mgr.set_context(ticket_id, "customer", result)
            elif action == "get_order":
                state_mgr.set_context(ticket_id, "order", result)
            elif action == "get_product":
                state_mgr.set_context(ticket_id, "product", result)
            elif action == "check_refund_eligibility":
                state_mgr.set_context(ticket_id, "refund_eligibility", result)

        context = state_mgr.get_context(ticket_id)
        context["tool_results"] = executor.get_history()
        llm_score = await score_resolution_confidence(ticket, context, executor.get_history())
        final_score = apply_automatic_score_deductions(llm_score, context)
        logger.set_confidence(ticket_id, final_score)
        logger.log_reasoning(
            ticket_id,
            "CONFIDENCE",
            f"Base confidence {llm_score:.2f}, final confidence {final_score:.2f}.",
        )

        escalated = any(entry["tool"] == "escalate" and entry.get("success") for entry in executor.get_history())
        if final_score < 0.6 and not escalated:
            await executor.execute_tool_with_retry(
                "escalate",
                {
                    "ticket_id": ticket_id,
                    "summary": build_escalation_summary(ticket, context, executor.get_history()),
                    "priority": "high" if final_score < 0.4 else "medium",
                },
            )
            escalated = True

        decision = "ESCALATED" if escalated else "RESOLVED"
        finalize_ticket_and_flush_logs(ticket_id, executor, decision, logger, state_mgr)

    except Exception as exc:
        logger.log_error(ticket_id, "UNHANDLED_ERROR", str(exc))
        state_mgr.transition(ticket_id, TicketState.FAILED)
        state_mgr.transition(ticket_id, TicketState.DEAD_LETTER)
        dlq.add(
            ticket_id=ticket_id,
            reason=str(exc),
            last_state="FAILED",
            attempted_actions=[entry["tool"] for entry in executor.get_history()],
            context=state_mgr.get_context(ticket_id),
        )
        logger.set_decision(ticket_id, "DEAD_LETTER")
        logger.flush_to_disk()


def finalize_ticket_and_flush_logs(
    ticket_id: str,
    executor: ToolExecutor,
    decision: str,
    logger,
    state_mgr,
) -> None:
    escalation_summary = None
    reply = None
    for entry in executor.get_history():
        if entry["tool"] == "escalate" and entry.get("success"):
            escalation_summary = entry["result"].get("summary")
        if entry["tool"] == "send_reply" and entry.get("success"):
            reply = entry["result"].get("message")

    state_mgr.transition(ticket_id, TicketState.ESCALATED if decision == "ESCALATED" else TicketState.RESOLVED)
    logger.set_decision(ticket_id, decision, escalation_summary=escalation_summary, reply=reply)
    logger.flush_to_disk()


async def run_batch_ticket_processing(tickets: list[dict]) -> None:
    tasks = [process_single_ticket_lifecycle(ticket) for ticket in tickets]
    await asyncio.gather(*tasks, return_exceptions=True)
    get_audit_logger().flush_to_disk()
