# Failure Modes

## 1. Tool timeout

Scenario: the first `get_customer` lookup for `alice.turner@email.com` times out.

- Detection: `asyncio.TimeoutError` inside `retry_with_backoff`
- Handling: retry up to 3 attempts with exponential backoff and log each retry event
- Outcome: later retry succeeds, processing continues, and the timeout remains visible in `audit_log.json`

## 2. Malformed tool payload

Scenario: the first `get_order("ORD-1011")` returns an incomplete object.

- Detection: Pydantic validation fails in `core/validator.py`
- Handling: executor records `VALIDATION_ERROR`, preserves the raw payload, and the planner continues with reduced confidence
- Outcome: the ticket still finishes cleanly, and the malformed payload is auditable

## 3. Partial knowledge-base response

Scenario: the first returns-related KB search omits `matched_sections`.

- Detection: schema validation rejects the response
- Handling: the failed call is logged, the agent falls back to the rest of the gathered context, and confidence is reduced
- Outcome: the ticket resolves or escalates without crashing

## 4. Conflicting customer claims

Scenario: a customer claims a tier not verified in the system or references a missing order.

- Detection: `detect_customer_conflicts` compares ticket text with verified customer and order data
- Handling: the case is flagged, confidence drops, and the ticket is escalated with a structured summary
- Outcome: no unsafe autonomous action is taken

## 5. Refund guard violation

Scenario: a code path tries to issue a refund before eligibility is checked, or the amount is above `$200`.

- Detection: `issue_refund` enforces cached eligibility and the supervisor threshold
- Handling: raise `RefundGuardError` or `EscalationRequired`
- Outcome: refund is blocked, logged, and escalated when necessary

## 6. Unrecoverable runtime failure

Scenario: an unexpected exception escapes normal handling.

- Detection: outer exception guard in `process_single_ticket_lifecycle`
- Handling: move the ticket to `FAILED`, then `DEAD_LETTER`, and persist a context snapshot to `dead_letter_queue.json`
- Outcome: failed work is not lost and can be inspected later
