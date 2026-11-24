from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock
import pytest

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from tenable_io.actions.EnrichEntities import main
from tenable_io.tests.conftest import (
    LegacyActionOutput,
    MockSiemplifyEntity,
)
from tenable_io.tests.core.response import MockResponse


class TestEnrichEntitiesCaching:
    """Tests for the Tenable.io "Enrich Entities" action focusing on caching."""

    def test_enrich_entities_uses_cached_uuid(
        self,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that action uses cached export UUID if valid."""
        action_params["Create Insight"] = False
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS"),
        ]

        mock_siemplify.environment = "TestEnv"
        mock_siemplify.integration_instance = "TestInstance"

        # Mock context properties
        context_data = {
            "export_uuid": "cached-uuid-123",
            "export_timestamp": str(int(time.time())),
        }
        mock_siemplify.get_context_property.side_effect = (
            lambda **kwargs: context_data.get(kwargs.get("property_key"))
        )

        # Mock requests.Session.request to return success for status check
        mock_request = MagicMock()
        mock_request.return_value = MockResponse(
            {"status": "FINISHED", "chunks_available": []}, 200
        )
        monkeypatch.setattr("requests.Session.request", mock_request)

        main()

        # Verify initiate_assets_export was NOT called (no POST to export endpoint)
        for call in mock_request.call_args_list:
            args, _ = call
            if len(args) > 0 and args[0] == "POST" and "export" in args[1]:
                assert False, "initiate_assets_export was called unexpectedly."

        # Verify status was checked for cached UUID
        called_get = False
        for call in mock_request.call_args_list:
            args, _ = call
            if len(args) > 0 and args[0] == "GET" and "cached-uuid-123" in args[1]:
                called_get = True
                break
        assert called_get, "Status check for cached UUID was not called."

    def test_enrich_entities_regenerates_uuid_if_expired(
        self,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that action regenerates export UUID if cached one is expired."""
        action_params["Create Insight"] = False
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS"),
        ]

        mock_siemplify.environment = "TestEnv"
        mock_siemplify.integration_instance = "TestInstance"

        # Mock context properties (expired: 2 hours ago)
        context_data = {
            "export_uuid": "cached-uuid-123",
            "export_timestamp": str(int(time.time()) - 7200),
        }
        mock_siemplify.get_context_property.side_effect = (
            lambda **kwargs: context_data.get(kwargs.get("property_key"))
        )

        # Mock requests.Session.request to return new UUID then success for status
        mock_request = MagicMock()
        mock_request.side_effect = [
            MockResponse({"export_uuid": "new-uuid-456"}, 200),
            MockResponse({"status": "FINISHED", "chunks_available": []}, 200),
        ]
        monkeypatch.setattr("requests.Session.request", mock_request)

        main()

        # Verify initiate_assets_export WAS called (POST to export endpoint)
        called_post = False
        for call in mock_request.call_args_list:
            args, _ = call
            if len(args) > 0 and args[0] == "POST" and "export" in args[1]:
                called_post = True
                break
        assert called_post, "initiate_assets_export was not called."

        # Verify new UUID was saved to context
        mock_siemplify.set_context_property.assert_any_call(
            context_type=0,
            identifier="testenv_testinstance_TenableIO",
            property_key="export_uuid",
            property_value="new-uuid-456",
        )

    def test_enrich_entities_handles_429_duplicate_export(
        self,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that action handles 429 Duplicate Export by extracting UUID."""
        action_params["Create Insight"] = False
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS"),
        ]

        mock_siemplify.environment = "TestEnv"
        mock_siemplify.integration_instance = "TestInstance"

        # No cached data
        mock_siemplify.get_context_property.return_value = None

        # Mock requests.Session.request to return 429 with specific message
        mock_request = MagicMock()
        mock_request.side_effect = [
            MockResponse(
                {
                    "message": (
                        "Duplicate export not allowed. "
                        "job_uuid=12345678-1234-1234-1234-123456789012"
                    )
                },
                429,
            ),
            MockResponse(
                {"status": "FINISHED", "chunks_available": []}, 200
            ),  # For status check
        ]
        monkeypatch.setattr("requests.Session.request", mock_request)

        main()

        # Verify it did NOT retry for POST (request called once for post,
        # once for get status)
        calls = mock_request.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "POST"
        assert calls[1][0][0] == "GET"
        assert action_output.status == EXECUTION_STATE_COMPLETED

        # Verify extracted UUID was saved to context
        mock_siemplify.set_context_property.assert_any_call(
            context_type=0,
            identifier="testenv_testinstance_TenableIO",
            property_key="export_uuid",
            property_value="12345678-1234-1234-1234-123456789012",
        )

    def test_enrich_entities_handles_429_rate_limit(
        self,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that action handles regular 429 rate limit by retrying."""
        action_params["Create Insight"] = False
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS"),
        ]

        mock_siemplify.environment = "TestEnv"
        mock_siemplify.integration_instance = "TestInstance"

        # No cached data
        mock_siemplify.get_context_property.return_value = None

        # Mock requests.Session.request to return regular 429 then 200
        mock_request = MagicMock()
        mock_request.side_effect = [
            MockResponse({"message": "Too Many Requests"}, 429),
            MockResponse({"export_uuid": "mock-uuid-123"}, 200),
            MockResponse({"status": "FINISHED", "chunks_available": []}, 200),
        ]
        monkeypatch.setattr("requests.Session.request", mock_request)

        # Mock time.sleep to avoid waiting in tests
        monkeypatch.setattr("time.sleep", lambda s: None)

        main()

        # Verify it retried (request called at least twice for post)
        calls = mock_request.call_args_list
        assert calls[0][0][0] == "POST"
        assert calls[1][0][0] == "POST"
        assert action_output.status == EXECUTION_STATE_COMPLETED

    def test_enrich_entities_handles_429_on_chunk_download(
        self,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that action handles 429 on chunk download by retrying."""
        action_params["Create Insight"] = False
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS"),
        ]

        mock_siemplify.environment = "TestEnv"
        mock_siemplify.integration_instance = "TestInstance"

        # No cached data
        mock_siemplify.get_context_property.return_value = None

        # Mock requests.Session.request
        mock_request = MagicMock()
        mock_request.side_effect = [
            MockResponse({"export_uuid": "mock-uuid-123"}, 200),  # 1. Initiate export
            MockResponse(
                {"status": "FINISHED", "chunks_available": [1]}, 200
            ),  # 2. Status check
            MockResponse(
                {"message": "Too Many Requests"}, 429
            ),  # 3. First chunk download fails
            MockResponse(
                [{"id": "asset_1"}], 200
            ),  # 4. Retry of chunk download succeeds
        ]
        monkeypatch.setattr("requests.Session.request", mock_request)

        # Mock time.sleep to avoid waiting in tests
        monkeypatch.setattr("time.sleep", lambda s: None)

        main()

        # Verify it retried the chunk download (total calls should be at least 4)
        assert mock_request.call_count >= 4
        calls = mock_request.call_args_list
        # Verify third call was a GET to chunks/1
        assert calls[2][0][0] == "GET"
        assert "chunks/1" in calls[2][0][1]
        # Verify fourth call was also a GET to chunks/1 (retry)
        assert calls[3][0][0] == "GET"
        assert "chunks/1" in calls[3][0][1]
        assert action_output.status == EXECUTION_STATE_COMPLETED
