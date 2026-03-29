"""
Error handling and recovery mechanisms for GMNAP.
Provides custom exceptions, error recovery strategies, and circuit breakers.
"""

import asyncio
import logging
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

logger = logging.getLogger(__name__)


T = TypeVar("T")


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"  # Can be ignored or logged
    MEDIUM = "medium"  # Should be handled, may retry
    HIGH = "high"  # Must be handled, affects functionality
    CRITICAL = "critical"  # System failure, requires immediate attention


class RecoveryStrategy(Enum):
    """Error recovery strategies."""

    IGNORE = "ignore"  # Log and continue
    RETRY = "retry"  # Retry the operation
    RETRY_WITH_BACKOFF = "retry_backoff"  # Retry with exponential backoff
    SKIP = "skip"  # Skip the current item
    FAIL_FAST = "fail_fast"  # Stop processing immediately
    FALLBACK = "fallback"  # Use fallback value/behavior
    CIRCUIT_BREAK = "circuit_break"  # Open circuit breaker


@dataclass
class ErrorContext:
    """Context information for an error."""

    error: Exception
    timestamp: datetime
    severity: ErrorSeverity
    component: str
    operation: str
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None

    def __post_init__(self):
        if self.traceback is None:
            self.traceback = traceback.format_exc()


# Custom Exceptions
class GMNAPError(Exception):
    """Base exception for GMNAP errors."""

    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.RETRY

    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.message = message
        self.metadata = kwargs
        self.timestamp = datetime.now()


class ValidationError(GMNAPError):
    """Data validation error."""

    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.SKIP


class SchemaError(ValidationError):
    """Schema validation error."""

    pass


class RegionError(GMNAPError):
    """Regional processing error."""

    pass


class UnicodeError(GMNAPError):
    """Unicode processing error."""

    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.FALLBACK


class DatabaseError(GMNAPError):
    """Database operation error."""

    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY_WITH_BACKOFF


class NetworkError(GMNAPError):
    """Network operation error."""

    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.RETRY_WITH_BACKOFF


class AuthenticationError(GMNAPError):
    """Authentication error."""

    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.FAIL_FAST


class RateLimitError(NetworkError):
    """Rate limit exceeded error."""

    recovery_strategy = RecoveryStrategy.RETRY_WITH_BACKOFF

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ConfigurationError(GMNAPError):
    """Configuration error."""

    severity = ErrorSeverity.CRITICAL
    recovery_strategy = RecoveryStrategy.FAIL_FAST


class ResourceExhaustedError(GMNAPError):
    """Resource exhaustion error."""

    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.CIRCUIT_BREAK


# Error Recovery
class ErrorRecovery:
    """Handles error recovery strategies."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._error_handlers: Dict[Type[Exception], Callable] = {}

    def register_handler(self, error_type: Type[Exception], handler: Callable) -> None:
        """Register a custom error handler."""
        self._error_handlers[error_type] = handler

    async def handle_error(self, error: Exception, context: ErrorContext) -> Any:
        """Handle an error based on its type and recovery strategy."""
        # Check for custom handler
        for error_type, handler in self._error_handlers.items():
            if isinstance(error, error_type):
                return await handler(error, context)

        # Use default strategy based on error type
        if isinstance(error, GMNAPError):
            strategy = error.recovery_strategy
        else:
            strategy = RecoveryStrategy.RETRY

        return await self._apply_strategy(strategy, error, context)

    async def _apply_strategy(
        self, strategy: RecoveryStrategy, error: Exception, context: ErrorContext
    ) -> Any:
        """Apply a recovery strategy."""
        if strategy == RecoveryStrategy.IGNORE:
            logger.warning(f"Ignoring error in {context.component}: {error}")
            return None

        elif strategy == RecoveryStrategy.RETRY:
            if context.retry_count < self.max_retries:
                await asyncio.sleep(self.base_delay)
                raise RetryableError(str(error), original_error=error)
            else:
                raise MaxRetriesExceededError(
                    f"Max retries ({self.max_retries}) exceeded for {context.operation}",
                    original_error=error,
                )

        elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            if context.retry_count < self.max_retries:
                delay = self.base_delay * (2**context.retry_count)
                await asyncio.sleep(delay)
                raise RetryableError(str(error), original_error=error)
            else:
                raise MaxRetriesExceededError(
                    f"Max retries ({self.max_retries}) exceeded for {context.operation}",
                    original_error=error,
                )

        elif strategy == RecoveryStrategy.SKIP:
            logger.warning(f"Skipping item due to error in {context.component}: {error}")
            raise SkippableError(str(error), original_error=error)

        elif strategy == RecoveryStrategy.FAIL_FAST:
            logger.error(f"Critical error in {context.component}, failing fast: {error}")
            raise

        elif strategy == RecoveryStrategy.FALLBACK:
            logger.warning(f"Using fallback for error in {context.component}: {error}")
            return context.metadata.get("fallback_value")

        elif strategy == RecoveryStrategy.CIRCUIT_BREAK:
            logger.error(f"Circuit breaker opened due to error in {context.component}: {error}")
            raise CircuitBreakerOpenError(
                f"Circuit breaker open for {context.component}", original_error=error
            )

        else:
            raise ValueError(f"Unknown recovery strategy: {strategy}")


# Special error types for recovery flow
class RetryableError(Exception):
    """Indicates an error that should be retried."""

    def __init__(self, message: str, original_error: Exception):
        super().__init__(message)
        self.original_error = original_error


class SkippableError(Exception):
    """Indicates an error where the item should be skipped."""

    def __init__(self, message: str, original_error: Exception):
        super().__init__(message)
        self.original_error = original_error


class MaxRetriesExceededError(Exception):
    """Indicates maximum retries have been exceeded."""

    def __init__(self, message: str, original_error: Exception):
        super().__init__(message)
        self.original_error = original_error


class CircuitBreakerOpenError(Exception):
    """Indicates circuit breaker is open."""

    def __init__(self, message: str, original_error: Exception):
        super().__init__(message)
        self.original_error = original_error


# Circuit Breaker Pattern
class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Implements circuit breaker pattern for fault tolerance."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0
        self._recent_errors: deque = deque(maxlen=10)

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        if self._state == CircuitBreakerState.OPEN:
            # Check if we should transition to half-open
            if (
                self._last_failure_time
                and time.time() - self._last_failure_time >= self.recovery_timeout
            ):
                self._state = CircuitBreakerState.HALF_OPEN
                self._success_count = 0

        return self._state

    def __enter__(self):
        """Enter circuit breaker context."""
        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN",
                original_error=Exception("Circuit breaker is open"),
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit circuit breaker context."""
        if exc_type is None:
            # Success
            self._on_success()
        elif isinstance(exc_val, self.expected_exception):
            # Expected failure
            self._on_failure(exc_val)
        # Let other exceptions propagate
        return False

    def _on_success(self):
        """Handle successful operation."""
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= 3:  # Require 3 successes to close
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED")

        # Reset failure count on success in closed state
        if self._state == CircuitBreakerState.CLOSED:
            self._failure_count = 0

    def _on_failure(self, error: Exception):
        """Handle failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._recent_errors.append(
            {"error": str(error), "type": type(error).__name__, "time": datetime.now()}
        )

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open state reopens the circuit
            self._state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' reopened due to failure")

        elif (
            self._state == CircuitBreakerState.CLOSED
            and self._failure_count >= self.failure_threshold
        ):
            # Too many failures, open the circuit
            self._state = CircuitBreakerState.OPEN
            logger.error(
                f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
            )

    def reset(self):
        """Reset circuit breaker to closed state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._recent_errors.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "recent_errors": list(self._recent_errors),
        }


# Error aggregation and reporting
class ErrorCollector:
    """Collects and aggregates errors for reporting."""

    def __init__(self, max_errors: int = 1000):
        self._errors: deque = deque(maxlen=max_errors)
        self._error_counts: Dict[str, int] = {}
        self._component_errors: Dict[str, List[ErrorContext]] = {}

    def add_error(self, error_context: ErrorContext) -> None:
        """Add an error to the collector."""
        self._errors.append(error_context)

        # Count by error type
        error_type = type(error_context.error).__name__
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        # Group by component
        if error_context.component not in self._component_errors:
            self._component_errors[error_context.component] = []
        self._component_errors[error_context.component].append(error_context)

    def get_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        return {
            "total_errors": len(self._errors),
            "error_counts": self._error_counts.copy(),
            "components": list(self._component_errors.keys()),
            "recent_errors": [
                {
                    "component": ctx.component,
                    "operation": ctx.operation,
                    "error": str(ctx.error),
                    "severity": ctx.severity.value,
                    "timestamp": ctx.timestamp.isoformat(),
                }
                for ctx in list(self._errors)[-10:]  # Last 10 errors
            ],
        }

    def get_errors_by_component(self, component: str) -> List[ErrorContext]:
        """Get errors for a specific component."""
        return self._component_errors.get(component, [])
