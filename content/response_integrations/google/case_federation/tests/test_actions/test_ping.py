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
from unittest.mock import MagicMock

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from ...actions import ping
from ...core.constants import GCP_PROJECT_ID_ENV_VAR

if TYPE_CHECKING:
    import pytest
    import requests
    from integration_testing.platform.script_output import MockActionOutput


@set_metadata(integration_config={"Verify SSL": "true"})
def test_ping_success(
    monkeypatch: pytest.MonkeyPatch,
    script_session: requests.Session,
    action_output: MockActionOutput,
) -> None:
    mock_creds = MagicMock()
    mock_get_creds = MagicMock(return_value=mock_creds)
    monkeypatch.setenv(GCP_PROJECT_ID_ENV_VAR, "test-gcp-project")
    monkeypatch.setattr(ping, "get_secops_siem_tenant_credentials", mock_get_creds)

    ping.main()

    mock_get_creds.assert_called_once()
    assert mock_get_creds.call_args.kwargs["quota_project_id"] == "test-gcp-project"
    mock_creds.refresh.assert_called_once()
    assert script_session.verify is True
    assert action_output.results == ActionOutput(
        output_message=ping.SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


@set_metadata(integration_config={"Verify SSL": "false"})
def test_ping_verify_ssl_false(
    monkeypatch: pytest.MonkeyPatch,
    script_session: requests.Session,
    action_output: MockActionOutput,
) -> None:
    mock_creds = MagicMock()
    mock_get_creds = MagicMock(return_value=mock_creds)
    monkeypatch.setattr(ping, "get_secops_siem_tenant_credentials", mock_get_creds)

    ping.main()

    mock_creds.refresh.assert_called_once()
    assert script_session.verify is False
    assert action_output.results == ActionOutput(
        output_message=ping.SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


@set_metadata(integration_config={"Verify SSL": True})
def test_ping_failure(monkeypatch: pytest.MonkeyPatch, action_output: MockActionOutput) -> None:
    error_reason = "SIEM tenant short-lived service account email not found in SOAR context"
    mock_get_creds = MagicMock(side_effect=RuntimeError(error_reason))
    monkeypatch.setattr(ping, "get_secops_siem_tenant_credentials", mock_get_creds)

    ping.main()

    assert action_output.results == ActionOutput(
        output_message=f"{ping.ERROR_MESSAGE}\nReason: {error_reason}",
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
