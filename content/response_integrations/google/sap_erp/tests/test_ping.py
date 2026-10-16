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

from typing import TYPE_CHECKING

import pytest
import requests
from TIPCommon.base.action import ExecutionState

from sap_erp.actions.ping import SUCCESS_MESSAGE, PingAction
from sap_erp.core.sap_erp_manager import SapErpAuthError

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from .conftest import ResponseFactory

pytestmark = pytest.mark.usefixtures("mock_soar_action")

# Exact wording required by the repository style guide.
EXPECTED_SUCCESS = (
    "Successfully connected to the SAP ERP server with the provided connection parameters!"
)
EXPECTED_FAILURE_PREFIX = "Failed to connect to the SAP ERP server! Error is "


def build_action(manager: MagicMock) -> PingAction:
    action = PingAction(name="Ping")
    action._api_client = manager
    action.cloud_run_url = "https://gw-abc.a.run.app"
    return action


def assert_failed(action: PingAction, error: str) -> None:
    assert action.result_value is False
    assert action.execution_state == ExecutionState.FAILED
    assert action.output_message.startswith(EXPECTED_FAILURE_PREFIX)
    assert error in action.output_message


def test_success_message_matches_style_guide() -> None:
    assert SUCCESS_MESSAGE == EXPECTED_SUCCESS


# The gateway only accepts POST, so a healthy service answers GET with 405.
@pytest.mark.parametrize("status_code", [200, 405])
def test_healthy(
    manager: MagicMock, make_response: ResponseFactory, status_code: int
) -> None:
    manager.ping.return_value = make_response(
        status_code, {"error": "Only POST requests are supported."}
    )
    action = build_action(manager)

    action._perform_action()

    assert action.result_value is True
    assert action.execution_state == ExecutionState.COMPLETED
    assert action.output_message == EXPECTED_SUCCESS


@pytest.mark.parametrize("status_code", [401, 403])
def test_iam_rejected(
    manager: MagicMock, make_response: ResponseFactory, status_code: int
) -> None:
    manager.ping.return_value = make_response(status_code, text="Forbidden")
    action = build_action(manager)

    action._perform_action()

    assert_failed(action, f"Authentication to Cloud Run failed (HTTP {status_code})")
    assert "roles/run.invoker" in action.output_message


def test_unexpected_status(manager: MagicMock, make_response: ResponseFactory) -> None:
    manager.ping.return_value = make_response(503, {"error": "Service Unavailable"})
    action = build_action(manager)

    action._perform_action()

    assert_failed(
        action, "Cloud Run service returned unexpected HTTP 503: Service Unavailable"
    )


def test_token_failure(manager: MagicMock) -> None:
    manager.ping.side_effect = SapErpAuthError("no creds")
    action = build_action(manager)

    action._perform_action()

    assert_failed(action, "Failed to generate Google Cloud authentication token.")


def test_network_error(manager: MagicMock) -> None:
    manager.ping.side_effect = requests.exceptions.ConnectionError("DNS failure")
    action = build_action(manager)

    action._perform_action()

    assert_failed(action, "Network error: DNS failure")
