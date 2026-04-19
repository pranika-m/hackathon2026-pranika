"""
state_manager.py — Tracks ticket state through the agent loop.

States: INGESTED → CONTEXT_LOADED → PLANNED → EXECUTING → RESOLVED/ESCALATED/FAILED → DEAD_LETTER
"""

from enum import Enum
from datetime import datetime
import threading

# =========================
# [STATE ENUM]
# =========================

class TicketState(str, Enum):
    INGESTED = "INGESTED"
    CONTEXT_LOADED = "CONTEXT_LOADED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


# Valid transitions
VALID_TRANSITIONS = {
    TicketState.INGESTED: [TicketState.CONTEXT_LOADED, TicketState.FAILED],
    TicketState.CONTEXT_LOADED: [TicketState.PLANNED, TicketState.FAILED],
    TicketState.PLANNED: [TicketState.EXECUTING, TicketState.FAILED],
    TicketState.EXECUTING: [TicketState.RESOLVED, TicketState.ESCALATED, TicketState.FAILED],
    TicketState.FAILED: [TicketState.DEAD_LETTER],
    TicketState.RESOLVED: [],
    TicketState.ESCALATED: [],
    TicketState.DEAD_LETTER: [],
}


# =========================
# [STATE MANAGER]
# =========================

class StateManager:
    """Thread-safe state manager for all tickets."""

    def __init__(self):
        self._lock = threading.Lock()
        self._states = {}       # ticket_id -> TicketState
        self._history = {}      # ticket_id -> list of (state, timestamp)
        self._contexts = {}     # ticket_id -> dict of gathered context

    def init_ticket(self, ticket_id: str):
        """Initialize a new ticket in INGESTED state."""
        with self._lock:
            self._states[ticket_id] = TicketState.INGESTED
            self._history[ticket_id] = [
                (TicketState.INGESTED, datetime.now().isoformat())
            ]
            self._contexts[ticket_id] = {
                "ticket": None,
                "customer": None,
                "order": None,
                "product": None,
                "policy_results": None,
                "refund_eligibility": None,
                "plan": None,
                "tool_results": [],
                "conflicts": [],
                "flags": [],
            }

    def transition(self, ticket_id: str, new_state: TicketState) -> bool:
        """
        Transition a ticket to a new state.
        Returns True if transition is valid, False otherwise.
        """
        with self._lock:
            current = self._states.get(ticket_id)
            if current is None:
                return False
            if new_state not in VALID_TRANSITIONS.get(current, []):
                return False
            self._states[ticket_id] = new_state
            self._history[ticket_id].append(
                (new_state, datetime.now().isoformat())
            )
            return True

    def get_state(self, ticket_id: str) -> TicketState:
        """Get the current state of a ticket."""
        with self._lock:
            return self._states.get(ticket_id)

    def get_all_states(self) -> dict:
        """Get states for all tickets."""
        with self._lock:
            return dict(self._states)

    def set_context(self, ticket_id: str, key: str, value):
        """Store context data gathered during processing."""
        with self._lock:
            if ticket_id in self._contexts:
                self._contexts[ticket_id][key] = value

    def get_context(self, ticket_id: str) -> dict:
        """Get all context for a ticket."""
        with self._lock:
            return self._contexts.get(ticket_id, {}).copy()

    def add_conflict(self, ticket_id: str, conflict: str):
        """Add a detected conflict for a ticket."""
        with self._lock:
            if ticket_id in self._contexts:
                self._contexts[ticket_id]["conflicts"].append(conflict)

    def add_flag(self, ticket_id: str, flag: str):
        """Add a flag (e.g. 'threatening_language', 'social_engineering')."""
        with self._lock:
            if ticket_id in self._contexts:
                self._contexts[ticket_id]["flags"].append(flag)

    def is_terminal(self, ticket_id: str) -> bool:
        """Check if ticket is in a terminal state."""
        state = self.get_state(ticket_id)
        return state in (TicketState.RESOLVED, TicketState.ESCALATED, TicketState.DEAD_LETTER)

    def get_summary(self) -> dict:
        """Get a summary of all ticket states."""
        with self._lock:
            total = len(self._states)
            counts = {}
            for state in TicketState:
                counts[state.value] = sum(
                    1 for s in self._states.values() if s == state
                )
            completed = sum(
                1 for s in self._states.values()
                if s in (TicketState.RESOLVED, TicketState.ESCALATED, TicketState.DEAD_LETTER)
            )
            return {
                "total": total,
                "completed": completed,
                "counts": counts,
            }


# Singleton
_manager = StateManager()

def get_state_manager() -> StateManager:
    return _manager
