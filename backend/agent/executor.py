"""
executor.py — runs tool calls with retry/backoff, enforces minimum 3 calls per ticket.
"""

import time
import asyncio
from core.retry_handler import retry_with_backoff, RetryExhausted
from core.validator import validate_tool_output
from core.logger import get_audit_logger
from tools.read_tools import get_customer, get_order, get_product, search_knowledge_base
from tools.write_tools import (
    check_refund_eligibility, issue_refund, send_reply, escalate,
    RefundGuardError, EscalationRequired
)

# =========================
# [TOOL REGISTRY]
# =========================

TOOL_MAP = {
    "get_customer": get_customer,
    "get_order": get_order,
    "get_product": get_product,
    "search_knowledge_base": search_knowledge_base,
    "check_refund_eligibility": check_refund_eligibility,
    "issue_refund": issue_refund,
    "send_reply": send_reply,
    "escalate": escalate,
}

# Tag mapping for audit log — MUST MATCH CODE EXACTLY
TAG_MAP = {
    "get_customer": "FETCH_CUSTOMER",
    "get_order": "FETCH_ORDER",
    "get_product": "FETCH_PRODUCT",
    "search_knowledge_base": "SEARCH_POLICY",
    "check_refund_eligibility": "CHECK_REFUND",
    "issue_refund": "ISSUE_REFUND",
    "send_reply": "SEND_REPLY",
    "escalate": "ESCALATE",
}


# =========================
# [TOOL EXECUTOR]
# =========================

class ToolExecutor:
    """Executes tool calls with retry logic, validation, and audit logging."""

    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id
        self.call_count = 0
        self.tool_history = []  # List of {tool, args, result, success}
        self.logger = get_audit_logger()

    async def execute_tool_with_retry(self, tool_name: str, args: dict) -> dict:
        """
        Execute a single tool call with retry and backoff.
        Validates the output and logs to the audit trail.
        """
        if tool_name not in TOOL_MAP:
            error = {"error": f"Unknown tool: {tool_name}"}
            self.tool_history.append({
                "tool": tool_name, "args": args,
                "result": error, "success": False
            })
            return error

        func = TOOL_MAP[tool_name]
        tag = TAG_MAP.get(tool_name, tool_name.upper())
        start_time = time.time()

        # Retry callback for logging with the standardized RETRY tag
        def on_retry_event(attempt, backoff, error):
            self.logger.log_retry(
                self.ticket_id, tool_name, attempt, backoff, error
            )

        try:
            # Execute with retry and backoff logic
            result = await retry_with_backoff(
                func,
                kwargs=args,
                max_retries=3,
                timeout=5.0,
                on_retry=on_retry_event
            )

            duration_ms = (time.time() - start_time) * 1000

            # Validate the output against Pydantic schemas
            is_valid, error_msg, validated = validate_tool_output(tool_name, result)
            if not is_valid:
                self.logger.log_error(self.ticket_id, "VALIDATION_ERROR", error_msg)
                self.logger.log_tool_call(
                    self.ticket_id, tag, tool_name,
                    args, {"validation_error": error_msg},
                    success=False, duration_ms=duration_ms
                )
                result_entry = {"error": "VALIDATION_ERROR", "details": error_msg, "raw": result}
                self.tool_history.append({
                    "tool": tool_name, "args": args,
                    "result": result_entry, "success": False
                })
                self.call_count += 1
                return result_entry

            # Success path
            self.logger.log_tool_call(
                self.ticket_id, tag, tool_name,
                args, validated if validated else result,
                success=True, duration_ms=duration_ms
            )
            self.call_count += 1
            self.tool_history.append({
                "tool": tool_name, "args": args,
                "result": validated if validated else result, "success": True
            })
            return validated if validated else result

        except RetryExhausted as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_error(self.ticket_id, "TIMEOUT", str(e))
            self.logger.log_tool_call(
                self.ticket_id, tag, tool_name,
                args, {"error": "RETRY_EXHAUSTED", "details": str(e)},
                success=False, duration_ms=duration_ms
            )
            self.call_count += 1
            error_result = {"error": "RETRY_EXHAUSTED", "tool": tool_name, "details": str(e)}
            self.tool_history.append({
                "tool": tool_name, "args": args,
                "result": error_result, "success": False
            })
            return error_result

        except RefundGuardError as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_error(self.ticket_id, "REFUND_GUARD", str(e))
            self.logger.log_tool_call(
                self.ticket_id, tag, tool_name,
                args, {"error": "REFUND_GUARD_BLOCKED", "details": str(e)},
                success=False, duration_ms=duration_ms
            )
            self.call_count += 1
            error_result = {"error": "REFUND_GUARD_BLOCKED", "details": str(e)}
            self.tool_history.append({
                "tool": tool_name, "args": args,
                "result": error_result, "success": False
            })
            return error_result

        except EscalationRequired as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_tool_call(
                self.ticket_id, tag, tool_name,
                args, {"escalation_required": str(e)},
                success=False, duration_ms=duration_ms
            )
            self.call_count += 1
            error_result = {"error": "ESCALATION_REQUIRED", "details": str(e)}
            self.tool_history.append({
                "tool": tool_name, "args": args,
                "result": error_result, "success": False
            })
            return error_result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_error(self.ticket_id, "TOOL_ERROR", str(e))
            self.logger.log_tool_call(
                self.ticket_id, tag, tool_name,
                args, {"error": str(e)},
                success=False, duration_ms=duration_ms
            )
            self.call_count += 1
            error_result = {"error": "TOOL_ERROR", "details": str(e)}
            self.tool_history.append({
                "tool": tool_name, "args": args,
                "result": error_result, "success": False
            })
            return error_result

    def has_minimum_calls_made(self) -> bool:
        """Check if the minimum requirement of 3 tool calls has been satisfied."""
        return self.call_count >= 3

    def get_history(self) -> list:
        """Retrieve the complete tool call history for the current ticket."""
        return list(self.tool_history)
