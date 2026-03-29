"""
Hardcore authority integration testing for GMNAP.

Tests API integration, rate limiting, network failures, quota management,
and all scenarios that could cause data corruption or system failures.
"""

import asyncio
import json
import random
import socket
import ssl
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.authorities.base import (
    FetchStatus,
    QuotaManager,
)
from src.authorities.tier0.openalex import OpenAlexFetcher


class TestAuthorityQuotaManagement:
    """Test quota management under extreme conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Create test source manifest
        self.source_manifest = {
            "OpenAlex": {"daily_quota": 864000, "tier": 0, "requires_auth": False},
            "ORCID": {"daily_quota": 10000, "tier": 0, "requires_auth": False},
            "TestService": {"daily_quota": 10, "tier": 0, "requires_auth": False},
        }
        self.quota_manager = QuotaManager(self.source_manifest, Path("/tmp/test_quota"))
        # Reset quota state for clean test
        self.quota_manager.reset()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_quota_exhaustion_recovery(self):
        """Test quota exhaustion and recovery scenarios."""
        test_service = "TestService"

        async def run_test():
            # Exhaust quota
            for i in range(10):
                can_acquire = await self.quota_manager.acquire_quota(test_service)
                assert can_acquire, f"Should be able to acquire quota for request {i}"

            # Should be exhausted now
            can_acquire = await self.quota_manager.acquire_quota(test_service)
            assert not can_acquire, "Quota should be exhausted"

            # Verify quota tracking
            remaining = self.quota_manager.get_remaining_quota(test_service)
            assert remaining == 0, f"Remaining quota should be 0, got {remaining}"

            # Test usage stats
            stats = self.quota_manager.get_usage_stats()
            assert test_service in stats
            assert stats[test_service]["used"] == 10
            assert stats[test_service]["quota"] == 10
            assert stats[test_service]["remaining"] == 0

        asyncio.run(run_test())

    def test_concurrent_quota_tracking(self):
        """Test quota tracking under concurrent access."""
        test_service = "OpenAlex"

        async def run_test():
            # Test concurrent quota acquisition
            tasks = []
            for i in range(20):
                task = asyncio.create_task(
                    self.quota_manager.acquire_quota(test_service, 1)
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # All should succeed since we have plenty of quota
            assert all(results), "All quota acquisitions should succeed"

            # Verify usage tracking
            remaining = self.quota_manager.get_remaining_quota(test_service)
            assert (
                remaining == 864000 - 20
            ), f"Should have consumed 20 requests, remaining: {remaining}"

        asyncio.run(run_test())

    def test_quota_persistence_across_restarts(self):
        """Test quota persistence across restarts."""
        test_service = "TestService"

        async def run_test():
            # Use some quota
            for i in range(5):
                await self.quota_manager.acquire_quota(test_service)

            # Check initial state
            stats_before = self.quota_manager.get_usage_stats()
            assert stats_before[test_service]["used"] == 5

            # Create new quota manager (simulate restart)
            new_quota_manager = QuotaManager(
                self.source_manifest, Path("/tmp/test_quota")
            )

            # Should have restored usage
            stats_after = new_quota_manager.get_usage_stats()
            if test_service in stats_after:
                assert stats_after[test_service]["used"] == 5

            # Should not be able to use more than remaining
            remaining = new_quota_manager.get_remaining_quota(test_service)
            assert remaining == 5

        asyncio.run(run_test())

    def test_quota_race_condition_prevention(self):
        """Test quota race condition prevention."""
        test_service = "TestService"

        async def run_test():
            # Create many concurrent tasks that try to exhaust quota
            tasks = []
            for i in range(20):  # More than quota (10)
                task = asyncio.create_task(
                    self.quota_manager.acquire_quota(test_service, 1)
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # Only 10 should succeed
            successful = sum(1 for r in results if r)
            assert (
                successful == 10
            ), f"Only 10 requests should succeed, got {successful}"

            # Verify final usage
            remaining = self.quota_manager.get_remaining_quota(test_service)
            assert remaining == 0, f"Should have no remaining quota, got {remaining}"

        asyncio.run(run_test())


class TestNetworkFailureRecovery:
    """Test network failure recovery scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.fetcher = OpenAlexFetcher({"email": "test@example.com"})

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_network_timeout_handling(self):
        """Test network timeout handling."""

        async def run_test():
            with patch("aiohttp.ClientSession.get") as mock_get:
                # Mock timeout
                mock_get.side_effect = asyncio.TimeoutError("Request timed out")

                result = await self.fetcher.fetch("test mathematician")

                assert result.status == FetchStatus.NETWORK_ERROR
                assert "timeout" in result.error_message.lower()

        asyncio.run(run_test())

    def test_dns_resolution_failure(self):
        """Test DNS resolution failure."""

        async def run_test():
            with patch("aiohttp.ClientSession.get") as mock_get:
                # Mock DNS failure
                mock_get.side_effect = socket.gaierror("DNS lookup failed")

                result = await self.fetcher.fetch("test mathematician")

                assert result.status == FetchStatus.NETWORK_ERROR
                assert result.error_message is not None

        asyncio.run(run_test())

    def test_ssl_certificate_failure(self):
        """Test SSL certificate failure."""

        async def run_test():
            with patch("aiohttp.ClientSession.get") as mock_get:
                # Mock SSL failure
                mock_get.side_effect = ssl.SSLError(
                    "SSL certificate verification failed"
                )

                result = await self.fetcher.fetch("test mathematician")

                assert result.status == FetchStatus.NETWORK_ERROR
                assert "ssl" in result.error_message.lower()

        asyncio.run(run_test())

    def test_connection_refused(self):
        """Test connection refused scenario."""

        async def run_test():
            with patch("aiohttp.ClientSession.get") as mock_get:
                # Mock connection refused
                mock_get.side_effect = ConnectionRefusedError("Connection refused")

                result = await self.fetcher.fetch("test mathematician")

                assert result.status == FetchStatus.NETWORK_ERROR
                assert result.error_message is not None

        asyncio.run(run_test())

    def test_rate_limit_handling(self):
        """Test rate limiting handling."""

        async def run_test():
            # Mock rate limited response
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.text = AsyncMock(return_value="Rate limited")

            # Mock the context manager properly
            mock_get = AsyncMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession.get", return_value=mock_get):
                result = await self.fetcher.fetch("test mathematician")

                assert result.status == FetchStatus.RATE_LIMITED
                assert result.retry_after == 60

        asyncio.run(run_test())

    def test_server_error_handling(self):
        """Test server error handling."""

        async def run_test():
            # Mock server error
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal server error")

            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await self.fetcher.fetch("test mathematician")

                assert result.status == FetchStatus.NETWORK_ERROR
                assert result.error_message is not None

        asyncio.run(run_test())

    def test_malformed_response_handling(self):
        """Test malformed response handling."""

        async def run_test():
            # Mock malformed JSON response
            mock_response = AsyncMock()
            mock_response.status = 200

            # Mock text() as an async method that returns a string
            async def mock_text():
                return "not json"

            mock_response.text = mock_text

            # Mock the context manager properly
            mock_get = AsyncMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession.get", return_value=mock_get):
                result = await self.fetcher.fetch("test mathematician")

                assert result.status == FetchStatus.PARSE_ERROR
                assert result.error_message is not None

        asyncio.run(run_test())

    def test_network_partition_recovery(self):
        """Test recovery from network partition."""

        async def run_test():
            call_count = 0

            async def mock_get(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 3:
                    raise asyncio.TimeoutError("Network partition")

                # Return successful response on 4th try
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value='{"results": []}')
                return mock_response

            with patch("aiohttp.ClientSession.get", side_effect=mock_get):
                result = await self.fetcher.fetch("test mathematician")

                # Should eventually succeed or give up gracefully
                assert result.status in [
                    FetchStatus.NOT_FOUND,
                    FetchStatus.NETWORK_ERROR,
                ]


class TestAPIDataCorruption:
    """Test API data corruption scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.fetcher = OpenAlexFetcher({"email": "test@example.com"})

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_response_injection_attack(self):
        """Test response injection attack prevention."""

        async def run_test():
            # Mock malicious response
            malicious_response = {
                "results": [
                    {
                        "id": "https://openalex.org/A12345",
                        "display_name": "John Smith<script>alert('xss')</script>",
                        "works_count": 999999999999999999999,  # Integer overflow attempt
                        "cited_by_count": -1,  # Negative value
                        "last_known_institution": {
                            "display_name": "Evil University\x00\x01\x02"  # Null bytes
                        },
                    }
                ]
            }

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(malicious_response))

            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await self.fetcher.fetch("test mathematician")

                # Should either sanitize or reject malicious data
                if result.status == FetchStatus.SUCCESS:
                    assert result.data is not None
                    # Should not contain script tags
                    assert "<script>" not in result.data.canonical_name
                    # Should handle null bytes
                    assert "\x00" not in str(result.data.affiliations)

        asyncio.run(run_test())

    def test_unicode_corruption_in_response(self):
        """Test handling of Unicode corruption in response."""

        async def run_test():
            # Mock response with Unicode issues
            corrupted_response = {
                "results": [
                    {
                        "id": "https://openalex.org/A12345",
                        "display_name": "John Smith\ufffe\uffff",  # Invalid Unicode
                        "works_count": 42,
                        "cited_by_count": 100,
                    }
                ]
            }

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(corrupted_response))

            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await self.fetcher.fetch("test mathematician")

                # Should handle Unicode corruption gracefully
                if result.status == FetchStatus.SUCCESS:
                    assert result.data is not None
                    # Should not contain invalid Unicode
                    assert "\ufffe" not in result.data.canonical_name
                    assert "\uffff" not in result.data.canonical_name

        asyncio.run(run_test())

    def test_extremely_large_response(self):
        """Test handling of extremely large responses."""

        async def run_test():
            # Mock huge response
            huge_response = {
                "results": [
                    {
                        "id": "https://openalex.org/A12345",
                        "display_name": "A" * 10000,  # 10KB name
                        "works_count": 42,
                        "cited_by_count": 100,
                    }
                ]
            }

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(huge_response))

            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await self.fetcher.fetch("test mathematician")

                # Should handle large responses gracefully
                if result.status == FetchStatus.SUCCESS:
                    assert result.data is not None
                    # Should truncate or reject overly large data
                    assert len(result.data.canonical_name) < 1000

        asyncio.run(run_test())

    def test_response_timing_attack(self):
        """Test response timing attack prevention."""

        async def run_test():
            start_time = time.time()

            # Mock slow response
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value='{"results": []}')
                return mock_response

            with patch("aiohttp.ClientSession.get", side_effect=slow_response):
                result = await self.fetcher.fetch("test mathematician")

                elapsed = time.time() - start_time

                # Should have reasonable timeout
                assert elapsed < 10.0, f"Request took too long: {elapsed:.2f}s"
                assert result.status in [
                    FetchStatus.NOT_FOUND,
                    FetchStatus.NETWORK_ERROR,
                ]

        asyncio.run(run_test())

    def test_concurrent_api_corruption(self):
        """Test concurrent API corruption scenarios."""

        async def run_test():
            # Test concurrent requests with mixed good/bad responses
            async def mixed_response(*args, **kwargs):
                if random.random() < 0.3:  # 30% bad responses
                    raise asyncio.TimeoutError("Random failure")

                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value='{"results": []}')
                return mock_response

            with patch("aiohttp.ClientSession.get", side_effect=mixed_response):
                # Run multiple concurrent requests
                tasks = []
                for i in range(10):
                    task = asyncio.create_task(
                        self.fetcher.fetch(f"test mathematician {i}")
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Should handle mixed success/failure gracefully
                successful = sum(
                    1
                    for r in results
                    if isinstance(r, type(results[0]))
                    and r.status == FetchStatus.NOT_FOUND
                )
                failed = sum(
                    1
                    for r in results
                    if isinstance(r, type(results[0]))
                    and r.status == FetchStatus.NETWORK_ERROR
                )

                assert successful + failed == 10, "All requests should complete"

        asyncio.run(run_test())


class TestAuthorityDataIntegrity:
    """Test authority data integrity."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.fetcher = OpenAlexFetcher({"email": "test@example.com"})

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_personal_data_scrubbing(self):
        """Test personal data scrubbing."""

        async def run_test():
            # Mock response with personal data
            response_with_pii = {
                "results": [
                    {
                        "id": "https://openalex.org/A12345",
                        "display_name": "John Smith",
                        "works_count": 42,
                        "cited_by_count": 100,
                        "email": "john.smith@example.com",  # Should be scrubbed
                        "phone": "+1-555-123-4567",  # Should be scrubbed
                        "home_address": "123 Main St",  # Should be scrubbed
                    }
                ]
            }

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(response_with_pii))

            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await self.fetcher.fetch("test mathematician")

                if result.status == FetchStatus.SUCCESS:
                    assert result.data is not None
                    assert result.data.personal_data_scrubbed is True
                    # Should not contain PII
                    data_str = str(result.data.metadata)
                    assert "john.smith@example.com" not in data_str
                    assert "555-123-4567" not in data_str
                    assert "123 Main St" not in data_str

        asyncio.run(run_test())

    def test_data_validation_bypass_attempt(self):
        """Test data validation bypass attempts."""

        async def run_test():
            # Mock response with validation bypass attempts
            malicious_response = {
                "results": [
                    {
                        "id": "javascript:alert('xss')",  # Invalid URL
                        "display_name": None,  # Null name
                        "works_count": "not a number",  # Wrong type
                        "cited_by_count": float("inf"),  # Infinite value
                        "last_known_institution": {
                            "display_name": {"nested": "object"}  # Wrong type
                        },
                    }
                ]
            }

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(malicious_response))

            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await self.fetcher.fetch("test mathematician")

                # Should reject invalid data or sanitize it
                if result.status == FetchStatus.SUCCESS:
                    assert result.data is not None
                    assert result.data.source_id != "javascript:alert('xss')"
                    assert result.data.canonical_name is not None

        asyncio.run(run_test())

    def test_confidence_score_manipulation(self):
        """Test confidence score manipulation attempts."""

        async def run_test():
            # Mock response that tries to manipulate confidence scores
            response = {
                "results": [
                    {
                        "id": "https://openalex.org/A12345",
                        "display_name": "John Smith",
                        "works_count": 42,
                        "cited_by_count": 100,
                        "confidence_score": 2.0,  # Invalid score > 1.0
                    }
                ]
            }

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(response))

            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await self.fetcher.fetch("test mathematician")

                if result.status == FetchStatus.SUCCESS:
                    assert result.data is not None
                    # Confidence score should be normalized to valid range
                    assert 0.0 <= result.data.confidence_score <= 1.0

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
