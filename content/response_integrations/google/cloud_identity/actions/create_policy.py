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

import yaml
from TIPCommon.exceptions import ActionSetupError
from TIPCommon.extraction import extract_action_param

from ..core.base_action import CloudIdentityAction
from ..core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.datamodels import Policy

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import Entity


class CreatePolicy(CloudIdentityAction):
    def __init__(self) -> None:
        super().__init__(f"{INTEGRATION_NAME} - CreatePolicy")

    def _extract_action_parameters(self) -> None:
        self.params.policy_entry_str = extract_action_param(
            self.soar_action,
            param_name="Policy Entry",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        try:
            policy_dict = yaml.safe_load(self.params.policy_entry_str)
        except Exception as e:
            msg = "Policy Entry is not a valid JSON."
            raise ActionSetupError(msg) from e

        if not isinstance(policy_dict, dict):
            msg = "Policy Entry must be a valid JSON dictionary."
            raise ActionSetupError(msg)

        self.params.policy_dict = policy_dict

    def _perform_action(self, _: Entity | None = None) -> None:
        policy_entry = Policy.from_dict(self.params.policy_dict)

        self.logger.info("Creating policy entry...")
        created_policy = self.api_client.create_policy(policy_entry)
        self.logger.info("Policy entry created successfully...")

        self.json_results = created_policy.to_dict()
        self.output_message = f"Successfully added a new policy in {INTEGRATION_DISPLAY_NAME}."


def main() -> NoReturn:
    """Run the CreatePolicy action."""
    CreatePolicy().run()


if __name__ == "__main__":
    main()
