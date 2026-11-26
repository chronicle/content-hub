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
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from ..core.GoogleCloudComputeConstants import (
    UPDATE_FIREWALL_RULE_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from ..core.GoogleCloudComputeDatamodels import OperationResource
from ..core.GoogleCloudComputeExceptions import (
    GoogleCloudComputeValidationError,
)
from ..core.GoogleCloudComputeGenerics import UpdateFirewallAction

from ..core.GoogleCloudComputeManager import GoogleCloudComputeManager


class UpdateFirewallRule(UpdateFirewallAction):

    def _validate_params(self) -> None:
        super()._validate_params()
        param_validator = ParameterValidator(self.soar_action)
        if not is_empty_string_or_none(self.params.workload_identity_email):
            param_validator.validate_email(
                param_name="Workload Identity Email",
                email=self.params.workload_identity_email,
            )
        if not is_empty_string_or_none(self.params.service_account_json):
            param_validator.validate_json(
                param_name="Service Account Json File Content",
                json_string=self.params.service_account_json,
                print_value=False,
            )

        self.params.source_ip_ranges = param_validator.validate_csv(
            param_name="Source IP ranges",
            csv_string=self.params.source_ip_ranges,
            print_value=True,
        )
        self.params.source_tags = param_validator.validate_csv(
            param_name="Source Tags",
            csv_string=self.params.source_tags,
            print_value=True,
        )
        self.params.source_service_accounts = param_validator.validate_csv(
            param_name="Source Service Accounts",
            csv_string=self.params.source_service_accounts,
            print_value=True,
        )
        self.params.destination_ip_ranges = param_validator.validate_csv(
            param_name="Destination IP Ranges",
            csv_string=self.params.destination_ip_ranges,
            print_value=True,
        )

        self.params.tcp_ports_list = param_validator.validate_csv(
            param_name="TCP Ports", csv_string=self.params.tcp_ports, print_value=True
        )
        self.params.udp_ports_list = param_validator.validate_csv(
            param_name="UDP Ports", csv_string=self.params.udp_ports, print_value=True
        )
        self.params.other_protocols_list = param_validator.validate_csv(
            param_name="Other Protocols",
            csv_string=self.params.other_protocols,
            print_value=True,
        )

        if not any(
            (
                self.params.source_ip_ranges,
                self.params.source_tags,
                self.params.source_service_accounts,
                self.params.destination_ip_ranges,
                self.params.tcp_ports_list,
                self.params.udp_ports_list,
                self.params.other_protocols_list,
            )
        ):
            raise GoogleCloudComputeValidationError(
                "you must provide at least one parameter to update the firewall "
                "rule with."
            )

    def _extract_action_params(self) -> None:
        super()._extract_action_params()

        self.params.source_ip_ranges = extract_action_param(
            self.soar_action, param_name="Source IP ranges", print_value=True
        )
        self.params.source_tags = extract_action_param(
            self.soar_action, param_name="Source Tags", print_value=True
        )
        self.params.source_service_accounts = extract_action_param(
            self.soar_action, param_name="Source Service Accounts", print_value=True
        )
        self.params.destination_ip_ranges = extract_action_param(
            self.soar_action, param_name="Destination IP Ranges", print_value=True
        )

        self.params.tcp_ports = extract_action_param(
            self.soar_action, param_name="TCP Ports", print_value=True
        )
        self.params.udp_ports = extract_action_param(
            self.soar_action, param_name="UDP Ports", print_value=True
        )
        self.params.other_protocols = extract_action_param(
            self.soar_action, param_name="Other Protocols", print_value=True
        )

    def _do_first_run_operation(
            self,
            resource_path: str,
            manager: GoogleCloudComputeManager
    ) -> OperationResource:
        """Start an update firewall operation."""
        firewall_rule = manager.get_firewall_rule(resource_path)

        firewall_rule.source_ranges = self.params.source_ip_ranges
        firewall_rule.source_tags = self.params.source_tags
        firewall_rule.source_service_accounts = self.params.source_service_accounts
        firewall_rule.destination_ranges = self.params.destination_ip_ranges

        if self.params.tcp_ports_list:
            firewall_rule.update_ports(
                protocol="tcp", ports_list=self.params.tcp_ports_list
            )

        if self.params.udp_ports_list:
            firewall_rule.update_ports(
                protocol="udp", ports_list=self.params.udp_ports_list
            )

        if self.params.other_protocols_list:
            ports_and_protocols = (
                firewall_rule.allowed
                if firewall_rule.allowed is not None
                else firewall_rule.denied
            )

            if self.params.other_protocols_list == ["all"]:
                new_ports_and_protocols = [{"IPProtocol": "all"}]

            elif self.params.other_protocols_list == ["none"]:
                new_ports_and_protocols = list(
                    filter(
                        lambda config: config["IPProtocol"] in ["tcp", "udp"],
                        ports_and_protocols,
                    )
                )

            else:
                new_ports_and_protocols = list(
                    filter(
                        lambda config: config["IPProtocol"] in ["tcp", "udp"],
                        ports_and_protocols,
                    )
                )
                for other_protocol_new in self.params.other_protocols_list:
                    new_ports_and_protocols.append({"IPProtocol": other_protocol_new})

            ports_and_protocols.clear()
            ports_and_protocols.extend(new_ports_and_protocols)

        return manager.patch_firewall_rule(
            resource_path=resource_path, firewall=firewall_rule
        )


def main() -> None:
    UpdateFirewallRule(
        f"{INTEGRATION_NAME} - {UPDATE_FIREWALL_RULE_SCRIPT_NAME}"
    ).run()


if __name__ == "__main__":
    main()
