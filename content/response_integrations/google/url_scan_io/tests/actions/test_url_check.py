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

from soar_sdk.ScriptResult import EXECUTION_STATE_INPROGRESS, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyDataModel import EntityTypes
from url_scan_io.tests.core.url_scan_io import UrlScanIo
from url_scan_io.tests.core.session import UrlScanIoSession
from url_scan_io.actions.UrlCheck import main


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
    if action_output.status != EXECUTION_STATE_INPROGRESS:
        print(f"EXCEPTION CALLS: {mock_siemplify.LOGGER.exception.call_args_list}")
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

    # Check JSON results
    results = json_results.json_results
    assert len(results) == 1
    assert results[0]["Entity"] == "https://google.com"
    assert results[0]["EntityResult"]["is_risky"] is True
