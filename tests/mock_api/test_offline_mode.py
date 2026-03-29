"""
Mock API server tests for offline mode.

Provides mock implementations of all external APIs for testing without network.
"""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest


class MockOpenAlexAPI:
    """Mock OpenAlex API for testing."""

    def __init__(self):
        self.responses = {}
        self.call_count = 0
        self.last_query = None
        self.rate_limit_count = 0

    def add_response(self, query: str, response: Dict[str, Any]):
        """Add a mock response for a query."""
        self.responses[query.lower()] = response

    def add_person_response(self, name: str, openalex_id: str, orcid: str = None):
        """Add a mock person response."""
        response = {
            "id": f"https://openalex.org/{openalex_id}",
            "display_name": name,
            "orcid": f"https://orcid.org/{orcid}" if orcid else None,
            "works_count": 42,
            "cited_by_count": 1337,
            "last_known_institution": {
                "id": "https://openalex.org/I1234567890",
                "display_name": "Test University",
                "country_code": "US",
            },
            "x_concepts": [
                {
                    "id": "https://openalex.org/C33923547",
                    "display_name": "Mathematics",
                    "score": 0.8,
                }
            ],
            "updated_date": "2025-01-01T00:00:00.000000",
        }
        self.add_response(name, {"results": [response]})

    def add_not_found_response(self, name: str):
        """Add a not found response."""
        self.add_response(name, {"results": []})

    async def fetch(self, query: str) -> Dict[str, Any]:
        """Mock fetch method."""
        self.call_count += 1
        self.last_query = query

        # Simulate rate limiting
        if self.rate_limit_count > 0:
            self.rate_limit_count -= 1
            raise Exception("Rate limit exceeded")

        # Return mock response
        response = self.responses.get(query.lower(), {"results": []})
        return response


class MockCrossrefAPI:
    """Mock Crossref API for testing."""

    def __init__(self):
        self.responses = {}
        self.call_count = 0

    def add_response(self, query: str, response: Dict[str, Any]):
        """Add a mock response."""
        self.responses[query.lower()] = response

    def add_author_response(self, name: str, doi_prefix: str = "10.1000"):
        """Add a mock author response."""
        response = {
            "status": "ok",
            "message": {
                "items": [
                    {
                        "DOI": f"{doi_prefix}/test.doi",
                        "title": ["Test Article"],
                        "author": [
                            {
                                "given": name.split(", ")[1] if ", " in name else name,
                                "family": (
                                    name.split(", ")[0] if ", " in name else "Unknown"
                                ),
                                "ORCID": "http://orcid.org/0000-0003-1234-5678",
                            }
                        ],
                        "publisher": "Test Publisher",
                        "issued": {"date-parts": [[2024, 1, 1]]},
                    }
                ]
            },
        }
        self.add_response(name, response)

    async def fetch(self, query: str) -> Dict[str, Any]:
        """Mock fetch method."""
        self.call_count += 1
        return self.responses.get(query.lower(), {"message": {"items": []}})


class MockORCIDAPI:
    """Mock ORCID API for testing."""

    def __init__(self):
        self.responses = {}
        self.call_count = 0

    def add_response(self, orcid: str, response: Dict[str, Any]):
        """Add a mock response."""
        self.responses[orcid] = response

    def add_profile_response(self, orcid: str, name: str):
        """Add a mock profile response."""
        response = {
            "orcid-identifier": {"uri": f"https://orcid.org/{orcid}", "path": orcid},
            "person": {
                "name": {
                    "given-names": {
                        "value": name.split(", ")[1] if ", " in name else name
                    },
                    "family-name": {
                        "value": name.split(", ")[0] if ", " in name else "Unknown"
                    },
                },
                "biography": {"content": "Test biography"},
                "researcher-urls": {"researcher-url": []},
            },
            "activities-summary": {
                "works": {"group": []},
                "educations": {"affiliation-group": []},
                "employments": {"affiliation-group": []},
            },
        }
        self.add_response(orcid, response)

    async def fetch(self, orcid: str) -> Dict[str, Any]:
        """Mock fetch method."""
        self.call_count += 1
        return self.responses.get(orcid, {})


class MockAPIServer:
    """Mock API server that coordinates all mock APIs."""

    def __init__(self):
        self.openalex = MockOpenAlexAPI()
        self.crossref = MockCrossrefAPI()
        self.orcid = MockORCIDAPI()
        self.offline_mode = True

    def setup_test_data(self):
        """Set up common test data."""
        # Add OpenAlex responses
        self.openalex.add_person_response(
            "Smith, John", "A1234567890", "0000-0003-1234-5678"
        )
        self.openalex.add_person_response(
            "García, María", "A2345678901", "0000-0002-5678-9012"
        )
        self.openalex.add_not_found_response("Nonexistent, Person")

        # Add Crossref responses
        self.crossref.add_author_response("Smith, John")
        self.crossref.add_author_response("García, María")

        # Add ORCID responses
        self.orcid.add_profile_response("0000-0003-1234-5678", "Smith, John")
        self.orcid.add_profile_response("0000-0002-5678-9012", "García, María")

    def get_stats(self) -> Dict[str, int]:
        """Get mock API call statistics."""
        return {
            "openalex_calls": self.openalex.call_count,
            "crossref_calls": self.crossref.call_count,
            "orcid_calls": self.orcid.call_count,
        }


class TestOfflineMode:
    """Test offline mode with mock APIs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = MockAPIServer()
        self.mock_server.setup_test_data()

    @pytest.mark.asyncio
    async def test_openalex_mock_success(self):
        """Test successful OpenAlex mock response."""
        # Mock the actual fetcher
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(
                return_value=Mock(
                    status=Mock(value="success"),
                    data=Mock(
                        source_id="A1234567890",
                        name_variants=["Smith, John", "Smith, J."],
                        identifiers={"ORCID": "0000-0003-1234-5678"},
                        confidence_score=0.9,
                    ),
                )
            )
            mock_class.return_value = mock_instance

            fetcher = mock_class()
            result = await fetcher.fetch("Smith, John")

            assert result.status.value == "success"
            assert result.data.source_id == "A1234567890"
            assert "ORCID" in result.data.identifiers

    @pytest.mark.asyncio
    async def test_openalex_mock_not_found(self):
        """Test OpenAlex mock not found response."""
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(
                return_value=Mock(
                    status=Mock(value="not_found"), error_message="Person not found"
                )
            )
            mock_class.return_value = mock_instance

            fetcher = mock_class()
            result = await fetcher.fetch("Nonexistent, Person")

            assert result.status.value == "not_found"
            assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test rate limit handling with mock."""
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            # First call fails with rate limit
            mock_instance.fetch = AsyncMock(
                side_effect=[
                    Exception("Rate limit exceeded"),
                    Mock(
                        status=Mock(value="success"), data=Mock(source_id="A1234567890")
                    ),
                ]
            )
            mock_class.return_value = mock_instance

            fetcher = mock_class()

            # First call should raise exception
            with pytest.raises(Exception, match="Rate limit exceeded"):
                await fetcher.fetch("Smith, John")

            # Second call should succeed
            result = await fetcher.fetch("Smith, John")
            assert result.status.value == "success"

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test network error handling with mock."""
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(side_effect=Exception("Network error"))
            mock_class.return_value = mock_instance

            fetcher = mock_class()

            with pytest.raises(Exception, match="Network error"):
                await fetcher.fetch("Smith, John")

    def test_offline_mode_configuration(self):
        """Test offline mode configuration."""
        import os

        # Set offline mode
        os.environ["OFFLINE"] = "1"

        # Mock configuration should detect offline mode
        assert self.mock_server.offline_mode is True

        # Clean up
        if "OFFLINE" in os.environ:
            del os.environ["OFFLINE"]

    @pytest.mark.asyncio
    async def test_batch_mock_responses(self):
        """Test batch processing with mock responses."""
        queries = ["Smith, John", "García, María", "Nonexistent, Person"]

        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_responses = [
                Mock(status=Mock(value="success"), data=Mock(source_id="A1234567890")),
                Mock(status=Mock(value="success"), data=Mock(source_id="A2345678901")),
                Mock(status=Mock(value="not_found"), error_message="Not found"),
            ]
            mock_instance.fetch = AsyncMock(side_effect=mock_responses)
            mock_class.return_value = mock_instance

            fetcher = mock_class()

            # Process batch
            results = []
            for query in queries:
                result = await fetcher.fetch(query)
                results.append(result)

            assert len(results) == 3
            assert results[0].status.value == "success"
            assert results[1].status.value == "success"
            assert results[2].status.value == "not_found"

    @pytest.mark.asyncio
    async def test_quota_management_mock(self):
        """Test quota management with mock."""

        # Mock quota manager
        quota_manager = Mock()
        quota_manager.can_fetch = Mock(return_value=True)
        quota_manager.record_fetch = Mock()
        quota_manager.get_remaining_quota = Mock(return_value=100)

        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_instance.quota_manager = quota_manager
            mock_instance.fetch = AsyncMock(
                return_value=Mock(
                    status=Mock(value="success"), data=Mock(source_id="A1234567890")
                )
            )
            mock_class.return_value = mock_instance

            fetcher = mock_class()

            # Check quota before fetch
            assert fetcher.quota_manager.can_fetch() is True

            # Perform fetch
            result = await fetcher.fetch("Smith, John")

            # Verify quota was recorded
            fetcher.quota_manager.record_fetch.assert_called_once()
            assert result.status.value == "success"

    def test_mock_data_persistence(self):
        """Test mock data persistence between calls."""
        # Add new response
        self.mock_server.openalex.add_person_response(
            "New, Person", "A9999999999", "0000-0009-9999-9999"
        )

        # Should persist
        assert "new, person" in self.mock_server.openalex.responses

        # Should be retrievable
        response = self.mock_server.openalex.responses["new, person"]
        assert response["results"][0]["id"] == "https://openalex.org/A9999999999"

    def test_mock_statistics_tracking(self):
        """Test mock API statistics tracking."""
        initial_stats = self.mock_server.get_stats()

        # Simulate API calls
        asyncio.run(self.mock_server.openalex.fetch("Smith, John"))
        asyncio.run(self.mock_server.crossref.fetch("García, María"))
        asyncio.run(self.mock_server.orcid.fetch("0000-0003-1234-5678"))

        final_stats = self.mock_server.get_stats()

        assert final_stats["openalex_calls"] == initial_stats["openalex_calls"] + 1
        assert final_stats["crossref_calls"] == initial_stats["crossref_calls"] + 1
        assert final_stats["orcid_calls"] == initial_stats["orcid_calls"] + 1

    @pytest.mark.asyncio
    async def test_mock_timeout_simulation(self):
        """Test timeout simulation with mock."""
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(
                side_effect=asyncio.TimeoutError("Request timeout")
            )
            mock_class.return_value = mock_instance

            fetcher = mock_class()

            with pytest.raises(asyncio.TimeoutError, match="Request timeout"):
                await fetcher.fetch("Smith, John")

    @pytest.mark.asyncio
    async def test_mock_malformed_response(self):
        """Test handling of malformed mock responses."""
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(
                return_value=Mock(
                    status=Mock(value="error"), error_message="Malformed response"
                )
            )
            mock_class.return_value = mock_instance

            fetcher = mock_class()
            result = await fetcher.fetch("Smith, John")

            assert result.status.value == "error"
            assert "malformed" in result.error_message.lower()

    def test_mock_configuration_validation(self):
        """Test mock configuration validation."""
        # Test invalid response format
        with pytest.raises(Exception):
            self.mock_server.openalex.add_response("test", "invalid_format")

        # Test valid response format
        self.mock_server.openalex.add_response("test", {"results": []})
        assert "test" in self.mock_server.openalex.responses

    @pytest.mark.asyncio
    async def test_concurrent_mock_requests(self):
        """Test concurrent requests with mock."""
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_class:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(
                return_value=Mock(
                    status=Mock(value="success"), data=Mock(source_id="A1234567890")
                )
            )
            mock_class.return_value = mock_instance

            fetcher = mock_class()

            # Make concurrent requests
            tasks = [
                fetcher.fetch("Smith, John"),
                fetcher.fetch("García, María"),
                fetcher.fetch("Brown, Alice"),
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            assert all(r.status.value == "success" for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
