"""
dead_letter_queue.py — Persists tickets that completely fail processing.

Failed tickets don't disappear — they get logged here with full context
about what went wrong and what was attempted.
"""

import json
import threading
from datetime import datetime
from pathlib import Path

# =========================
# [CONFIG]
# =========================

DLQ_PATH = Path(__file__).parent.parent / "dead_letter_queue.json"

# =========================
# [DEAD LETTER QUEUE]
# =========================

class DeadLetterQueue:
    """Persists tickets that fail all processing attempts."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = []
        self._write_to_disk()

    def add(self, ticket_id: str, reason: str, last_state: str,
            attempted_actions: list, context: dict = None):
        """
        Add a ticket to the dead letter queue.

        Args:
            ticket_id: The failed ticket ID
            reason: Why it ended up here
            last_state: The last known state before failure
            attempted_actions: List of actions that were attempted
            context: Any relevant context gathered before failure
        """
        with self._lock:
            entry = {
                "ticket_id": ticket_id,
                "dead_lettered_at": datetime.now().isoformat(),
                "reason": reason,
                "last_state": last_state,
                "attempted_actions": attempted_actions,
                "context_snapshot": context or {},
                "tag": "DEAD_LETTER"
            }
            self._entries.append(entry)
        self._write_to_disk()

    def get_all(self) -> list:
        """Get all dead-lettered tickets."""
        with self._lock:
            return list(self._entries)

    def _write_to_disk(self):
        """Persist to disk."""
        with self._lock:
            data = list(self._entries)
        with open(DLQ_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Singleton
_dlq = DeadLetterQueue()

def get_dead_letter_queue() -> DeadLetterQueue:
    return _dlq
