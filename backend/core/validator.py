"""
Pydantic validation for tool outputs.
"""

from __future__ import annotations

from pydantic import BaseModel


class CustomerSchema(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str
    tier: str
    member_since: str
    total_orders: int
    total_spent: float
    address: dict
    notes: str


class OrderSchema(BaseModel):
    order_id: str
    customer_id: str
    product_id: str
    quantity: int
    amount: float
    status: str
    order_date: str
    delivery_date: str | None = None
    return_deadline: str | None = None
    refund_status: str | None = None
    notes: str


class ProductSchema(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    warranty_months: int
    return_window_days: int
    returnable: bool
    notes: str


class RefundEligibilitySchema(BaseModel):
    order_id: str
    eligible: bool
    reason: str
    amount: float | None = None


class KnowledgeBaseResultSchema(BaseModel):
    query: str
    results: list[str]
    matched_sections: list[str]


def validate_tool_output(tool_name: str, data: dict) -> tuple[bool, str, object]:
    if isinstance(data, dict) and "error" in data:
        return True, "", data

    schema_map = {
        "get_customer": CustomerSchema,
        "get_order": OrderSchema,
        "get_product": ProductSchema,
        "check_refund_eligibility": RefundEligibilitySchema,
        "search_knowledge_base": KnowledgeBaseResultSchema,
    }

    schema_class = schema_map.get(tool_name)
    if schema_class is None:
        return True, "", data

    try:
        validated = schema_class(**data)
        return True, "", validated.model_dump()
    except Exception as exc:
        return False, f"Validation failed for {tool_name}: {exc}", None
