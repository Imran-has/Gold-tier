"""
Error Recovery and Graceful Degradation for Gold Tier
Implements robust error handling, circuit breakers, and retry policies.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic

from config.settings import LOGS_DIR


T = TypeVar('T')


class CircuitState(Enum):
    """State of a circuit breaker."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a retry attempt."""
        if self.exponential_backoff:
            delay = self.base_delay_seconds * (2 ** attempt)
        else:
            delay = self.base_delay_seconds

        delay = min(delay, self.max_delay_seconds)

        if self.jitter:
            import random
            delay *= (0.5 + random.random())

        return delay


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    Prevents cascading failures by stopping requests to failing services.
    """
    name: str
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("gold.circuit_breaker"))

    def __post_init__(self):
        self.logger = logging.getLogger(f"gold.circuit_breaker.{self.name}")

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()

    def can_execute(self) -> bool:
        """Check if an operation can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._timeout_expired():
                self._transition_to_half_open()
                return True
            return False
        else:  # HALF_OPEN
            return True

    def _timeout_expired(self) -> bool:
        """Check if the timeout has expired."""
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout_seconds

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.logger.warning(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.logger.info(f"Circuit breaker '{self.name}' half-opened for testing")

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info(f"Circuit breaker '{self.name}' closed - service recovered")

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class GracefulDegradation:
    """
    Implements graceful degradation for service failures.
    Provides fallback behaviors when primary services are unavailable.
    """

    def __init__(self):
        self.logger = logging.getLogger("gold.graceful_degradation")
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.degraded_services: Dict[str, datetime] = {}

    def register_circuit_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ) -> CircuitBreaker:
        """Register a circuit breaker for a service."""
        cb = CircuitBreaker(
            name=service_name,
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
        )
        self.circuit_breakers[service_name] = cb
        return cb

    def register_fallback(self, service_name: str, handler: Callable) -> None:
        """Register a fallback handler for a service."""
        self.fallback_handlers[service_name] = handler

    def get_circuit_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker for a service."""
        return self.circuit_breakers.get(service_name)

    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a function with circuit breaker and fallback.
        """
        cb = self.circuit_breakers.get(service_name)

        if cb and not cb.can_execute():
            self.logger.warning(f"Circuit open for '{service_name}', using fallback")
            return await self._execute_fallback(service_name, *args, **kwargs)

        try:
            if asyncio.iscoroutinefunction(primary_func):
                result = await primary_func(*args, **kwargs)
            else:
                result = primary_func(*args, **kwargs)

            if cb:
                cb.record_success()

            # Remove from degraded services if it was there
            if service_name in self.degraded_services:
                del self.degraded_services[service_name]

            return result

        except Exception as e:
            self.logger.error(f"Service '{service_name}' failed: {e}")

            if cb:
                cb.record_failure()

            self.degraded_services[service_name] = datetime.now()

            return await self._execute_fallback(service_name, *args, **kwargs)

    async def _execute_fallback(self, service_name: str, *args, **kwargs) -> Any:
        """Execute fallback handler for a service."""
        handler = self.fallback_handlers.get(service_name)

        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(*args, **kwargs)
            return handler(*args, **kwargs)

        # Default fallback: return error result
        return {
            "success": False,
            "error": f"Service '{service_name}' unavailable and no fallback configured",
            "degraded": True,
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all services."""
        return {
            "circuit_breakers": {
                name: cb.get_status()
                for name, cb in self.circuit_breakers.items()
            },
            "degraded_services": {
                name: ts.isoformat()
                for name, ts in self.degraded_services.items()
            },
        }


class ErrorRecovery:
    """
    Comprehensive error recovery system.
    Handles retries, logging, and recovery actions.
    """

    def __init__(self):
        self.logger = logging.getLogger("gold.error_recovery")
        self.error_log: List[Dict[str, Any]] = []
        self.recovery_actions: Dict[str, Callable] = {}
        self.degradation = GracefulDegradation()

    def register_recovery_action(self, error_type: str, action: Callable) -> None:
        """Register a recovery action for an error type."""
        self.recovery_actions[error_type] = action

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        retry_policy: Optional[RetryPolicy] = None,
        operation_name: str = "operation",
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic.
        """
        policy = retry_policy or RetryPolicy()
        last_exception = None

        for attempt in range(policy.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                if attempt > 0:
                    self.logger.info(
                        f"Operation '{operation_name}' succeeded after {attempt + 1} attempts"
                    )

                return result

            except policy.retryable_exceptions as e:
                last_exception = e
                self._log_error(operation_name, e, attempt + 1)

                if attempt < policy.max_retries:
                    delay = policy.get_delay(attempt)
                    self.logger.warning(
                        f"Operation '{operation_name}' failed (attempt {attempt + 1}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"Operation '{operation_name}' failed after {attempt + 1} attempts: {e}"
                    )

        # All retries exhausted
        await self._attempt_recovery(operation_name, last_exception)
        raise last_exception

    def _log_error(self, operation: str, error: Exception, attempt: int) -> None:
        """Log an error occurrence."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "attempt": attempt,
        }
        self.error_log.append(entry)

        # Persist to file
        self._persist_error(entry)

    def _persist_error(self, entry: Dict[str, Any]) -> None:
        """Persist error entry to file."""
        error_dir = LOGS_DIR / "errors"
        error_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        error_file = error_dir / f"errors_{date_str}.jsonl"

        with open(error_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    async def _attempt_recovery(self, operation: str, error: Exception) -> None:
        """Attempt to recover from an error."""
        error_type = type(error).__name__
        recovery_action = self.recovery_actions.get(error_type)

        if recovery_action:
            self.logger.info(f"Attempting recovery for {error_type}")
            try:
                if asyncio.iscoroutinefunction(recovery_action):
                    await recovery_action(operation, error)
                else:
                    recovery_action(operation, error)
            except Exception as e:
                self.logger.error(f"Recovery action failed: {e}")

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent errors."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_errors = [
            e for e in self.error_log
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]

        error_counts: Dict[str, int] = {}
        for error in recent_errors:
            error_type = error["error_type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return {
            "period_hours": hours,
            "total_errors": len(recent_errors),
            "error_counts": error_counts,
            "recent_errors": recent_errors[-10:],  # Last 10 errors
        }


def with_retry(
    retry_policy: Optional[RetryPolicy] = None,
    operation_name: Optional[str] = None,
):
    """
    Decorator to add retry logic to a function.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            recovery = ErrorRecovery()
            name = operation_name or func.__name__
            return await recovery.execute_with_retry(
                func,
                *args,
                retry_policy=retry_policy,
                operation_name=name,
                **kwargs,
            )
        return wrapper
    return decorator


def with_circuit_breaker(service_name: str, failure_threshold: int = 5):
    """
    Decorator to add circuit breaker to a function.
    """
    degradation = GracefulDegradation()
    degradation.register_circuit_breaker(service_name, failure_threshold)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await degradation.execute_with_fallback(
                service_name,
                func,
                *args,
                **kwargs,
            )
        return wrapper
    return decorator


# Global instances
error_recovery = ErrorRecovery()
graceful_degradation = GracefulDegradation()
