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

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from ..core.GoogleCloudComputeConstants import (
    ADD_IP_TO_FIREWALL_RULE,
    INTEGRATION_NAME,
)
from ..core.GoogleCloudComputeDatamodels import OperationResource, IPRangeType
from ..core.GoogleCloudComputeGenerics import UpdateFirewallAction
from ..core.GoogleCloudComputeManager import GoogleCloudComputeManager


class AddIPToFirewallRule(UpdateFirewallAction):

    def _validate_params(self) -> None:
        super()._validate_params()
        param_validator = ParameterValidator(self.soar_action)
        self.params.ip_ranges_set = set(
            param_validator.validate_csv(
                param_name="IP Ranges",
                csv_string=self.params.ip_ranges,
                print_value=True,
            )
        )
        self.params.type_ = IPRangeType[
            param_validator.validate_ddl(
                param_name="Type",
                value=self.params.type_.upper(),
                ddl_values=[enum.name for enum in IPRangeType],
                print_value=True,
            )
        ]

    def _extract_action_params(self) -> None:
        super()._extract_action_params()
        self.params.ip_ranges = extract_action_param(
            self.soar_action, param_name="IP Ranges", print_value=True
        )
        self.params.type_ = extract_action_param(
            self.soar_action, param_name="Type", print_value=True
        )

    def _do_first_run_operation(
            self,
            resource_path: str,
            manager: GoogleCloudComputeManager
    ) -> OperationResource:
        """Start an update firewall operation."""
        firewall_rule = manager.get_firewall_rule(resource_path)
        firewall_rule.extend_ip_ranges(
            type_=self.params.type_,
            ip_ranges=self.params.ip_ranges_set
        )
        return manager.patch_firewall_rule(
            resource_path=resource_path, firewall=firewall_rule
        )


def main() -> None:
    AddIPToFirewallRule(
        f"{INTEGRATION_NAME} - {ADD_IP_TO_FIREWALL_RULE}"
    ).run()


if __name__ == "__main__":
    main()
