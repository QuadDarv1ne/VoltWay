"""
Circuit Breaker pattern for external API calls.

Prevents cascading failures by stopping requests to failing services.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are blocked
    - HALF_OPEN: Testing if service recovered
    
    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds to wait before trying again (OPEN -> HALF_OPEN)
        success_threshold: Successes needed in HALF_OPEN to close circuit
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        # Check if we should transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")

        return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        if self._last_failure_time is None:
            return False
        return datetime.now() >= self._last_failure_time + timedelta(
            seconds=self.timeout
        )

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN"
            )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed after recovery")
        else:
            # Reset failure count on success in CLOSED state
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery, go back to OPEN
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' reopened after failed recovery attempt"
            )
        elif self._failure_count >= self.failure_threshold:
            # Too many failures, open the circuit
            self._state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
            )

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time.isoformat()
            if self._last_failure_time
            else None,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


# Global circuit breakers for external services
open_charge_map_breaker = CircuitBreaker(
    name="OpenChargeMap",
    failure_threshold=5,
    timeout=60,
    success_threshold=2,
)

api_ninjas_breaker = CircuitBreaker(
    name="APINinjas",
    failure_threshold=5,
    timeout=60,
    success_threshold=2,
)
