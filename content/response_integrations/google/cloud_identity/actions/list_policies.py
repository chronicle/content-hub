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

from TIPCommon.extraction import extract_action_param

from ..core.base_action import CloudIdentityAction
from ..core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.datamodels import PolicyType
from ..core.exceptions import GoogleCloudIdentityApiEntityNotFoundException
from ..core.utils import string_to_list

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import Entity


# pylint: disable=invalid-name
class PolicyTypeDDL(StrEnum):
    ADMIN = PolicyType.ADMIN
    SYSTEM = PolicyType.SYSTEM
    BOTH = "BOTH"


MAX_RESULTS_LIMIT = 100


class ListPolicies(CloudIdentityAction):
    def __init__(self) -> None:
        super().__init__(f"{INTEGRATION_NAME} - ListPolicies")

    def _extract_action_parameters(self) -> None:
        self.params.org_unit_name = extract_action_param(
            self.soar_action,
            param_name="Organization Unit Name",
            is_mandatory=True,
            print_value=True,
        )
        policy_type_str = extract_action_param(
            self.soar_action,
            param_name="Policy Type Filter",
            is_mandatory=False,
            print_value=True,
        )
        if policy_type_str:
            policy_type_str = policy_type_str.upper()
        self.params.policy_type_filter = policy_type_str

        self.params.setting_type_filter = extract_action_param(
            self.soar_action,
            param_name="Setting Type Filter",
            is_mandatory=False,
            print_value=True,
        )
        display_names_str = extract_action_param(
            self.soar_action,
            param_name="Settings Display Name Filter",
            is_mandatory=False,
            print_value=True,
        )
        self.params.display_names = string_to_list(display_names_str)

        self.params.max_results = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, _: Entity | None = None) -> None:
        client = self._get_api_manager()

        if not self.params.org_unit_name or not self.params.org_unit_name.strip():
            msg = "Organization Unit Name parameter cannot be empty."
            raise ValueError(msg)

        if self.params.max_results < 1 or self.params.max_results > MAX_RESULTS_LIMIT:
            msg = "Max Results To Return must be between 1 and 100."
            raise ValueError(msg)

        client.test_connectivity()

        policy_type_filter = self.params.policy_type_filter
        if policy_type_filter == PolicyTypeDDL.BOTH:
            policy_type_filter = None
        elif policy_type_filter:
            policy_type_filter = PolicyType(policy_type_filter)

        self.logger.info(
            "setting_type_filter: %s, display_names: %s, policy_type_filter: %s, "
            "organization_unit_name_or_path: %s, max_results: %s",
            self.params.setting_type_filter,
            self.params.display_names,
            policy_type_filter,
            self.params.org_unit_name,
            self.params.max_results,
        )

        org_unit = client.fetch_org_unit(self.params.org_unit_name)
        if org_unit:
            org_unit_id = org_unit.get_org_unit_id()
        else:
            msg = "Organization Unit not found."
            raise GoogleCloudIdentityApiEntityNotFoundException(msg)

        policies = client.list_policies(
            org_unit_id,
            self.params.display_names,
            policy_type_filter,
            self.params.setting_type_filter,
        )
        policies = list(islice(policies, self.params.max_results))

        if not policies:
            self.result_value = False
            self.output_message = (
                f"No policies found based on the provided "
                f"criteria in {INTEGRATION_DISPLAY_NAME}."
            )
            return

        self.json_results = [policy.to_dict() for policy in policies]
        self.output_message = (
            f"Successfully listed policies based on the provided criteria in "
            f"{INTEGRATION_DISPLAY_NAME}."
        )


def main() -> NoReturn:
    """Run the ListPolicies action."""
    ListPolicies().run()


if __name__ == "__main__":
    main()
