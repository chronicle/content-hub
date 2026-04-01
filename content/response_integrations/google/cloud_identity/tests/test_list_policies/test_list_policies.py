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

from unittest.mock import Mock

import pytest
from actions.ListPolicies import prepare_runner
from core.datamodels import OrgUnit, Policy, PolicyType


@pytest.mark.parametrize(
    "action_params, expected_list_policies_args",
    [
        (
                {
                    "Organization Unit Name": "TestOrgName",
                    "Policy Type Filter": "ADMIN",
                    "Setting Type Filter": "dlp/rule",
                    "Settings Display Name Filter": ["Display name", "Display name 2"],
                    "Max Results To Return": 3,
                },
                ("Id", ["Display name", "Display name 2"], "ADMIN", "dlp/rule"),
        ),
        (
                {
                    "Organization Unit Name": "TestOrgName",
                },
                ("Id", None, None, None),
        ),
        (
                {
                    "Organization Unit Name": "TestOrgName",
                    "Policy Type Filter": "ADMIN",
                },
                ("Id", None, "ADMIN", None),
        ),
        (
                {
                    "Organization Unit Name": "TestOrgName",
                    "Setting Type Filter": "dlp/rule",
                },
                ("Id", None, None, "dlp/rule"),
        ),
        (
                {
                    "Organization Unit Name": "TestOrgName",
                    "Policy Type Filter": "ADMIN",
                    "Setting Type Filter": "dlp/rule",
                },
                ("Id", None, "ADMIN", "dlp/rule"),
        ),
        (
                {
                    "Organization Unit Name": "TestOrgName",
                    "Policy Type Filter": "ADMIN",
                    "Settings Display Name Filter": ["Display name", "Display name 2"],
                },
                ("Id", ["Display name", "Display name 2"], "ADMIN", None),
        ),
        (
                {
                    "Organization Unit Name": "TestOrgName",
                    "Setting Type Filter": "dlp/rule",
                    "Settings Display Name Filter": ["Display name", "Display name 2"],
                },
                ("Id", ["Display name", "Display name 2"], None, "dlp/rule"),
        ),
    ],
)
def test_list_policies_success_scenarios(
        action_context, api_manager, action_params, expected_list_policies_args
) -> None:
    # GIVEN
    action_context.action_parameters = action_params
    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.list_policies.return_value = [
        Policy({}, {}, PolicyType.ADMIN, "Customer", "TestName")
    ]
    api_manager.fetch_org_unit.return_value = OrgUnit("TestOrgName", org_unit_id="Id")

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.list_policies.assert_called_once_with(*expected_list_policies_args)
    assert result.value is True
    assert result.json_result is not None
    assert result.json_result[0]["name"] == "TestName"


def test_should_show_error_when_find_policies_fails(
        action_context, api_manager
) -> None:
    # GIVEN
    action_context.action_parameters = {
        "Organization Unit Name": "TestOrgName",
        "Policy Type Filter": "ADMIN",
        "Setting Type Filter": "dlp/rule",
        "Settings Display Name Filter": ["Display name", "Display name 2"],
        "Max Results To Return": 3,
    }
    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.list_policies.side_effect = Exception("Something went wrong")
    api_manager.fetch_org_unit.return_value = Mock()

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.list_policies.assert_called_once()
    assert result.value is False
    assert (
            "Error executing action “List Policies”. Reason: Something went wrong"
            in result.output_message
    )
