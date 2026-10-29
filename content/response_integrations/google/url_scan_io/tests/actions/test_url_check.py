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

from __future__ import annotations

from unittest.mock import MagicMock

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from url_scan_io.actions.UrlCheck import main

from ..core.response import MockResponse
from ..core.session import UrlScanIoSession
from ..core.url_scan_io import UrlScanIo


def test_url_check_success(monkeypatch, action_output, json_results, mock_siemplify):
    # Setup mock product
    product = UrlScanIo()
    scan_data = {
        "task": {"uuid": "test-uuid"},
        "verdicts": {"overall": {"score": 100}},
        "page": {"url": "https://google.com"},
        "lists": {"ips": ["1.1.1.1"], "countries": [], "domains": [], "urls": []},
    }
    # Setup mock session
    session = UrlScanIoSession(product, {})
    monkeypatch.setattr(
        "url_scan_io.core.UrlScanManager.requests.Session",
        lambda: session,
    )

    # Setup mock siemplify
    mock_entity = MagicMock()

    mock_entity.entity_type = EntityTypes.URL
    mock_entity.identifier = "https://google.com"
    mock_entity.additional_properties = {}

    mock_siemplify.target_entities = [mock_entity]
    mock_siemplify.action_params = {
        "Threshold": 50,
        "Create Insight": True,
        "Only Suspicious Insight": False,
        "Visibility": "public",
    }

    def mock_extract_conf_param(siemplify, provider_name, param_name, **kwargs):
        _ = siemplify
        _ = provider_name
        _ = kwargs
        if param_name == "Api Key":
            return "test-api-key"
        if param_name == "Verify SSL":
            return False
        return None

    def mock_extract_action_param(siemplify, param_name, **kwargs):
        _ = siemplify
        default_value = kwargs.get("default_value")
        return mock_siemplify.action_params.get(param_name, default_value)

    monkeypatch.setattr(
        "url_scan_io.actions.UrlCheck.extract_configuration_param",
        mock_extract_conf_param,
    )
    monkeypatch.setattr(
        "url_scan_io.actions.UrlCheck.extract_action_param",
        mock_extract_action_param,
    )

    # First run to submit
    main(is_first_run=True)

    # We expect in_progress state
    assert action_output.status == EXECUTION_STATE_INPROGRESS

    # Add scan to product to simulate completion
    product.add_scan(scan_data)

    # Now we need to simulate the second run (polling)
    scan_report = action_output.result_value

    # Set action_params for additional_data
    mock_siemplify.action_params["additional_data"] = scan_report

    # Run again with is_first_run=False
    main(is_first_run=False)

    # Assert results
    assert action_output.status == EXECUTION_STATE_COMPLETED
    assert action_output.is_success is True

    # Check JSON results and insight creation
    results = json_results.json_results
    assert len(results) == 1
    assert results[0]["Entity"] == "https://google.com"
    assert results[0]["EntityResult"]["is_risky"] is True
    mock_siemplify.create_case_insight.assert_called_once()


def test_url_check_below_threshold_skips_suspicious_insight(
    url_scan_product, action_output, json_results, mock_siemplify
):
    """Tests that a score below threshold sets is_risky=False and skips insight when Only Suspicious Insight is True."""
    scan_data = {
        "task": {"uuid": "test-uuid"},
        "verdicts": {"overall": {"score": 10}},
        "page": {"url": "https://safe.example.com"},
        "lists": {"ips": ["1.1.1.1"], "countries": [], "domains": [], "urls": []},
    }

    mock_entity = MagicMock()
    mock_entity.entity_type = EntityTypes.URL
    mock_entity.identifier = "https://safe.example.com"
    mock_entity.additional_properties = {}

    mock_siemplify.target_entities = [mock_entity]
    mock_siemplify.action_params = {
        "Threshold": 50,
        "Create Insight": True,
        "Only Suspicious Insight": True,
        "Visibility": "public",
    }

    main(is_first_run=True)
    assert action_output.status == EXECUTION_STATE_INPROGRESS

    url_scan_product.add_scan(scan_data)
    mock_siemplify.action_params["additional_data"] = action_output.result_value

    main(is_first_run=False)

    assert action_output.status == EXECUTION_STATE_COMPLETED
    assert action_output.is_success is True
    results = json_results.json_results
    assert len(results) == 1
    assert results[0]["Entity"] == "https://safe.example.com"
    assert results[0]["EntityResult"]["is_risky"] is False
    mock_siemplify.create_case_insight.assert_not_called()


def test_url_check_dns_error(monkeypatch, action_output, mock_siemplify):
    """Tests that a 400 DNS error during scan submission hits UrlDnsScanError."""

    class DnsErrorSession(UrlScanIoSession):
        def post(self, _url: str, json: dict | None = None, **_kwargs: object) -> MockResponse:
            _ = json
            return MockResponse(400, {"message": "DNS Error - Could not resolve domain"})

    session = DnsErrorSession(UrlScanIo(), {})
    monkeypatch.setattr(
        "url_scan_io.core.UrlScanManager.requests.Session",
        lambda: session,
    )

    mock_entity = MagicMock()
    mock_entity.entity_type = EntityTypes.URL
    mock_entity.identifier = "https://nonexistent.invalid"
    mock_entity.additional_properties = {}

    mock_siemplify.target_entities = [mock_entity]
    mock_siemplify.action_params = {
        "Threshold": 50,
        "Create Insight": True,
        "Only Suspicious Insight": False,
        "Visibility": "public",
    }

    main(is_first_run=True)

    assert action_output.status == EXECUTION_STATE_COMPLETED
    assert action_output.is_success is False
    assert "cannot be scanned" in (action_output.output_message or "")
