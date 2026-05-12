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
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import list_policies
from cloud_identity.core.base_action import CloudIdentityAction
from cloud_identity.core.datamodels import OrgUnit, Policy, PolicyType


@set_metadata(
    integration_config={
        "Delegated Email": "admin@example.com",
    },
    parameters={
        "Organization Unit Name": "TestOrgName",
        "Policy Type Filter": "ADMIN",
        "Setting Type Filter": "dlp/rule",
        "Settings Display Name Filter": "Display name, Display name 2",
        "Max Results To Return": 3,
    },
)
def test_list_policies_success(
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    policy = Policy({}, {}, PolicyType.ADMIN, "Customer", "TestName")
    api_manager.list_policies.return_value = [policy]
    api_manager.fetch_org_unit.return_value = OrgUnit("TestOrgName", org_unit_id="Id")

    list_policies.main()

    api_manager.list_policies.assert_called_once_with(
        "Id", ["Display name", "Display name 2"], PolicyType.ADMIN, "dlp/rule"
    )
    assert action_output.results == ActionOutput(
        output_message="Successfully listed policies based on the provided criteria in Cloud Identity.",
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(json_result=[policy.to_dict()]),
    )


@set_metadata(
    integration_config={
        "Delegated Email": "admin@example.com",
    },
    parameters={
        "Organization Unit Name": "TestOrgName",
        "Policy Type Filter": "ADMIN",
        "Setting Type Filter": "dlp/rule",
        "Settings Display Name Filter": "Display name, Display name 2",
        "Max Results To Return": 3,
    },
)
def test_list_policies_failure(
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    api_manager.list_policies.side_effect = Exception("Something went wrong")
    api_manager.fetch_org_unit.return_value = OrgUnit("TestOrgName", org_unit_id="Id")

    list_policies.main()

    api_manager.list_policies.assert_called_once()
    assert action_output.results == ActionOutput(
        output_message=(
            'Error executing action "CloudIdentity - ListPolicies"\n'
            "Reason: Something went wrong"
        ),
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
