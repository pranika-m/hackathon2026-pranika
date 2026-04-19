"""
logger.py — Structured audit logging for the ShopWave agent.

Every ticket gets a full audit entry written to audit_log.json on disk.
Uses clear tags: FETCH_CUSTOMER, FETCH_ORDER, FETCH_PRODUCT, SEARCH_POLICY,
CHECK_REFUND, ISSUE_REFUND, SEND_REPLY, ESCALATE, RETRY, DEAD_LETTER,
VALIDATION_ERROR, TIMEOUT.
"""

import json
import threading
from datetime import datetime
from pathlib import Path

# =========================
# [CONFIG]
# =========================

AUDIT_LOG_PATH = Path(__file__).parent.parent / "audit_log.json"

# =========================
# [AUDIT LOGGER]
# =========================

class AuditLogger:
    """Thread-safe structured audit logger that writes to audit_log.json."""

    def __init__(self):
        self._lock = threading.Lock()
        self._ticket_logs = {}  # ticket_id -> full audit entry
        self._write_to_disk([])

    def init_ticket(self, ticket_id: str, customer_email: str, subject: str):
        """Initialize an audit entry for a new ticket."""
        with self._lock:
            self._ticket_logs[ticket_id] = {
                "ticket_id": ticket_id,
                "customer_email": customer_email,
                "subject": subject,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "customer_ref": None,
                "order_ref": None,
                "product_ref": None,
                "tool_calls": [],
                "retry_events": [],
                "confidence_score": None,
                "final_decision": None,  # RESOLVED | ESCALATED | DEAD_LETTER
                "escalation_summary": None,
                "reply_sent": None,
                "errors": [],
                "reasoning_trace": []
            }

    def log_tool_call(self, ticket_id: str, tag: str, tool_name: str,
                      inputs: dict, outputs: dict, success: bool, duration_ms: float = 0):
        """Log a single tool call with inputs and outputs."""
        with self._lock:
            if ticket_id not in self._ticket_logs:
                return
            self._ticket_logs[ticket_id]["tool_calls"].append({
                "step": len(self._ticket_logs[ticket_id]["tool_calls"]) + 1,
                "timestamp": datetime.now().isoformat(),
                "tag": tag,
                "tool_name": tool_name,
                "inputs": inputs,
                "outputs": outputs,
                "success": success,
                "duration_ms": round(duration_ms, 2)
            })

    def log_retry(self, ticket_id: str, tool_name: str, attempt: int,
                  backoff_seconds: float, reason: str):
        """Log a retry event with backoff duration."""
        with self._lock:
            if ticket_id not in self._ticket_logs:
                return
            self._ticket_logs[ticket_id]["retry_events"].append({
                "timestamp": datetime.now().isoformat(),
                "tag": "RETRY",
                "tool_name": tool_name,
                "attempt": attempt,
                "backoff_seconds": backoff_seconds,
                "reason": reason
            })

    def log_reasoning(self, ticket_id: str, step: str, reasoning: str):
        """Log a reasoning step from the LLM."""
        with self._lock:
            if ticket_id not in self._ticket_logs:
                return
            self._ticket_logs[ticket_id]["reasoning_trace"].append({
                "timestamp": datetime.now().isoformat(),
                "step": step,
                "reasoning": reasoning
            })

    def log_error(self, ticket_id: str, tag: str, error: str):
        """Log an error (VALIDATION_ERROR, TIMEOUT, etc.)."""
        with self._lock:
            if ticket_id not in self._ticket_logs:
                return
            self._ticket_logs[ticket_id]["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "tag": tag,
                "error": error
            })

    def set_refs(self, ticket_id: str, customer_ref: str = None,
                 order_ref: str = None, product_ref: str = None):
        """Set customer/order/product references."""
        with self._lock:
            if ticket_id not in self._ticket_logs:
                return
            if customer_ref:
                self._ticket_logs[ticket_id]["customer_ref"] = customer_ref
            if order_ref:
                self._ticket_logs[ticket_id]["order_ref"] = order_ref
            if product_ref:
                self._ticket_logs[ticket_id]["product_ref"] = product_ref

    def set_confidence(self, ticket_id: str, score: float):
        """Set the confidence score for a ticket."""
        with self._lock:
            if ticket_id not in self._ticket_logs:
                return
            self._ticket_logs[ticket_id]["confidence_score"] = round(score, 2)

    def set_decision(self, ticket_id: str, decision: str,
                     escalation_summary: str = None, reply: str = None):
        """Set the final decision and optionally the escalation summary."""
        with self._lock:
            if ticket_id not in self._ticket_logs:
                return
            self._ticket_logs[ticket_id]["final_decision"] = decision
            self._ticket_logs[ticket_id]["completed_at"] = datetime.now().isoformat()
            if escalation_summary:
                self._ticket_logs[ticket_id]["escalation_summary"] = escalation_summary
            if reply:
                self._ticket_logs[ticket_id]["reply_sent"] = reply

    def get_ticket_log(self, ticket_id: str) -> dict:
        """Get the full audit log for a single ticket."""
        with self._lock:
            return self._ticket_logs.get(ticket_id, {})

    def get_all_logs(self) -> list:
        """Get all audit logs as a list."""
        with self._lock:
            return list(self._ticket_logs.values())

    def flush_to_disk(self):
        """Write all audit logs to audit_log.json on disk."""
        with self._lock:
            logs = list(self._ticket_logs.values())
        self._write_to_disk(logs)

    def _write_to_disk(self, logs: list):
        """Write logs list to the JSON file."""
        with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)


# Singleton
_logger = AuditLogger()

def get_audit_logger() -> AuditLogger:
    return _logger
