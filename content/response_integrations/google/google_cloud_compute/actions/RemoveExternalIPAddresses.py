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

import itertools
import json
import sys
from typing import Any

from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.base.utils import validate_manager
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from ..core.GoogleCloudComputeConstants import (
    UNASSIGN_EXTERNAL_IP_SCRIPT_NAME,
    INSTANCE_RESOURCE_NAME,
    INTEGRATION_NAME,
    IPV4_ONLY,
    WILDCARD,
    API_URL,
)
from ..core.GoogleCloudComputeExceptions import (
    GoogleCloudComputeOperationError,
    GoogleCloudComputeInvalidInstanceID,
    GoogleCloudComputeInvalidZone,
    GoogleCloudComputeTimeoutError,
    GoogleCloudComputeValidationError,
)
from ..core.GoogleCloudComputeUtils import (
    extract_instance_resource_path,
    is_async_action_global_timeout_approaching,
)

from ..core.GoogleCloudComputeManager import GoogleCloudComputeManager


class UnassignExternalAddresses(Action):

    def __init__(self, script_name: str, is_first_run: bool) -> None:
        super().__init__(script_name)
        self._is_first_run = is_first_run
        self.result_value = False

    def _init_api_clients(self) -> Any | None:
        return GoogleCloudComputeManager(
            api_root=self.params.api_root,
            account_type=self.params.account_type,
            project_id=self.params.target_project_id or self.params.project_id,
            private_key_id=self.params.private_key_id,
            private_key=self.params.private_key,
            client_email=self.params.client_email,
            client_id=self.params.client_id,
            auth_uri=self.params.auth_uri,
            token_uri=self.params.token_uri,
            auth_provider_x509_url=self.params.auth_provider_x509_url,
            client_x509_cert_url=self.params.client_x509_url,
            service_account_json=self.params.service_account_json,
            workload_identity_email=self.params.workload_identity_email,
            verify_ssl=self.params.verify_ssl,
        )

    def _validate_params(self) -> None:
        if not (
            self.params.resource_name
            or (self.params.instance_zone and self.params.instance_id)
        ):
            raise GoogleCloudComputeValidationError(
                "you should provide either 'Resource Name' or "
                "'Instance Zone' and 'Instance ID' parameters"
            )

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

        self.params.network_interface_list = param_validator.validate_csv(
            param_name="Network Interfaces",
            csv_string=self.params.network_interfaces,
            print_value=True,
        )

    def _extract_configuration_params(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
            print_value=True,
            default_value=API_URL
        )
        self.params.account_type = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Account Type",
            print_value=True,
        )
        self.params.project_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Project ID",
            print_value=True,
        )
        self.params.private_key_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Private Key ID",
            remove_whitespaces=False,
        )
        self.params.private_key = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Private Key",
            remove_whitespaces=False,
        )
        self.params.client_email = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client Email",
            print_value=True,
        )
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client ID",
            print_value=True,
        )
        self.params.auth_uri = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Auth URI",
            print_value=True,
        )
        self.params.token_uri = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Token URI",
            print_value=True,
        )
        self.params.auth_provider_x509_url = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Auth Provider X509 URL",
            print_value=True,
        )
        self.params.client_x509_url = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client X509 URL",
            print_value=True,
        )
        self.params.service_account_json = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Service Account Json File Content",
            remove_whitespaces=False,
        )
        self.params.workload_identity_email = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Workload Identity Email",
            print_value=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            print_value=True,
        )

    def _extract_action_params(self) -> None:
        # Action params
        self.params.resource_name = extract_action_param(
            self.soar_action, param_name="Resource Name", print_value=True
        )
        self.params.target_project_id = extract_action_param(
            self.soar_action,
            param_name="Project ID",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        self.params.instance_zone = extract_action_param(
            self.soar_action, param_name="Instance Zone", print_value=True
        )
        self.params.instance_id = extract_action_param(
            self.soar_action, param_name="Instance ID", print_value=True
        )
        self.params.network_interfaces = extract_action_param(
            self.soar_action,
            param_name="Network Interfaces",
            print_value=True,
            default_value=WILDCARD,
        )

    def _extract_action_parameters(self):
        self.params.async_context = json.loads(
            extract_action_param(
                self.soar_action, param_name="additional_data", default_value="{}"
            )
        )
        self._extract_configuration_params()
        self._extract_action_params()

    def _do_operation(
        self, resource_path: str, manager: GoogleCloudComputeManager
    ) -> dict[str, list[SingleJson]]:
        """Start operations of updating networkInterfaces."""
        instance = manager.get_instance(resource_path=resource_path)
        operations = {}

        interfaces_to_update = set(self.params.network_interface_list)
        non_existent_interfaces = interfaces_to_update.difference(
            ni.name for ni in instance.network_interfaces
        )

        if (
            WILDCARD not in self.params.network_interface_list
            and non_existent_interfaces
        ):
            non_existent_interfaces_str = ",".join(non_existent_interfaces)
            raise GoogleCloudComputeOperationError(
                f"the following network interfaces were not found: "
                f"{non_existent_interfaces_str} on the {resource_path} "
                f"in {INTEGRATION_NAME}. Please check the spelling."
            )

        for network_interface in instance.network_interfaces:
            if not (
                WILDCARD in self.params.network_interface_list
                or network_interface.name in interfaces_to_update
            ):
                continue

            operations[network_interface.name] = []
            if not network_interface.stack_type == IPV4_ONLY:
                operations[network_interface.name].append(
                    manager.patch_network_interface(
                        resource_path=resource_path,
                        network_interface=network_interface.name,
                        fingerprint=network_interface.fingerprint,
                        stack_type=IPV4_ONLY,
                    ).to_json()
                )

            for access_config in network_interface.access_configs:
                operations[network_interface.name].append(
                    manager.delete_access_config(
                        resource_path=resource_path,
                        network_interface=network_interface.name,
                        access_config=access_config["name"],
                    ).to_json()
                )

        return operations

    def _perform_action(self, _=None) -> None:
        manager = self._api_client
        self.logger.info("Validating manager is not None")
        validate_manager(manager)
        resource_path = (
            extract_instance_resource_path(self.params.resource_name)
            if self.params.resource_name is not None
            else INSTANCE_RESOURCE_NAME.format(
                project_id=manager.project_id,
                zone=self.params.instance_zone,
                resource_id=self.params.instance_id,
            )
        )
        try:
            if self.is_first_run:
                operations_map = self._do_operation(resource_path, manager)

            else:
                operations_map = self.params.async_context
                running_operations = [
                    operation
                    for operation in itertools.chain(*operations_map.values())
                    if operation["status"] in ["RUNNING", "PENDING"]
                ]

                if is_async_action_global_timeout_approaching(
                    siemplify=self.soar_action, start_time=self.action_start_time
                ):
                    running_operations_names = ",".join(
                        (op["name"] for op in running_operations)
                    )
                    raise GoogleCloudComputeTimeoutError(
                        "action ran into a timeout during execution. "
                        f"Pending operations: {running_operations_names}. "
                        "Please increase the timeout in IDE."
                    )

                for operation_json in running_operations:
                    operation = manager.get_operation(operation_json["selfLink"])
                    operation_json.update(operation.to_json())

            self.json_results = list(
                itertools.chain(
                    *(
                        [
                            {**operation_json, "networkInterface": network_interface}
                            for operation_json in operations_json
                        ]
                        for network_interface, operations_json in operations_map.items()
                    )
                )
            )

            failed_networks = {}
            updated_networks = []
            pending_networks = []

            for network_interface, operations in operations_map.items():
                if any(op["status"] in ["RUNNING", "PENDING"] for op in operations):
                    pending_networks.append(network_interface)
                    continue

                if any(op.get("error") for op in operations):
                    errors_messages = []
                    for op in operations:
                        errors = op.get("error", {}).get("errors", [])
                        errors_message = ", ".join(
                            err.get("message") for err in errors if "message" in err
                        )
                        if errors_message:
                            errors_messages.append(errors_message)

                    failed_networks[network_interface] = "; ".join(errors_messages)
                    continue

                updated_networks.append(network_interface)

            if pending_networks:
                self.output_message = (
                    "Waiting for the operations to finish execution on the "
                    f"{resource_path} instance in {INTEGRATION_NAME}."
                )
                self._result_value = json.dumps(operations_map)
                self.execution_state = ExecutionState.IN_PROGRESS
                return

            if failed_networks:
                failed_networks_str = "\n".join(
                    f"{name}. {msg}" for name, msg in failed_networks.items()
                )
                raise GoogleCloudComputeOperationError(
                    "action failed to remove the following nics\n"
                    f"{failed_networks_str}"
                )

            updated_networks_str = ",".join(updated_networks)
            self.output_message = (
                "Successfully removed external IP addresses from "
                f"{updated_networks_str} interfaces of "
                f"{resource_path} instance in {INTEGRATION_NAME}."
            )
            self.result_value = True

        except GoogleCloudComputeInvalidZone as error:
            raise GoogleCloudComputeInvalidZone(
                "provided instance zone is not valid."
            ) from error

        except GoogleCloudComputeInvalidInstanceID as error:
            raise GoogleCloudComputeInvalidInstanceID(
                "provided instance id is not valid."
            ) from error


def main() -> None:
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    UnassignExternalAddresses(
        f"{INTEGRATION_NAME} - {UNASSIGN_EXTERNAL_IP_SCRIPT_NAME}", is_first_run
    ).run()


if __name__ == "__main__":
    main()
