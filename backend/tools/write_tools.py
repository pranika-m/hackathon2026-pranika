"""
Stateful write tools for refunds, replies, and escalations.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_eligibility_cache: dict[str, dict] = {}


class RefundGuardError(Exception):
    """Raised when a refund is attempted without prior eligibility verification."""


class EscalationRequired(Exception):
    """Raised when a human should take over instead of autonomous execution."""


def reset_tool_state() -> None:
    _eligibility_cache.clear()


def _load_json(filename: str) -> list[dict]:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _find_order(order_id: str) -> dict | None:
    return next((entry for entry in _load_json("orders.json") if entry["order_id"] == order_id), None)


def _find_customer(customer_id: str) -> dict | None:
    return next((entry for entry in _load_json("customers.json") if entry["customer_id"] == customer_id), None)


async def check_refund_eligibility(order_id: str) -> dict:
    order = _find_order(order_id)
    if not order:
        return {
            "order_id": order_id,
            "eligible": False,
            "reason": "ORDER_NOT_FOUND",
            "amount": None,
        }

    customer = _find_customer(order["customer_id"]) or {}
    product = next(
        (entry for entry in _load_json("products.json") if entry["product_id"] == order["product_id"]),
        None,
    ) or {}

    if order.get("refund_status") == "refunded":
        result = {
            "order_id": order_id,
            "eligible": False,
            "reason": "ALREADY_REFUNDED",
            "amount": order["amount"],
        }
        _eligibility_cache[order_id] = result
        return result

    delivery_date = order.get("delivery_date")
    if not delivery_date:
        result = {
            "order_id": order_id,
            "eligible": False,
            "reason": "NOT_DELIVERED",
            "amount": order["amount"],
        }
        _eligibility_cache[order_id] = result
        return result

    today = datetime(2024, 3, 15).date()
    delivered_at = datetime.strptime(delivery_date, "%Y-%m-%d").date()
    days_since_delivery = (today - delivered_at).days
    return_window = int(product.get("return_window_days", 30))

    reason = "WITHIN_RETURN_WINDOW"
    eligible = days_since_delivery <= return_window

    notes = f"{order.get('notes', '')} {customer.get('notes', '')}".lower()
    tier = str(customer.get("tier", "standard")).lower()
    days_outside_window = max(days_since_delivery - return_window, 0)

    if not eligible and tier == "premium" and 1 <= days_outside_window <= 3:
        eligible = True
        reason = "PREMIUM_BORDERLINE_EXCEPTION"

    if not eligible and tier == "vip" and "extended return" in notes:
        eligible = True
        reason = "VIP_EXCEPTION_ON_FILE"

    if "registered online" in order.get("notes", "").lower():
        eligible = False
        reason = "NON_RETURNABLE_REGISTERED_ITEM"

    result = {
        "order_id": order_id,
        "eligible": eligible,
        "reason": reason if eligible else reason or "RETURN_WINDOW_EXPIRED",
        "amount": order["amount"],
    }
    if not eligible and reason == "WITHIN_RETURN_WINDOW":
        result["reason"] = "RETURN_WINDOW_EXPIRED"

    _eligibility_cache[order_id] = result
    return result


async def issue_refund(order_id: str, amount: float) -> dict:
    eligibility = _eligibility_cache.get(order_id)
    if not eligibility:
        raise RefundGuardError(
            f"Cannot issue refund for {order_id}: check_refund_eligibility must run first."
        )

    if not eligibility.get("eligible"):
        raise RefundGuardError(
            f"Refund blocked for {order_id}: eligibility result was {eligibility.get('reason')}."
        )

    if amount > 200.0:
        raise EscalationRequired(
            f"Refund amount ${amount:.2f} exceeds the autonomous threshold of $200."
        )

    return {
        "status": "SUCCESS",
        "order_id": order_id,
        "refund_id": f"REF-{order_id[4:]}-{int(datetime.now().timestamp())}",
        "amount_refunded": amount,
        "currency": "USD",
    }


async def send_reply(ticket_id: str, message: str) -> dict:
    return {
        "status": "SENT",
        "ticket_id": ticket_id,
        "timestamp": datetime.now().isoformat(),
        "message_preview": message[:120],
        "message": message,
    }


async def escalate(ticket_id: str, summary: str, priority: str = "medium") -> dict:
    return {
        "status": "ESCALATED",
        "ticket_id": ticket_id,
        "queue": "HUMAN_SUPPORT_PRIMARY",
        "priority": priority,
        "summary": summary,
    }
