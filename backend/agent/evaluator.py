"""
Hybrid confidence scoring.

Gemini scores the case when available; heuristic scoring remains the fallback.
"""

from __future__ import annotations

import json

from core.llm_client import get_llm_client


def extract_failures(tool_history: list[dict]) -> list[dict]:
    return [entry for entry in tool_history if not entry.get("success", True)]


def _heuristic_score(context: dict, tool_history: list[dict]) -> float:
    score = 0.88

    if not context.get("customer") or "error" in str(context.get("customer")):
        score -= 0.28
    failures = extract_failures(tool_history)
    if failures:
        score -= min(0.24, 0.08 * len(failures))
    if context.get("conflicts"):
        score -= 0.35
    if context.get("flags"):
        score -= 0.12
    if not any(entry["tool"] == "send_reply" and entry.get("success") for entry in tool_history):
        score -= 0.2
    if any(entry["tool"] == "escalate" and entry.get("success") for entry in tool_history):
        score = min(score, 0.72)
    if not any(entry.get("success") for entry in tool_history):
        score = 0.2

    return max(0.0, min(1.0, score))


async def score_resolution_confidence(ticket: dict, context: dict, tool_history: list) -> float:
    fallback = _heuristic_score(context, tool_history)
    llm = get_llm_client()

    if not llm.enabled:
        return fallback

    prompt = f"""
Score how confident ShopWave's agent should be in this ticket outcome.

Ticket:
{json.dumps(ticket, ensure_ascii=True)}

Context:
{json.dumps({
    "customer": context.get("customer"),
    "order": context.get("order"),
    "product": context.get("product"),
    "refund_eligibility": context.get("refund_eligibility"),
    "conflicts": context.get("conflicts", []),
    "flags": context.get("flags", []),
}, ensure_ascii=True)}

Tool history:
{json.dumps(tool_history[-8:], ensure_ascii=True)}

Heuristic fallback:
{fallback}

Return JSON only:
{{"score": 0.0, "reasoning": "short explanation"}}
"""

    try:
        response = await llm.generate_json(prompt)
        if response.startswith("[LLM_"):
            return fallback
        parsed = json.loads(response)
        score = float(parsed.get("score", fallback))
        return max(0.0, min(1.0, score))
    except Exception:
        return fallback


def apply_automatic_score_deductions(base_score: float, context: dict) -> float:
    score = base_score
    if context.get("conflicts"):
        score -= 0.05
    if context.get("flags"):
        score -= 0.05
    refund_eligibility = context.get("refund_eligibility") or {}
    if refund_eligibility.get("reason") == "ORDER_NOT_FOUND":
        score -= 0.1
    return max(0.0, min(1.0, score))
