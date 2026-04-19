"""
retry_handler.py — Exponential backoff logic with retry budgets.

Handles tool failures gracefully with configurable retry limits.
Backoff sequence: 0.5s → 1s → 2s (doubles each attempt).
"""

import asyncio
import time
from typing import Callable, Any

# =========================
# [CONFIG]
# =========================

DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 0.5  # seconds
DEFAULT_TIMEOUT = 5.0          # seconds per tool call

# =========================
# [RETRY HANDLER]
# =========================

class RetryExhausted(Exception):
    """Raised when all retries are exhausted."""
    def __init__(self, tool_name: str, attempts: int, last_error: str):
        self.tool_name = tool_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Retry exhausted for {tool_name} after {attempts} attempts: {last_error}"
        )


async def retry_with_backoff(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
    timeout: float = DEFAULT_TIMEOUT,
    on_retry: Callable = None,  # callback(attempt, backoff, error)
) -> Any:
    """
    Execute a function with exponential backoff on failure.

    Args:
        func: The async function to call
        args: Positional arguments
        kwargs: Keyword arguments
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff duration in seconds
        timeout: Timeout per call in seconds
        on_retry: Optional callback for retry events (for logging)

    Returns:
        The function's return value on success

    Raises:
        RetryExhausted: If all retries fail
    """
    if kwargs is None:
        kwargs = {}

    last_error = ""
    backoff = initial_backoff

    for attempt in range(1, max_retries + 1):
        try:
            # Apply timeout to the function call
            start = time.time()
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
            return result

        except asyncio.TimeoutError:
            last_error = f"Timeout after {timeout}s"
            if on_retry and attempt < max_retries:
                on_retry(attempt, backoff, last_error)
            if attempt < max_retries:
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff

        except Exception as e:
            last_error = str(e)
            if on_retry and attempt < max_retries:
                on_retry(attempt, backoff, last_error)
            if attempt < max_retries:
                await asyncio.sleep(backoff)
                backoff *= 2

    # All retries exhausted
    func_name = getattr(func, '__name__', str(func))
    raise RetryExhausted(func_name, max_retries, last_error)
