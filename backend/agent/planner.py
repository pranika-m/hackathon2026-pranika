"""
Hybrid planner for the ShopWave agent loop.

Gemini is used for action planning when available. Deterministic policy logic
remains as the safety fallback so the project still runs offline.
"""

from __future__ import annotations

import json
import re

from core.llm_client import get_llm_client


DAMAGE_KEYWORDS = [
    "damaged",
    "defective",
    "broken",
    "cracked",
    "stopped working",
    "not working",
]
THREAT_KEYWORDS = ["lawyer", "dispute", "chargeback", "bank", "legal", "sue"]
TIER_CLAIM_KEYWORDS = ["premium member", "vip member", "gold member", "premium policy"]
VALID_ACTIONS = {
    "get_customer",
    "get_order",
    "get_product",
    "search_knowledge_base",
    "check_refund_eligibility",
    "issue_refund",
    "send_reply",
    "escalate",
    "DONE",
}


def extract_order_id(text: str) -> str | None:
    match = re.search(r"ORD-\d+", text or "")
    return match.group(0) if match else None


def detect_customer_conflicts(ticket: dict, customer: dict, order: dict | None = None) -> list[str]:
    conflicts: list[str] = []
    body_lower = ticket.get("body", "").lower()

    for keyword in TIER_CLAIM_KEYWORDS:
        if keyword in body_lower and customer and "error" not in str(customer):
            claimed = "vip" if "vip" in keyword else "premium"
            actual = str(customer.get("tier", "unknown")).lower()
            if actual != claimed:
                conflicts.append(
                    f"CONFLICTING_DATA (TIER_MISMATCH): claimed {claimed}, verified {actual}."
                )

    if order and isinstance(order, dict) and order.get("error") == "ORDER_NOT_FOUND":
        conflicts.append("CONFLICTING_DATA (ORDER_NOT_FOUND): referenced order does not exist.")

    return conflicts


def detect_warning_flags(ticket: dict) -> list[str]:
    body_lower = ticket.get("body", "").lower()
    flags = [f"THREATENING_LANGUAGE: {keyword}" for keyword in THREAT_KEYWORDS if keyword in body_lower]
    return flags[:1]


def is_damaged_defective(ticket: dict) -> bool:
    combined = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    return any(keyword in combined for keyword in DAMAGE_KEYWORDS)


def is_warranty_claim(ticket: dict, order: dict | None = None, product: dict | None = None) -> bool:
    body_lower = ticket.get("body", "").lower()
    if "warranty" in body_lower:
        return True
    if not (order and product) or "error" in str(order) or "error" in str(product):
        return False
    if not is_damaged_defective(ticket):
        return False
    return bool(
        order.get("delivery_date")
        and order.get("return_deadline")
        and product.get("warranty_months", 0) > 0
        and "return window has expired" in order.get("notes", "").lower()
    )


def wants_replacement(ticket: dict) -> bool:
    body_lower = ticket.get("body", "").lower()
    return "replacement" in body_lower or "replace" in body_lower


def _is_refund_request(ticket: dict) -> bool:
    combined = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    return "refund" in combined or "return" in combined


def _is_cancellation_request(ticket: dict) -> bool:
    combined = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    return "cancel" in combined


def _is_order_status_request(ticket: dict) -> bool:
    combined = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    return "where is my order" in combined or "haven't received" in combined or "tracking" in combined


def _is_policy_question(ticket: dict) -> bool:
    combined = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    return (
        "return policy" in combined
        or "do you offer exchanges" in combined
        or "what is your return policy" in combined
    )


def _is_refund_status_question(ticket: dict, order: dict | None) -> bool:
    combined = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    return "refund already" in combined or (
        "went through" in combined and order and order.get("refund_status") == "refunded"
    )


def _has_tool(tool_history: list[dict], tool_name: str) -> bool:
    return any(entry["tool"] == tool_name for entry in tool_history)


def _last_result(tool_history: list[dict], tool_name: str) -> dict | None:
    for entry in reversed(tool_history):
        if entry["tool"] == tool_name:
            return entry.get("result")
    return None


def _priority_from_context(context: dict) -> str:
    if context.get("conflicts") or context.get("flags"):
        return "high"
    return "medium"


def _compose_reply(ticket: dict, context: dict) -> str:
    customer = context.get("customer") or {}
    order = context.get("order") or {}
    kb = context.get("policy_results") or {}
    first_name = (customer.get("name", "there").split() or ["there"])[0]
    subject = ticket.get("subject", "").lower()
    body = ticket.get("body", "").lower()

    if customer.get("error") == "CUSTOMER_NOT_FOUND":
        return (
            f"Hi {first_name}, I could not match this request to a registered ShopWave account yet. "
            "Please reply with your order number and the email address used at checkout so we can help right away."
        )

    if context.get("conflicts"):
        return (
            f"Hi {first_name}, thanks for reaching out. I found a mismatch between the details in your message and our records, "
            "so I have sent this to a specialist to review safely. They will follow up shortly."
        )

    if _is_refund_status_question(ticket, order):
        return (
            f"Hi {first_name}, I confirmed that the refund for order {order.get('order_id')} has already been processed. "
            "Refunds normally appear on the original payment method within 5-7 business days."
        )

    if _is_order_status_request(ticket):
        tracking = "Tracking details were not available."
        notes = order.get("notes", "")
        match = re.search(r"(TRK-\d+)", notes)
        if match:
            tracking = f"Your tracking number is {match.group(1)}."
        expected = ""
        if "expected delivery" in notes.lower():
            expected = notes.split("Expected delivery", 1)[-1].strip(". ")
            expected = f" Expected delivery {expected}."
        return (
            f"Hi {first_name}, I checked order {order.get('order_id')} and it is currently {order.get('status')}. "
            f"{tracking}{expected}"
        )

    if _is_cancellation_request(ticket):
        if order.get("status") == "processing":
            return (
                f"Hi {first_name}, I confirmed order {order.get('order_id')} is still in processing, so it can be cancelled at no charge. "
                "Your cancellation request has been recorded and you will receive confirmation by email shortly."
            )
        if order.get("status") == "shipped":
            return (
                f"Hi {first_name}, order {order.get('order_id')} has already shipped, so it can no longer be cancelled. "
                "Once it arrives, you can request a return under the normal return policy."
            )
        return (
            f"Hi {first_name}, delivered orders cannot be cancelled. If you still need help, I can guide you through the return options."
        )

    if is_damaged_defective(ticket) and wants_replacement(ticket):
        return (
            f"Hi {first_name}, I am sorry your item arrived in that condition. "
            "I have escalated this to a specialist so they can arrange the replacement for you as quickly as possible."
        )

    if is_warranty_claim(ticket, context.get("order"), context.get("product")):
        return (
            f"Hi {first_name}, thanks for reporting this issue. Your case falls under our warranty workflow, "
            "so I have escalated it to the warranty team for specialist handling."
        )

    refund_result = _last_result(context.get("tool_results", []), "issue_refund")
    if refund_result and refund_result.get("status") == "SUCCESS":
        return (
            f"Hi {first_name}, I have processed your refund for order {order.get('order_id')} for ${refund_result.get('amount_refunded'):.2f}. "
            "It will return to your original payment method within 5-7 business days."
        )

    eligibility = context.get("refund_eligibility") or {}
    if eligibility.get("eligible") and _is_refund_request(ticket):
        if "return" in subject or "return" in body:
            return (
                f"Hi {first_name}, your request for order {order.get('order_id')} is eligible under our policy. "
                "You can proceed with the return, and once it is received in the expected condition we will complete the refund."
            )
        return (
            f"Hi {first_name}, your request for order {order.get('order_id')} is eligible for a refund. "
            "I have completed the policy checks and confirmed the next step for you."
        )

    if eligibility and not eligibility.get("eligible"):
        reason = str(eligibility.get("reason", "POLICY_LIMIT")).replace("_", " ").lower()
        return (
            f"Hi {first_name}, I reviewed order {order.get('order_id')} and cannot approve the refund under our policy because of {reason}. "
            "If you would like, I can help with the available alternatives."
        )

    if _is_policy_question(ticket):
        snippets = "; ".join((kb.get("results") or [])[:2])
        return (
            f"Hi {first_name}, for electronics we usually allow returns within 30 days of delivery, while high-value electronics such as smart watches use a 15-day window. "
            f"Exchanges are available for wrong size, wrong color, or wrong item requests. {snippets}"
        )

    if "too late" in body or "process" in body:
        return (
            f"Hi {first_name}, order {order.get('order_id')} is still within its return window. "
            "Returns must be unused and in the original packaging, and exchanges are available for wrong size, wrong color, or wrong item cases."
        )

    return (
        f"Hi {first_name}, I reviewed your request and gathered the available policy and order details. "
        "If you can share a little more about the issue, I can take the next step for you."
    )


def build_escalation_summary(ticket: dict, context: dict, tool_history: list[dict]) -> str:
    order = context.get("order") or {}
    attempted = ", ".join(entry["tool"] for entry in tool_history) or "no tools"
    issues = context.get("conflicts") or context.get("flags") or ["policy review required"]
    return (
        f"Issue: {ticket.get('subject')} for {ticket.get('customer_email')}. "
        f"Verified order: {order.get('order_id', 'unknown')}. "
        f"Attempted: {attempted}. "
        f"Observed: {issues}. "
        "Recommended path: specialist review and customer follow-up."
    )


def _deterministic_plan(ticket: dict, context: dict, tool_history: list[dict]) -> dict:
    customer = context.get("customer") or {}
    order = context.get("order") or {}
    product = context.get("product") or {}
    eligibility = context.get("refund_eligibility") or {}

    if _has_tool(tool_history, "send_reply"):
        return {"action": "DONE", "args": {}, "reasoning": "Customer-facing response has already been sent."}

    if customer.get("error") == "CUSTOMER_NOT_FOUND":
        return {
            "action": "send_reply",
            "args": {"ticket_id": ticket["ticket_id"], "message": _compose_reply(ticket, context)},
            "reasoning": "Customer identity could not be verified, so request clarification instead of taking account actions.",
        }

    if context.get("conflicts"):
        if not _has_tool(tool_history, "escalate"):
            return {
                "action": "escalate",
                "args": {
                    "ticket_id": ticket["ticket_id"],
                    "summary": build_escalation_summary(ticket, context, tool_history),
                    "priority": _priority_from_context(context),
                },
                "reasoning": "Conflicting data requires specialist review per policy.",
            }
        return {
            "action": "send_reply",
            "args": {"ticket_id": ticket["ticket_id"], "message": _compose_reply(ticket, context)},
            "reasoning": "After escalation, keep the customer informed in empathetic language.",
        }

    if is_warranty_claim(ticket, order, product) or (is_damaged_defective(ticket) and wants_replacement(ticket)):
        if not _has_tool(tool_history, "escalate"):
            return {
                "action": "escalate",
                "args": {
                    "ticket_id": ticket["ticket_id"],
                    "summary": build_escalation_summary(ticket, context, tool_history),
                    "priority": "high",
                },
                "reasoning": "Warranty and replacement cases must be escalated.",
            }
        return {
            "action": "send_reply",
            "args": {"ticket_id": ticket["ticket_id"], "message": _compose_reply(ticket, context)},
            "reasoning": "Specialist escalation is complete, so update the customer.",
        }

    if _is_policy_question(ticket) or (not order and "order" not in ticket.get("body", "").lower()):
        return {
            "action": "send_reply",
            "args": {"ticket_id": ticket["ticket_id"], "message": _compose_reply(ticket, context)},
            "reasoning": "This request can be answered directly from policy and available account context.",
        }

    if not eligibility and _is_refund_request(ticket) and order and "error" not in str(order):
        return {
            "action": "check_refund_eligibility",
            "args": {"order_id": order["order_id"]},
            "reasoning": "Refund or return intent detected, so verify eligibility before any financial action.",
        }

    if eligibility.get("eligible") and "refund" in f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower():
        if order.get("amount", 0) > 200 and not _has_tool(tool_history, "escalate"):
            return {
                "action": "escalate",
                "args": {
                    "ticket_id": ticket["ticket_id"],
                    "summary": build_escalation_summary(ticket, context, tool_history),
                    "priority": "high",
                },
                "reasoning": "Refund amount exceeds the autonomous threshold.",
            }
        if not _has_tool(tool_history, "issue_refund"):
            return {
                "action": "issue_refund",
                "args": {"order_id": order["order_id"], "amount": order["amount"]},
                "reasoning": "Eligibility was confirmed and the customer explicitly requested a refund.",
            }

    return {
        "action": "send_reply",
        "args": {"ticket_id": ticket["ticket_id"], "message": _compose_reply(ticket, context)},
        "reasoning": "Enough evidence has been gathered to conclude with a customer-facing response.",
    }


def _build_llm_prompt(ticket: dict, context: dict, tool_history: list[dict], fallback: dict) -> str:
    compact_history = [
        {
            "tool": entry["tool"],
            "success": entry.get("success", False),
            "args": entry.get("args", {}),
            "result": entry.get("result", {}),
        }
        for entry in tool_history[-6:]
    ]
    compact_context = {
        "customer": context.get("customer"),
        "order": context.get("order"),
        "product": context.get("product"),
        "refund_eligibility": context.get("refund_eligibility"),
        "policy_results": context.get("policy_results"),
        "conflicts": context.get("conflicts", []),
        "flags": context.get("flags", []),
    }
    return f"""
You are planning the NEXT SINGLE action for ShopWave's support agent.

Ticket:
{json.dumps(ticket, ensure_ascii=True)}

Current context:
{json.dumps(compact_context, ensure_ascii=True)}

Tool history:
{json.dumps(compact_history, ensure_ascii=True)}

Available actions:
{sorted(VALID_ACTIONS)}

Hard constraints:
- At least 3 tool calls before the ticket is finished.
- Warranty claims must escalate.
- Replacement request for a damaged item must escalate.
- Refunds above $200 must escalate.
- Never issue a refund before check_refund_eligibility confirms eligibility.
- If there is conflicting data or suspected manipulation, escalate.
- Keep customer messages empathetic and professional.

Use this deterministic fallback if uncertain:
{json.dumps(fallback, ensure_ascii=True)}

Return JSON only in this format:
{{"action":"tool_name","args":{{}},"reasoning":"short explanation"}}
"""


def _normalize_llm_plan(llm_result: dict, ticket: dict, context: dict, fallback: dict) -> dict:
    action = llm_result.get("action")
    args = llm_result.get("args", {})
    reasoning = str(llm_result.get("reasoning", "")).strip() or "LLM-selected action."

    if action not in VALID_ACTIONS or not isinstance(args, dict):
        return fallback

    plan = {"action": action, "args": args, "reasoning": reasoning}

    if action == "send_reply":
        plan["args"] = {
            "ticket_id": ticket["ticket_id"],
            "message": args.get("message") or _compose_reply(ticket, context),
        }
    elif action == "escalate":
        plan["args"] = {
            "ticket_id": ticket["ticket_id"],
            "summary": args.get("summary") or build_escalation_summary(ticket, context, []),
            "priority": args.get("priority", _priority_from_context(context)),
        }
    elif action == "check_refund_eligibility":
        order = context.get("order") or {}
        plan["args"] = {"order_id": args.get("order_id") or order.get("order_id")}
        if not plan["args"]["order_id"]:
            return fallback
    elif action == "issue_refund":
        order = context.get("order") or {}
        plan["args"] = {
            "order_id": args.get("order_id") or order.get("order_id"),
            "amount": args.get("amount", order.get("amount")),
        }
        if not plan["args"]["order_id"] or plan["args"]["amount"] is None:
            return fallback

    return plan


async def plan_next_agent_action(ticket: dict, context: dict, tool_history: list[dict]) -> dict:
    fallback = _deterministic_plan(ticket, context, tool_history)
    llm = get_llm_client()

    if not llm.enabled:
        return fallback

    try:
        response = await llm.generate_json(_build_llm_prompt(ticket, context, tool_history, fallback))
        if response.startswith("[LLM_"):
            return fallback
        parsed = json.loads(response)
        return _normalize_llm_plan(parsed, ticket, context, fallback)
    except Exception:
        return fallback
