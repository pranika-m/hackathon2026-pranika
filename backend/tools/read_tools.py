"""
Read-only tools for loading ShopWave records and policy results.

The mocks intentionally inject a small number of deterministic failures so the
agent can demonstrate retry handling, schema validation, and graceful recovery.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_failure_counters: dict[str, int] = {}


def _load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _should_fail(key: str) -> bool:
    _failure_counters[key] = _failure_counters.get(key, 0) + 1
    return _failure_counters[key] == 1


def reset_read_failures() -> None:
    _failure_counters.clear()


async def get_customer(email: str) -> dict:
    if email == "alice.turner@email.com" and _should_fail(f"customer-timeout:{email}"):
        raise asyncio.TimeoutError("Customer lookup timed out")

    customers = _load_json("customers.json")
    customer = next((entry for entry in customers if entry["email"] == email), None)
    if not customer:
        return {"error": "CUSTOMER_NOT_FOUND", "email": email}
    return customer


async def get_order(order_id: str) -> dict:
    if order_id == "ORD-1011" and _should_fail(f"order-malformed:{order_id}"):
        return {"order_id": order_id, "status": "delivered"}

    orders = _load_json("orders.json")
    order = next((entry for entry in orders if entry["order_id"] == order_id), None)
    if not order:
        return {"error": "ORDER_NOT_FOUND", "order_id": order_id}
    return order


async def get_product(product_id: str) -> dict:
    products = _load_json("products.json")
    product = next((entry for entry in products if entry["product_id"] == product_id), None)
    if not product:
        return {"error": "PRODUCT_NOT_FOUND", "product_id": product_id}
    return product


async def search_knowledge_base(query: str) -> dict:
    if "returns" in query.lower() and _should_fail(f"kb-partial:{query.lower()}"):
        return {"query": query, "results": ["Partial KB payload"]}

    content = (DATA_DIR / "knowledge-base.md").read_text(encoding="utf-8")
    sections = []
    for chunk in content.split("## "):
        if not chunk.strip():
            continue
        title, _, body = chunk.partition("\n")
        sections.append({"title": title.strip(), "body": body.strip()})

    tokens = {token.strip(".,?!:;").lower() for token in query.split() if len(token) > 2}
    matched = []
    for section in sections:
        haystack = f"{section['title']} {section['body']}".lower()
        overlap = sum(1 for token in tokens if token in haystack)
        if overlap:
            matched.append((overlap, section))

    matched.sort(key=lambda item: item[0], reverse=True)
    chosen = [section for _, section in matched[:3]]
    if not chosen:
        chosen = [
            {
                "title": "Escalation Guidelines",
                "body": "Escalate when policy is unclear, data conflicts, or confidence drops below 0.6.",
            }
        ]

    return {
        "query": query,
        "results": [f"{section['title']}: {section['body'][:280]}" for section in chosen],
        "matched_sections": [section["title"] for section in chosen],
    }
