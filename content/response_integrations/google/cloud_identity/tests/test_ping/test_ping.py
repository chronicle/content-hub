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

import pytest
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import ping
from cloud_identity.core.base_action import CloudIdentityAction


@set_metadata(
    integration_config={
        "Delegated Email": "admin@example.com",
    }
)
def test_ping_success(
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    ping.main()

    api_manager.test_connectivity.assert_called_once()
    assert action_output.results == ActionOutput(
        output_message=(
            "Successfully connected to the Cloud Identity server with "
            "the provided connection parameters!"
        ),
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


@set_metadata(
    integration_config={
        "Delegated Email": "admin@example.com",
    }
)
def test_ping_failure(
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    api_manager.test_connectivity.side_effect = Exception("Something went wrong")
    ping.main()

    api_manager.test_connectivity.assert_called_once()
    assert action_output.results == ActionOutput(
        output_message=(
            "Failed to connect to the Cloud Identity server!\n"
            "Reason: Something went wrong"
        ),
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
