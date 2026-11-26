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

import json
from typing import Any
from unittest.mock import MagicMock

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS

from tenable_io.actions.ScanEndpoints import main
from tenable_io.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
)
from tenable_io.tests.core.product import TenableIOProduct


class TestScanEndpointsAction:
    """Tests for the "Scan Endpoints" action."""

    def test_scan_is_successful(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test the full, successful, two-step scan process.

        Verifies that a scan is initiated, transitions to "in progress",
        and then completes successfully, returning JSON results.

        Args:
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
            json_results: The captured JSON results.
            mock_siemplify: The mocked Siemplify API object.
            action_params: The parameters for the action.
        """
        policy_name = "Basic Network Scan"
        scanner_name = "Local Scanner"

        action_params["Scan Name"] = "Test Scan"
        action_params["Policy Name"] = policy_name
        action_params["Scanner Name"] = scanner_name
        action_params["Send Report To"] = "test@example.com"

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS"),
            MockSiemplifyEntity(identifier="HOST1", entity_type="HOSTNAME"),
        ]

        # First run: Initiate scan
        main(is_first_run=True)

        assert action_output.status == EXECUTION_STATE_INPROGRESS
        result_value_json = json.loads(action_output.result_value)
        scan_id = result_value_json["scan_id"]
        assert scan_id is not None
        assert result_value_json["not_found"] == []

        # Second run: Check status and get results
        tenable_io_product.update_scan_status(scan_id, "completed")
        action_params["additional_data"] = action_output.result_value
        main(is_first_run=False)

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully executed scan" in action_output.output_message
        assert action_output.result_value is True
        assert len(json_results.json_results) > 0
        scan_result = json_results.json_results[0]
        assert "vulnerabilities" in scan_result
        assert len(scan_result["vulnerabilities"]) > 0

    def test_scan_waits_for_completion(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test the asynchronous waiting mechanism of the scan.

        Verifies that if a scan is still running on the second check, the
        action remains in an "in progress" state.

        Args:
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
            mock_siemplify: The mocked Siemplify API object.
            action_params: The parameters for the action.
        """
        policy_name = "Basic Network Scan"

        action_params["Scan Name"] = "Test Scan"
        action_params["Policy Name"] = policy_name

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS")
        ]

        main(is_first_run=True)
        scan_id = json.loads(action_output.result_value)["scan_id"]

        tenable_io_product.update_scan_status(scan_id, "running")
        action_params["additional_data"] = action_output.result_value

        main(is_first_run=False)

        assert action_output.status == EXECUTION_STATE_INPROGRESS
        assert "Waiting for the scan" in action_output.output_message

    def test_scan_matches_hostnames(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test robust hostname matching (FQDN, NetBIOS, Short Hostname).

        Verifies that the action correctly identifies target entities based
        on various hostname formats found in the asset data.

        Args:
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
            mock_siemplify: The mocked Siemplify API object.
            action_params: The parameters for the action.
        """
        _ = tenable_io_product
        policy_name = "Basic Network Scan"

        action_params["Scan Name"] = "Robust Match Scan"
        action_params["Policy Name"] = policy_name

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="server.domain.local", entity_type="HOSTNAME"
            ),
            MockSiemplifyEntity(identifier="SERVER-NB", entity_type="HOSTNAME"),
            MockSiemplifyEntity(identifier="server", entity_type="HOSTNAME"),
        ]

        main(is_first_run=True)

        assert action_output.status == EXECUTION_STATE_INPROGRESS
        result_value_json = json.loads(action_output.result_value)

        assert result_value_json["not_found"] == []
