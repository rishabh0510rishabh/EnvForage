import asyncio
import logging
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger("CircuitBreaker")

T = TypeVar('T')

class CircuitState(Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failing, requests blocked
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class CircuitBreakerError(Exception):
    pass

class CircuitBreaker:
    """
    A sophisticated Circuit Breaker state machine for protecting external API calls.
    """
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0

    def _evaluate_state(self):
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.recovery_timeout:
                logger.warning("Circuit entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit recovered, returning to CLOSED state")
            self.state = CircuitState.CLOSED
            self.failure_count = 0

    def record_failure(self):
        self.last_failure_time = time.time()
        self.failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            logger.error("Circuit failed in HALF_OPEN, reverting to OPEN")
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit failure threshold reached ({self.failure_count}). Tripping OPEN.")
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        self._evaluate_state()
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        return False

class ExponentialBackoff:
    """Provides robust exponential backoff retry logic."""
    @staticmethod
    async def execute(
        func: Callable[..., Any],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        *args, **kwargs
    ) -> Any:
        retries = 0
        while True:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Max retries ({max_retries}) exhausted.")
                    raise

                delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                logger.warning(f"Execution failed: {e}. Retrying in {delay}s ({retries}/{max_retries})...")
                await asyncio.sleep(delay)

# Global instances for core systems
matrix_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

def with_resilience(max_retries: int = 3):
    """Decorator that wraps a function with both Circuit Breaker and Backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not matrix_circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit is OPEN. Fast-failing request to protect downstream.")

            try:
                result = await ExponentialBackoff.execute(func, max_retries=max_retries, *args, **kwargs)
                matrix_circuit_breaker.record_success()
                return result
            except Exception:
                matrix_circuit_breaker.record_failure()
                raise
        return wrapper
    return decorator
