"""
Hardcore error handling and recovery testing for GMNAP.

Tests circuit breakers, retry storms, error context leaks, exception propagation,
and all scenarios that could cause cascading failures or system instability.
"""

import asyncio
import gc
import json
import random
import string
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from queue import Empty, Queue
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest

from src.core.errors import (
    AuthenticationError,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    ConfigurationError,
    DatabaseError,
    ErrorCollector,
    ErrorContext,
    ErrorRecovery,
    ErrorSeverity,
    GMNAPError,
    MaxRetriesExceededError,
    NetworkError,
    RateLimitError,
    RecoveryStrategy,
    ResourceExhaustedError,
    RetryableError,
    SchemaError,
    SkippableError,
    UnicodeError,
    ValidationError,
)


class TestCircuitBreakerResilience:
    """Test circuit breaker under extreme conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.breaker = CircuitBreaker(
            name="test_breaker", failure_threshold=5, recovery_timeout=1.0
        )

    def test_circuit_breaker_state_transitions(self):
        """Test proper state transitions under all conditions."""
        # Start in CLOSED state
        assert self.breaker.state == CircuitBreakerState.CLOSED

        # Accumulate failures to reach threshold
        for i in range(5):
            try:
                with self.breaker:
                    raise Exception(f"Test failure {i}")
            except Exception:
                pass

            # Should still be closed until threshold reached
            if i < 4:
                assert self.breaker.state == CircuitBreakerState.CLOSED

        # Should be OPEN after threshold failures
        assert self.breaker.state == CircuitBreakerState.OPEN

        # Should reject calls when OPEN
        with pytest.raises(CircuitBreakerOpenError):
            with self.breaker:
                pass

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should transition to HALF_OPEN
        assert self.breaker.state == CircuitBreakerState.HALF_OPEN

        # Test success in HALF_OPEN (need 3 successes to close)
        for i in range(3):
            with self.breaker:
                pass  # Success

        # Should be CLOSED after 3 successes
        assert self.breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_concurrent_access(self):
        """Test circuit breaker under concurrent access."""
        results = Queue()
        errors = Queue()

        def circuit_worker(worker_id, operations):
            """Worker that accesses circuit breaker."""
            successes = 0
            failures = 0
            circuit_open_errors = 0

            for i in range(operations):
                try:
                    with self.breaker:
                        # Randomly fail 70% of the time
                        if random.random() < 0.7:
                            raise Exception(f"Random failure {worker_id}-{i}")
                        else:
                            successes += 1
                except CircuitBreakerOpenError:
                    circuit_open_errors += 1
                except Exception:
                    failures += 1

            results.put((worker_id, successes, failures, circuit_open_errors))

        # Run concurrent workers
        num_workers = 20
        operations_per_worker = 100

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(
                target=circuit_worker, args=(i, operations_per_worker)
            )
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        worker_results = []
        while not results.empty():
            try:
                worker_results.append(results.get_nowait())
            except Empty:
                break

        # Verify results
        assert (
            len(worker_results) == num_workers
        ), f"Not all workers completed: {len(worker_results)}"

        # Should have triggered circuit breaker
        total_circuit_open = sum(result[3] for result in worker_results)
        assert total_circuit_open > 0, "Circuit breaker should have opened"

        # Circuit breaker should be protecting the system
        total_operations = num_workers * operations_per_worker
        total_protected = total_circuit_open
        protection_ratio = total_protected / total_operations

        assert (
            protection_ratio > 0.1
        ), f"Circuit breaker should protect more operations: {protection_ratio:.2%}"

    def test_circuit_breaker_memory_leak(self):
        """Test circuit breaker doesn't leak memory under stress."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Create many circuit breakers
        breakers = []
        for i in range(1000):
            breaker = CircuitBreaker(f"breaker_{i}")
            breakers.append(breaker)

            # Trigger state transitions
            for j in range(10):
                try:
                    with breaker:
                        if j % 3 == 0:
                            raise Exception(f"Test error {j}")
                except (Exception, CircuitBreakerOpenError):
                    pass

        # Check memory usage
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Should not leak excessive memory
        assert memory_growth < 50, f"Circuit breaker memory leak: {memory_growth}MB"

        # Clean up
        breakers.clear()
        gc.collect()

    def test_circuit_breaker_rapid_state_changes(self):
        """Test rapid state changes don't cause race conditions."""
        state_changes = []

        def state_monitor():
            """Monitor state changes."""
            for _ in range(1000):
                state_changes.append(self.breaker.state)
                time.sleep(0.001)

        def state_trigger():
            """Trigger state changes."""
            for i in range(100):
                try:
                    with self.breaker:
                        if i % 2 == 0:
                            raise Exception(f"Trigger {i}")
                except (Exception, CircuitBreakerOpenError):
                    pass
                time.sleep(0.001)

        # Run monitor and trigger concurrently
        monitor_thread = threading.Thread(target=state_monitor)
        trigger_thread = threading.Thread(target=state_trigger)

        monitor_thread.start()
        trigger_thread.start()

        monitor_thread.join()
        trigger_thread.join()

        # Should have recorded state changes
        assert len(state_changes) > 0, "No state changes recorded"

        # Should have valid state transitions
        valid_states = {
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        }
        for state in state_changes:
            assert state in valid_states, f"Invalid state recorded: {state}"

    def test_circuit_breaker_error_history_overflow(self):
        """Test error history doesn't overflow memory."""
        # Generate many errors
        for i in range(1000):
            try:
                with self.breaker:
                    raise Exception(f"Error {i:04d}")
            except (Exception, CircuitBreakerOpenError):
                pass

        # Check stats
        stats = self.breaker.get_stats()

        # Should limit recent errors
        assert (
            len(stats["recent_errors"]) <= 10
        ), f"Too many recent errors stored: {len(stats['recent_errors'])}"

        # Memory usage should be bounded
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        assert (
            memory_usage < 100
        ), f"Circuit breaker using too much memory: {memory_usage}MB"


class TestRetryStormPrevention:
    """Test prevention of retry storms."""

    def setup_method(self):
        """Set up test fixtures."""
        self.recovery = ErrorRecovery(max_retries=3, base_delay=0.1)

    @pytest.mark.asyncio
    async def test_retry_storm_detection(self):
        """Test detection and prevention of retry storms."""
        retry_counts = []

        async def failing_operation():
            """Operation that always fails."""
            raise NetworkError("Network unreachable")

        # Track retry attempts
        original_apply_strategy = self.recovery._apply_strategy

        async def tracked_apply_strategy(strategy, error, context):
            retry_counts.append(context.retry_count)
            return await original_apply_strategy(strategy, error, context)

        self.recovery._apply_strategy = tracked_apply_strategy

        # Simulate concurrent retry storms
        tasks = []
        for i in range(50):
            context = ErrorContext(
                error=NetworkError("Test error"),
                timestamp=datetime.now(),
                severity=ErrorSeverity.MEDIUM,
                component="test_component",
                operation=f"operation_{i}",
            )

            task = asyncio.create_task(
                self.recovery.handle_error(NetworkError("Test error"), context)
            )
            tasks.append(task)

        # Wait for all tasks (they should all fail after max retries)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should fail with MaxRetriesExceededError
        max_retry_errors = [
            r for r in results if isinstance(r, MaxRetriesExceededError)
        ]
        assert (
            len(max_retry_errors) == 50
        ), f"Expected 50 max retry errors, got {len(max_retry_errors)}"

        # Should have limited retry attempts
        max_retry_count = max(retry_counts) if retry_counts else 0
        assert max_retry_count <= 3, f"Too many retries: {max_retry_count}"

    @pytest.mark.asyncio
    async def test_exponential_backoff_limits(self):
        """Test exponential backoff doesn't grow indefinitely."""
        backoff_times = []

        original_sleep = asyncio.sleep

        async def tracked_sleep(delay):
            backoff_times.append(delay)
            await original_sleep(0.001)  # Short delay for testing

        with patch("asyncio.sleep", tracked_sleep):
            context = ErrorContext(
                error=NetworkError("Test error"),
                timestamp=datetime.now(),
                severity=ErrorSeverity.MEDIUM,
                component="test_component",
                operation="test_operation",
            )

            for retry_count in range(10):
                context.retry_count = retry_count

                try:
                    await self.recovery._apply_strategy(
                        RecoveryStrategy.RETRY_WITH_BACKOFF,
                        NetworkError("Test error"),
                        context,
                    )
                except (RetryableError, MaxRetriesExceededError):
                    pass

        # Should have exponential backoff
        assert len(backoff_times) > 0, "No backoff times recorded"

        # Should not grow indefinitely
        max_backoff = max(backoff_times)
        assert max_backoff <= 60, f"Backoff time too large: {max_backoff}s"

    @pytest.mark.asyncio
    async def test_concurrent_retry_coordination(self):
        """Test coordination of concurrent retry attempts."""
        retry_times = []

        async def coordinated_operation(operation_id):
            """Operation that tracks retry timing."""
            context = ErrorContext(
                error=NetworkError("Test error"),
                timestamp=datetime.now(),
                severity=ErrorSeverity.MEDIUM,
                component="test_component",
                operation=f"operation_{operation_id}",
            )

            start_time = time.time()

            try:
                await self.recovery.handle_error(NetworkError("Test error"), context)
            except MaxRetriesExceededError:
                pass

            end_time = time.time()
            retry_times.append(end_time - start_time)

        # Run concurrent operations
        tasks = [coordinated_operation(i) for i in range(20)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Should have reasonable spread of retry times
        assert (
            len(retry_times) == 20
        ), f"Expected 20 retry times, got {len(retry_times)}"

        # Should not all retry at exactly the same time
        time_variance = max(retry_times) - min(retry_times)
        assert (
            time_variance > 0.1
        ), f"Retry times too synchronized: {time_variance}s variance"


class TestErrorContextLeaks:
    """Test error context information leaks."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = ErrorCollector()

    def test_sensitive_data_scrubbing(self):
        """Test sensitive data is scrubbed from error contexts."""
        # Create error with sensitive data
        sensitive_error = DatabaseError(
            "Connection failed",
            username="admin",
            password="SuperSecret123",
            api_key="sk-1234567890abcdef",
            database_url="postgresql://user:pass@db.example.com:5432/prod",
            credit_card="4111-1111-1111-1111",
            ssn="123-45-6789",
        )

        context = ErrorContext(
            error=sensitive_error,
            timestamp=datetime.now(),
            severity=ErrorSeverity.HIGH,
            component="database",
            operation="connect",
            metadata={
                "connection_string": "postgresql://user:password@localhost/db",
                "credentials": {"username": "admin", "password": "secret"},
                "session_token": "Bearer jwt-token-12345",
            },
        )

        self.collector.add_error(context)

        # Get summary
        summary = self.collector.get_summary()
        summary_str = json.dumps(summary)

        # Should not contain sensitive data
        assert "SuperSecret123" not in summary_str
        assert "sk-1234567890abcdef" not in summary_str
        assert "4111-1111-1111-1111" not in summary_str
        assert "123-45-6789" not in summary_str
        assert "postgresql://user:pass@" not in summary_str
        assert "password" not in summary_str
        assert "jwt-token-12345" not in summary_str

    def test_error_context_memory_bounds(self):
        """Test error context doesn't grow unbounded."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Generate many error contexts
        for i in range(10000):
            large_error = ValidationError(
                f"Validation error {i}",
                large_data="x" * 1000,  # 1KB per error
                index=i,
                timestamp=datetime.now().isoformat(),
            )

            context = ErrorContext(
                error=large_error,
                timestamp=datetime.now(),
                severity=ErrorSeverity.MEDIUM,
                component=f"component_{i % 10}",
                operation=f"operation_{i}",
                metadata={"large_field": "y" * 1000},
            )

            self.collector.add_error(context)

        # Check memory usage
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Should be bounded by max_errors setting
        assert memory_growth < 50, f"Error collector memory leak: {memory_growth}MB"

        # Should limit number of errors
        assert (
            len(self.collector._errors) <= 1000
        ), f"Too many errors stored: {len(self.collector._errors)}"

    def test_error_traceback_sanitization(self):
        """Test error tracebacks are sanitized."""
        # Create error with sensitive data in traceback
        try:
            username = "admin"
            password = "SuperSecret123"
            api_key = "sk-1234567890abcdef"

            def sensitive_function():
                database_url = "postgresql://user:pass@db.example.com:5432/prod"
                raise DatabaseError("Connection failed", database_url=database_url)

            sensitive_function()

        except DatabaseError as e:
            context = ErrorContext(
                error=e,
                timestamp=datetime.now(),
                severity=ErrorSeverity.HIGH,
                component="database",
                operation="connect",
            )

            # Traceback should be sanitized
            assert "SuperSecret123" not in context.traceback
            assert "sk-1234567890abcdef" not in context.traceback
            assert "postgresql://user:pass@" not in context.traceback

    def test_concurrent_error_collection(self):
        """Test error collection under concurrent access."""
        results = Queue()
        errors = Queue()

        def error_generator(worker_id, error_count):
            """Generate errors concurrently."""
            generated_errors = 0

            for i in range(error_count):
                try:
                    error = ValidationError(f"Error {worker_id}-{i}")
                    context = ErrorContext(
                        error=error,
                        timestamp=datetime.now(),
                        severity=ErrorSeverity.MEDIUM,
                        component=f"component_{worker_id}",
                        operation=f"operation_{i}",
                    )

                    self.collector.add_error(context)
                    generated_errors += 1

                except Exception as e:
                    errors.put((worker_id, i, str(e)))

            results.put((worker_id, generated_errors))

        # Run concurrent error generators
        num_workers = 10
        errors_per_worker = 100

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(
                target=error_generator, args=(i, errors_per_worker)
            )
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        worker_results = []
        worker_errors = []

        while not results.empty():
            try:
                worker_results.append(results.get_nowait())
            except Empty:
                break

        while not errors.empty():
            try:
                worker_errors.append(errors.get_nowait())
            except Empty:
                break

        # Verify results
        assert (
            len(worker_results) == num_workers
        ), f"Not all workers completed: {len(worker_results)}"
        assert (
            len(worker_errors) == 0
        ), f"Errors during concurrent collection: {worker_errors}"

        # Should have collected errors
        total_generated = sum(result[1] for result in worker_results)
        assert total_generated > 0, "No errors generated"

        # Should have reasonable number of errors (limited by max_errors)
        collected_errors = len(self.collector._errors)
        assert (
            collected_errors <= 1000
        ), f"Too many errors collected: {collected_errors}"


class TestCascadingFailurePrevention:
    """Test prevention of cascading failures."""

    def setup_method(self):
        """Set up test fixtures."""
        self.recovery = ErrorRecovery(max_retries=3, base_delay=0.1)

    def test_failure_isolation(self):
        """Test failures are isolated between components."""
        # Create separate circuit breakers for components
        database_breaker = CircuitBreaker("database", failure_threshold=3)
        network_breaker = CircuitBreaker("network", failure_threshold=3)
        cache_breaker = CircuitBreaker("cache", failure_threshold=3)

        # Fail database component
        for i in range(5):
            try:
                with database_breaker:
                    raise DatabaseError("Database connection failed")
            except (DatabaseError, CircuitBreakerOpenError):
                pass

        # Database should be open
        assert database_breaker.state == CircuitBreakerState.OPEN

        # Other components should still work
        assert network_breaker.state == CircuitBreakerState.CLOSED
        assert cache_breaker.state == CircuitBreakerState.CLOSED

        # Network and cache should still accept operations
        with network_breaker:
            pass  # Should succeed

        with cache_breaker:
            pass  # Should succeed

    def test_bulkhead_pattern(self):
        """Test bulkhead pattern prevents resource exhaustion."""
        # Simulate different resource pools
        thread_pools = {
            "database": ThreadPoolExecutor(max_workers=2),
            "network": ThreadPoolExecutor(max_workers=2),
            "cache": ThreadPoolExecutor(max_workers=2),
        }

        results = Queue()

        def resource_intensive_task(pool_name, task_id):
            """Task that consumes resources."""
            try:
                time.sleep(0.1)  # Simulate work
                results.put((pool_name, task_id, "success"))
            except Exception as e:
                results.put((pool_name, task_id, f"error: {e}"))

        # Overload database pool
        database_futures = []
        for i in range(10):  # More than max_workers
            future = thread_pools["database"].submit(
                resource_intensive_task, "database", i
            )
            database_futures.append(future)

        # Other pools should still work
        network_future = thread_pools["network"].submit(
            resource_intensive_task, "network", 0
        )
        cache_future = thread_pools["cache"].submit(resource_intensive_task, "cache", 0)

        # Wait for completion
        for future in database_futures + [network_future, cache_future]:
            future.result()

        # Collect results
        task_results = []
        while not results.empty():
            try:
                task_results.append(results.get_nowait())
            except Empty:
                break

        # Network and cache should have succeeded despite database overload
        network_results = [r for r in task_results if r[0] == "network"]
        cache_results = [r for r in task_results if r[0] == "cache"]

        assert len(network_results) == 1, "Network task should have completed"
        assert len(cache_results) == 1, "Cache task should have completed"
        assert network_results[0][2] == "success", "Network task should have succeeded"
        assert cache_results[0][2] == "success", "Cache task should have succeeded"

        # Clean up
        for pool in thread_pools.values():
            pool.shutdown(wait=True)

    def test_graceful_degradation(self):
        """Test graceful degradation when components fail."""

        # Create a system with fallback behaviors
        class DegradedSystem:
            def __init__(self):
                self.database_available = True
                self.cache_available = True
                self.network_available = True

            def get_data(self, key):
                """Get data with fallback chain."""
                if self.cache_available:
                    try:
                        return f"cached_{key}"
                    except Exception:
                        self.cache_available = False

                if self.database_available:
                    try:
                        return f"db_{key}"
                    except Exception:
                        self.database_available = False

                if self.network_available:
                    try:
                        return f"network_{key}"
                    except Exception:
                        self.network_available = False

                return f"default_{key}"

        system = DegradedSystem()

        # Normal operation
        assert system.get_data("test") == "cached_test"

        # Cache fails
        system.cache_available = False
        assert system.get_data("test") == "db_test"

        # Database fails
        system.database_available = False
        assert system.get_data("test") == "network_test"

        # Network fails
        system.network_available = False
        assert system.get_data("test") == "default_test"

        # System should still function at minimum level
        assert system.get_data("test") is not None


class TestErrorLoggingSecurity:
    """Test error logging security."""

    def setup_method(self):
        """Set up test fixtures."""
        self.log_messages = []

    def mock_logger(self, level, message):
        """Mock logger that captures messages."""
        self.log_messages.append((level, str(message)))

    def test_sensitive_data_not_logged(self):
        """Test sensitive data is not logged in error messages."""
        # Create error with sensitive data
        sensitive_error = AuthenticationError(
            "Login failed",
            username="admin",
            password="SuperSecret123",
            api_key="sk-1234567890abcdef",
            jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        )

        # Mock logging
        with patch("logging.getLogger") as mock_logger:
            mock_logger.return_value.error = lambda msg: self.mock_logger("error", msg)
            mock_logger.return_value.warning = lambda msg: self.mock_logger(
                "warning", msg
            )
            mock_logger.return_value.info = lambda msg: self.mock_logger("info", msg)

            # Log the error
            logger = mock_logger.return_value
            logger.error(f"Authentication failed: {sensitive_error}")
            logger.warning(f"Error details: {sensitive_error.metadata}")

        # Check logged messages
        all_messages = " ".join(msg[1] for msg in self.log_messages)

        # Should not contain sensitive data
        assert "SuperSecret123" not in all_messages
        assert "sk-1234567890abcdef" not in all_messages
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in all_messages

    def test_error_message_injection_prevention(self):
        """Test prevention of log injection attacks."""
        # Create error with injection attempts
        injection_error = ValidationError(
            "Invalid input\n[ERROR] Fake error message\n[CRITICAL] System compromised",
            malicious_field="test\r\nINFO: This is a fake log entry",
            script_injection="<script>alert('xss')</script>",
            command_injection="'; rm -rf /; --",
        )

        # Mock logging
        with patch("logging.getLogger") as mock_logger:
            mock_logger.return_value.error = lambda msg: self.mock_logger("error", msg)

            # Log the error
            logger = mock_logger.return_value
            logger.error(f"Validation error: {injection_error}")

        # Check logged messages
        all_messages = " ".join(msg[1] for msg in self.log_messages)

        # Should not contain injection attempts
        assert "\n[ERROR]" not in all_messages
        assert "\n[CRITICAL]" not in all_messages
        assert "\r\nINFO:" not in all_messages
        assert "<script>" not in all_messages
        assert "rm -rf" not in all_messages

    def test_error_logging_performance(self):
        """Test error logging doesn't impact performance."""
        # Generate many errors
        errors = []
        for i in range(1000):
            error = ValidationError(f"Error {i:04d}", index=i, data="x" * 100)
            errors.append(error)

        # Mock logging
        with patch("logging.getLogger") as mock_logger:
            mock_logger.return_value.error = lambda msg: self.mock_logger("error", msg)

            # Time error logging
            start_time = time.time()

            logger = mock_logger.return_value
            for error in errors:
                logger.error(f"Error occurred: {error}")

            logging_time = time.time() - start_time

        # Should log quickly
        assert logging_time < 1.0, f"Error logging too slow: {logging_time:.2f}s"

        # Should have logged all errors
        assert (
            len(self.log_messages) == 1000
        ), f"Not all errors logged: {len(self.log_messages)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
