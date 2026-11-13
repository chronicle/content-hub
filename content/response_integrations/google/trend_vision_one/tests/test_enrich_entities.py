# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the Trend Vision One Enrich Entities action."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import DomainEntityInfo, EntityTypes

from ..actions import EnrichEntities
from ..core.constants import REQUEST_TIMEOUT_SECONDS
from ..core.datamodels import Endpoint
from ..core.TrendVisionOneExceptions import TrendVisionOneException
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.TrendVisionOneParser import TrendVisionOneParser
from .common import get_json_by_entity, get_summary_lines, make_entity, run_action
from .test_action_result_summary import make_http_error, make_response

AGENT_GUID = "3573f000-0000-0000-0000-000000000001"


def make_endpoint() -> Endpoint:
    """Build an endpoint from a raw eiqs endpoint record."""
    return TrendVisionOneParser.build_endpoint_obj({
        "agentGuid": AGENT_GUID,
        "osDescription": "CentOS 7",
        "loginAccount": {"value": ["root"]},
        "endpointName": {"value": "host-1"},
        "ip": {"value": ["10.0.0.1"]},
        "installedProductCodes": ["xes"],
    })


def make_domain_entity(identifier: str, entity_type: str) -> MagicMock:
    """Build a target entity that passes the DomainEntityInfo type check of the action."""
    entity = make_entity(identifier, entity_type)
    entity.__class__ = DomainEntityInfo

    return entity


class TestEnrichEntities:
    """Tests for the isolation status, failure reasons, and summary line of Enrich Entities."""

    @pytest.mark.parametrize(
        ("entity_type", "search_param", "isolation_status"),
        [(EntityTypes.ADDRESS, "ip", "on"), (EntityTypes.HOSTNAME, "hostname", "off")],
    )
    def test_entity_success_reports_isolation_status(
        self,
        entity_type: str,
        search_param: str,
        isolation_status: str,
    ) -> None:
        """Test that a found entity keeps the raw endpoint keys and gets its isolation status."""
        entity = make_domain_entity("target-1", entity_type)
        endpoint = make_endpoint()

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.return_value = endpoint
            manager.get_endpoint_isolation_status.return_value = isolation_status

        mock_siemplify = run_action(EnrichEntities, {}, setup, [entity])

        assert get_json_by_entity(mock_siemplify)["target-1"] == {
            **endpoint.raw_data,
            "isolationStatus": isolation_status,
        }
        assert entity.additional_properties["TrendVisionOne_isolationStatus"] == isolation_status
        assert entity.additional_properties["TrendVisionOne_endpoint_name"] == "host-1"
        assert entity.is_enriched is True
        table_identifier, table = mock_siemplify.result.add_entity_table.call_args.args
        assert table_identifier == "target-1"
        assert any("isolationStatus" in row and isolation_status in row for row in table)
        message, result_value, status = mock_siemplify.end.call_args.args
        assert message.startswith("Successfully enriched the following entities")
        assert (result_value, status) == (True, EXECUTION_STATE_COMPLETED)
        assert get_summary_lines(mock_siemplify) == [
            {
                "outcome": "SUCCESS",
                "error_type": "NONE",
                "execution_state": "COMPLETED",
                "targets": "1",
                "failed": "0",
                "skipped": "0",
                "exc_type": "NONE",
                "http_status": "NONE",
            }
        ]

    def test_entity_search_uses_entity_type_field(self) -> None:
        """Test that an address searches by IP and a hostname searches by endpoint name."""
        entities = [make_domain_entity("10.0.0.1", EntityTypes.ADDRESS), make_domain_entity("h", EntityTypes.HOSTNAME)]
        calls: list[dict[str, str]] = []

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.side_effect = lambda **kwargs: calls.append(kwargs) or make_endpoint()
            manager.get_endpoint_isolation_status.return_value = "off"

        run_action(EnrichEntities, {}, setup, entities)

        assert calls == [{"ip": "10.0.0.1"}, {"hostname": "h"}]

    def test_agent_uuid_success_reports_isolation_status(self) -> None:
        """Test that an Agent UUID result is keyed by the endpoint GUID and has the isolation status."""
        endpoint = make_endpoint()
        isolation_calls: list[str] = []

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.return_value = endpoint
            manager.get_endpoint_isolation_status.side_effect = lambda guid: isolation_calls.append(guid) or "on"

        mock_siemplify = run_action(EnrichEntities, {"Agent UUID": AGENT_GUID}, setup)

        assert get_json_by_entity(mock_siemplify) == {AGENT_GUID: {**endpoint.raw_data, "isolationStatus": "on"}}
        assert isolation_calls == [AGENT_GUID]
        mock_siemplify.result.add_entity_table.assert_not_called()
        message, result_value, _ = mock_siemplify.end.call_args.args
        assert AGENT_GUID in message
        assert result_value is True
        assert get_summary_lines(mock_siemplify)[0]["outcome"] == "SUCCESS"

    def test_duplicate_agent_uuids_processed_once(self) -> None:
        """Test that a repeated Agent UUID is looked up once and counts as one target."""

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.return_value = make_endpoint()
            manager.get_endpoint_isolation_status.return_value = "on"

        mock_siemplify = run_action(EnrichEntities, {"Agent UUID": f"{AGENT_GUID}, {AGENT_GUID}"}, setup)

        mock_siemplify.LOGGER.exception.assert_not_called()
        assert mock_siemplify.end.call_args.args[0].count(AGENT_GUID) == 1
        assert get_summary_lines(mock_siemplify)[0]["targets"] == "1"

    @pytest.mark.parametrize(
        "isolation_lookup",
        [{"side_effect": make_http_error(403)}, {"return_value": None}],
        ids=["permission_denied", "no_value"],
    )
    def test_isolation_lookup_failure_keeps_success(self, isolation_lookup: dict[str, Any]) -> None:
        """Test that a failed or empty isolation lookup reports unknown and keeps the entity successful."""
        entity = make_domain_entity("10.0.0.1", EntityTypes.ADDRESS)

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.return_value = make_endpoint()
            manager.get_endpoint_isolation_status.configure_mock(**isolation_lookup)

        mock_siemplify = run_action(EnrichEntities, {}, setup, [entity])

        assert get_json_by_entity(mock_siemplify)["10.0.0.1"]["isolationStatus"] == "unknown"
        assert entity.additional_properties["TrendVisionOne_isolationStatus"] == "unknown"
        assert mock_siemplify.end.call_args.args[1:] == (True, EXECUTION_STATE_COMPLETED)
        assert mock_siemplify.LOGGER.exception.call_count == int("side_effect" in isolation_lookup)
        summary = get_summary_lines(mock_siemplify)[0]
        assert (summary["outcome"], summary["failed"]) == ("SUCCESS", "0")

    def test_not_found_entity_gets_error_type(self) -> None:
        """Test that a not found entity gets an error entry and the found entity still succeeds."""
        entities = [
            make_domain_entity("found", EntityTypes.HOSTNAME),
            make_domain_entity("missing", EntityTypes.HOSTNAME),
        ]

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.side_effect = lambda hostname: make_endpoint() if hostname == "found" else None
            manager.get_endpoint_isolation_status.return_value = "off"

        mock_siemplify = run_action(EnrichEntities, {}, setup, entities)

        json_result = get_json_by_entity(mock_siemplify)
        assert json_result["found"]["isolationStatus"] == "off"
        assert json_result["missing"] == {
            "error": "Endpoint was not found in Trend Vision One.",
            "error_type": "ENDPOINT_NOT_FOUND",
        }
        message, result_value, status = mock_siemplify.end.call_args.args
        assert "found" in message.split("\n\n")[0]
        assert message.endswith("using information from Trend Vision One: missing\n")
        assert (result_value, status) == (True, EXECUTION_STATE_COMPLETED)
        summary = get_summary_lines(mock_siemplify)[0]
        assert (summary["outcome"], summary["error_type"], summary["failed"]) == (
            "PARTIAL_SUCCESS",
            "ENDPOINT_NOT_FOUND",
            "1",
        )

    def test_all_not_found_reports_json_result(self) -> None:
        """Test that failed targets get JSON entries when no target succeeds."""

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.return_value = None

        mock_siemplify = run_action(EnrichEntities, {"Agent UUID": AGENT_GUID}, setup)

        assert get_json_by_entity(mock_siemplify)[AGENT_GUID]["error_type"] == "ENDPOINT_NOT_FOUND"
        assert mock_siemplify.end.call_args.args == (
            "None of the provided entities were enriched.",
            False,
            EXECUTION_STATE_COMPLETED,
        )
        summary = get_summary_lines(mock_siemplify)[0]
        assert (summary["outcome"], summary["error_type"]) == ("FAILURE", "ENDPOINT_NOT_FOUND")

    def test_exception_per_target_continues_others(self) -> None:
        """Test that a lookup error fails only its target and is classified."""
        entities = [make_domain_entity("broken", EntityTypes.HOSTNAME), make_domain_entity("ok", EntityTypes.HOSTNAME)]

        def search(hostname: str | None = None, agent_id: str | None = None) -> Endpoint:
            if hostname == "broken":
                raise make_http_error(500)
            if agent_id:
                raise requests.ConnectionError("down")
            return make_endpoint()

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.side_effect = search
            manager.get_endpoint_isolation_status.return_value = "on"

        mock_siemplify = run_action(EnrichEntities, {"Agent UUID": AGENT_GUID}, setup, entities)

        json_result = get_json_by_entity(mock_siemplify)
        assert json_result["broken"]["error_type"] == "VENDOR_ERROR"
        assert json_result[AGENT_GUID] == {"error": "down", "error_type": "CONNECTION_ERROR"}
        assert json_result["ok"]["isolationStatus"] == "on"
        assert mock_siemplify.end.call_args.args[1:] == (True, EXECUTION_STATE_COMPLETED)
        assert mock_siemplify.LOGGER.exception.call_count == 2
        summary = get_summary_lines(mock_siemplify)[0]
        assert (summary["outcome"], summary["targets"], summary["failed"], summary["error_type"]) == (
            "PARTIAL_SUCCESS",
            "3",
            "2",
            "CONNECTION_ERROR",
        )

    def test_run_ending_exception_logs_summary(self) -> None:
        """Test that a connectivity failure ends the run as FAILED with a JSON failure entry per target."""
        entity = make_domain_entity("10.0.0.1", EntityTypes.ADDRESS)
        error = make_http_error(401)

        def setup(manager: MagicMock) -> None:
            manager.test_connectivity.side_effect = error

        mock_siemplify = run_action(EnrichEntities, {"Agent UUID": AGENT_GUID}, setup, [entity])

        failure = {"error": str(error), "error_type": "AUTHENTICATION_FAILED"}
        assert get_json_by_entity(mock_siemplify) == {"10.0.0.1": failure, AGENT_GUID: failure}
        assert mock_siemplify.end.call_args.args[1:] == (False, EXECUTION_STATE_FAILED)
        assert get_summary_lines(mock_siemplify) == [
            {
                "outcome": "FAILURE",
                "error_type": "AUTHENTICATION_FAILED",
                "execution_state": "FAILED",
                "targets": "2",
                "failed": "2",
                "skipped": "0",
                "exc_type": "TrendVisionOneException",
                "http_status": "401",
            }
        ]

    def test_summary_counts_skipped_entities(self) -> None:
        """Test that unsupported entities count as skipped and not as targets."""
        entities = [
            make_domain_entity("10.0.0.1", EntityTypes.ADDRESS),
            make_domain_entity("http://x", EntityTypes.URL),
            make_domain_entity("abc", EntityTypes.FILEHASH),
        ]

        def setup(manager: MagicMock) -> None:
            manager.search_endpoint.return_value = make_endpoint()
            manager.get_endpoint_isolation_status.return_value = "off"

        mock_siemplify = run_action(EnrichEntities, {"Agent UUID": AGENT_GUID}, setup, entities)

        summary = get_summary_lines(mock_siemplify)[0]
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("2", "0", "2")


class TestGetEndpointIsolationStatus:
    """Tests for the isolation status lookup of the manager."""

    def make_manager(self, response: requests.Response) -> TrendVisionOneManager:
        """Build a manager whose session returns a fixed response."""
        manager = TrendVisionOneManager(api_root="https://api.example.com", api_token="token", verify_ssl=True)
        manager.session = MagicMock()
        manager.session.get.return_value = response

        return manager

    def test_returns_isolation_status(self) -> None:
        """Test that the manager reads isolationStatus from the endpoint details API."""
        manager = self.make_manager(make_response(200, b'{"agentGuid": "g", "isolationStatus": "on"}'))

        assert manager.get_endpoint_isolation_status("g") == "on"
        manager.session.get.assert_called_once_with(
            "https://api.example.com/v3.0/endpointSecurity/endpoints/g",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    def test_raises_on_http_error(self) -> None:
        """Test that an HTTP error from the endpoint details API raises a Trend Vision One error."""
        manager = self.make_manager(make_response(403, b'{"error": {"message": "Insufficient permissions"}}'))

        with pytest.raises(TrendVisionOneException, match="Insufficient permissions"):
            manager.get_endpoint_isolation_status("g")
