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

"""Tests for the Ping action."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from sap_erp.actions import ping
from sap_erp.actions.ping import SUCCESS_MESSAGE
from sap_erp.core.exceptions import SapErpAuthError
from sap_erp.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from .conftest import ResponseFactory

# Exact wording required by the repository style guide.
EXPECTED_SUCCESS = (
    "Successfully connected to the SAP ERP server with the provided connection parameters!"
)
EXPECTED_FAILURE_PREFIX = "Failed to connect to the SAP ERP server!\nReason: "


def assert_failed(action_output: MockActionOutput, error: str) -> None:
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.output_message.startswith(EXPECTED_FAILURE_PREFIX)
    assert error in action_output.results.output_message


def test_success_message_matches_style_guide() -> None:
    assert SUCCESS_MESSAGE == EXPECTED_SUCCESS


# The gateway only accepts POST, so a healthy service answers GET with 405.
@pytest.mark.parametrize("status_code", [200, 405])
@set_metadata(integration_config_file_path=CONFIG_PATH)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.ping")
def test_healthy(
    mock_ping: MagicMock,
    make_response: ResponseFactory,
    status_code: int,
    action_output: MockActionOutput,
) -> None:
    mock_ping.return_value = make_response(
        status_code, {"error": "Only POST requests are supported."}
    )

    ping.main()

    mock_ping.assert_called_once_with()
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.output_message == EXPECTED_SUCCESS


@pytest.mark.parametrize("status_code", [401, 403])
@set_metadata(integration_config_file_path=CONFIG_PATH)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.ping")
def test_iam_rejected(
    mock_ping: MagicMock,
    make_response: ResponseFactory,
    status_code: int,
    action_output: MockActionOutput,
) -> None:
    mock_ping.return_value = make_response(status_code, text="Forbidden")

    ping.main()

    assert_failed(
        action_output, f"Authentication to Cloud Run failed (HTTP {status_code})"
    )
    assert "roles/run.invoker" in action_output.results.output_message


@set_metadata(integration_config_file_path=CONFIG_PATH)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.ping")
def test_unexpected_status(
    mock_ping: MagicMock,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    mock_ping.return_value = make_response(503, {"error": "Service Unavailable"})

    ping.main()

    assert_failed(
        action_output,
        "Cloud Run service returned unexpected HTTP 503: Service Unavailable",
    )


@set_metadata(integration_config_file_path=CONFIG_PATH)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.ping")
def test_token_failure(
    mock_ping: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_ping.side_effect = SapErpAuthError("no creds")

    ping.main()

    assert_failed(
        action_output, "Failed to generate Google Cloud authentication token."
    )


@set_metadata(integration_config_file_path=CONFIG_PATH)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.ping")
def test_network_error(
    mock_ping: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_ping.side_effect = requests.exceptions.ConnectionError("DNS failure")

    ping.main()

    assert_failed(action_output, "Network error: DNS failure")
