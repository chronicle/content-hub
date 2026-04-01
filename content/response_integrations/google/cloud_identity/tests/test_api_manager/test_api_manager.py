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
from core.api_manager import GoogleCloudIdentityApiManager
from core.datamodels import (
    DLPRulePolicySettingValue,
    Policy,
    PolicySetting,
    PolicySettingType,
    PolicyType,
    URLListDetectorPolicySettingValue,
)


@pytest.fixture(name="api_manager")
def api_manager_fixture(
    auth_session, policies_resource, org_units_resource
) -> GoogleCloudIdentityApiManager:
    """GoogleCloudIdentityApiManager instance with mocked dependencies."""

    manager = GoogleCloudIdentityApiManager(
        auth_session,
        policies_resource=policies_resource,
        org_units_resource=org_units_resource,
    )
    return manager


def test_test_connectivity_success(
    api_manager: GoogleCloudIdentityApiManager, policies_resource
):
    """Test test_connectivity method for successful connection."""
    policies_resource.list.return_value = iter(
        [Mock()]
    )  # Simulate a policy being returned
    api_manager.test_connectivity()
    policies_resource.list.assert_called_once()


def test_test_connectivity_failure(
    api_manager: GoogleCloudIdentityApiManager, policies_resource
):
    """Test test_connectivity method for connection failure."""
    policies_resource.list.side_effect = Exception("Connection error")
    with pytest.raises(Exception, match="Connection error"):
        api_manager.test_connectivity()
    policies_resource.list.assert_called_once()


def test_fetch_policies_by_setting_type(
    api_manager: GoogleCloudIdentityApiManager, policies_resource
):
    """Test fetching policies by setting type."""
    setting = PolicySetting(
        type=PolicySettingType.URL_LIST_DETECTOR,
        value=URLListDetectorPolicySettingValue(display_name="test"),
    )
    policies_resource.list.return_value = iter(
        [
            Policy(
                name="policy1",
                customer="customers/C123",
                policy_query={},
                setting=setting,
                type=PolicyType.ADMIN,
            ),
            Policy(
                name="policy2",
                customer="customers/C123",
                policy_query={},
                setting=setting,
                type=PolicyType.ADMIN,
            ),
        ]
    )
    policies = list(
        api_manager.fetch_policies_by_setting_type(PolicySettingType.URL_LIST_DETECTOR)
    )
    assert len(policies) == 2
    assert policies[0].name == "policy1"
    policies_resource.list.assert_called_once()


def test_fetch_policy(api_manager: GoogleCloudIdentityApiManager, policies_resource):
    """Test fetching a single policy by ID."""
    policy_id = "customers/C123/policies/P456"
    expected_policy = Policy(
        name=policy_id,
        customer="customers/C123",
        policy_query={},
        setting=PolicySetting(
            type=PolicySettingType.URL_LIST_DETECTOR,
            value=URLListDetectorPolicySettingValue(display_name="test"),
        ),
        type=PolicyType.ADMIN,
    )
    policies_resource.get.return_value = expected_policy
    policy = api_manager.fetch_policy(policy_id)
    assert policy == expected_policy
    policies_resource.get.assert_called_once_with("P456")


def test_create_policy(api_manager: GoogleCloudIdentityApiManager, policies_resource):
    """Test creating a policy."""
    new_policy = Policy(
        name="new_policy",
        customer="customers/C123",
        policy_query={},
        setting=PolicySetting(
            type=PolicySettingType.URL_LIST_DETECTOR,
            value=URLListDetectorPolicySettingValue(display_name="test"),
        ),
        type=PolicyType.ADMIN,
    )
    policies_resource.create.return_value = new_policy
    created_policy = api_manager.create_policy(new_policy)
    assert created_policy == new_policy
    policies_resource.create.assert_called_once_with(new_policy)


def test_create_chrome_dlp_policy(
    api_manager: GoogleCloudIdentityApiManager, policies_resource
):
    """Test creating a Chrome DLP policy."""
    organization_unit_id = "OU456"
    rule_name = "TestRule"
    description = "Test Description"
    html_message_body = "Blocked!"

    policies_resource.create.return_value = Policy(
        name="created_dlp_policy",
        customer="customers/test_customer",
        policy_query={"orgUnit": f"orgUnits/{organization_unit_id}"},
        setting=PolicySetting(
            type=PolicySettingType.DLP_RULE,
            value=DLPRulePolicySettingValue(display_name=rule_name),
        ),
        type=PolicyType.ADMIN,
    )

    created_policy = api_manager.create_chrome_dlp_policy(
        organization_unit_id=organization_unit_id,
        rule_name=rule_name,
        description=description,
        html_message_body=html_message_body,
        cel_condition="test.contains('w')",
    )

    assert created_policy.name == "created_dlp_policy"
    policies_resource.create.assert_called_once()


def test_create_policy_for_org_unit(
    api_manager: GoogleCloudIdentityApiManager, policies_resource
):
    """Test creating a policy for an organizational unit."""
    organization_unit_id = "OU456"
    setting_value = DLPRulePolicySettingValue(display_name="TestSetting")

    policies_resource.create.return_value = Policy(
        name="created_org_unit_policy",
        customer="customers/test_customer",
        policy_query={"orgUnit": f"orgUnits/{organization_unit_id}"},
        setting=PolicySetting.from_setting_value(setting_value),
        type=PolicyType.ADMIN,
    )

    created_policy = api_manager.create_policy_for_org_unit(
        organization_unit_id=organization_unit_id,
        setting=setting_value,
    )

    assert created_policy.name == "created_org_unit_policy"
    policies_resource.create.assert_called_once()
    args, _ = policies_resource.create.call_args
    policy_arg = args[0]
    assert isinstance(policy_arg, Policy)
    assert policy_arg.type == PolicyType.ADMIN
    assert policy_arg.policy_query["orgUnit"] == f"orgUnits/{organization_unit_id}"
    assert isinstance(policy_arg.setting, PolicySetting)
    assert policy_arg.setting.value == setting_value


def test_list_policies_with_filters(
    api_manager: GoogleCloudIdentityApiManager, policies_resource
):
    """Test listing policies with various filters."""
    organization_unit_id = "OU123"
    display_name = ["Test Display Name"]
    policy_type = PolicyType.ADMIN
    setting_type = PolicySettingType.DLP_RULE
    policies_resource.list.return_value = iter([Mock()])
    list(
        api_manager.list_policies(
            organization_unit_id=organization_unit_id,
            display_names=display_name,
            policy_type=policy_type,
            setting_type=setting_type,
        )
    )

    policies_resource.list.assert_called_once()
