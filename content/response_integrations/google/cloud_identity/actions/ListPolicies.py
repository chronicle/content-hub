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

from enum import StrEnum  # pylint: disable=no-name-in-module
from itertools import islice
from typing import TYPE_CHECKING

from core.action_param_mappers import (
    as_csv,
    as_ddl,
    as_type,
    non_empty,
    required,
    to_upper_case,
    validate_range,
)
from core.action_wrapper import ActionContext, ActionResult, ActionRunner
from core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME, INTEGRATION_PARAM_MAPPERS
from core.datamodels import PolicyType
from core.exceptions import GoogleCloudIdentityApiEntityNotFoundException
from core.manager_providers import build_api_manager
from soar_sdk.SiemplifyDataModel import EntityTypes

if TYPE_CHECKING:
    from core.api_manager import GoogleCloudIdentityApiManager


SCRIPT_NAME = "ListPolicies"
SCRIPT_DISPLAY_NAME = "List Policies"


# pylint: disable=invalid-name
class PolicyTypeDDL(StrEnum):
    ADMIN = PolicyType.ADMIN
    SYSTEM = PolicyType.SYSTEM
    BOTH = "BOTH"


def prepare_runner() -> ActionRunner:
    """Prepare action runner.

    Returns:
        The action runner.

    """
    param_mappers = {
        "Organization Unit Name": [required(), non_empty()],
        "Policy Type Filter": [to_upper_case(), as_ddl(PolicyTypeDDL)],
        "Setting Type Filter": [],
        "Settings Display Name Filter": [as_csv()],
        "Max Results To Return": [as_type(int), validate_range(1, 100)],
    }

    return ActionRunner(
        main,
        integration_name=INTEGRATION_NAME,
        action_name=f"{INTEGRATION_NAME} - {SCRIPT_NAME}",
        print_params=True,
        supported_entities=[EntityTypes.URL],
        enable_default_error_handling=True,
        error_message_format=f"Error executing action “{SCRIPT_DISPLAY_NAME}”. "
        f"Reason: {{error}}",
        action_param_mappers=param_mappers,
        integration_param_mappers=INTEGRATION_PARAM_MAPPERS,
        injectables={"api_manager": build_api_manager},
    )


def main(
    context: ActionContext,
    result: ActionResult,
    api_manager: GoogleCloudIdentityApiManager,
) -> None:
    """List policies.

    Args:
        context: The action context.
        result: The action result.
        api_manager: The API manager.

    Raises:
        GoogleCloudIdentityApiEntityNotFoundException: If the organization unit is not found.

    """
    api_manager.test_connectivity()

    parameters = context.action_parameters
    organization_unit_name_or_path = parameters.get("Organization Unit Name")
    policy_type_filter = parameters.get("Policy Type Filter")
    policy_type_filter = (
        policy_type_filter if policy_type_filter != PolicyTypeDDL.BOTH else None
    )
    setting_type_filter = parameters.get("Setting Type Filter")
    display_names = parameters.get("Settings Display Name Filter")
    max_results = parameters.get("Max Results To Return")
    context.get_logger().info(
        {
            "setting_type_filter": setting_type_filter,
            "display_names": display_names,
            "policy_type_filter": policy_type_filter,
            "organization_unit_name_or_path": organization_unit_name_or_path,
            "max_results": max_results,
        }
    )

    org_unit = api_manager.fetch_org_unit(organization_unit_name_or_path)

    if org_unit:
        org_unit_id = org_unit.get_org_unit_id()
    else:
        msg = "Organization Unit not found."
        raise GoogleCloudIdentityApiEntityNotFoundException(msg)

    policies = api_manager.list_policies(
        org_unit_id, display_names, policy_type_filter, setting_type_filter
    )
    policies = list(islice(policies, max_results))

    if not policies:
        result.value = False
        result.output_message = (
            f"No policies found based on the provided"
            f" criteria in {INTEGRATION_DISPLAY_NAME}."
        )
        return

    result.json_result = [policy.to_dict() for policy in policies]
    result.output_message = (
        f"Successfully listed policies based on the provided criteria in "
        f"{INTEGRATION_DISPLAY_NAME}."
    )


if __name__ == "__main__":
    prepare_runner().run()
