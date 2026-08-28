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

from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string
from TIPCommon.validation import ParameterValidator
from ..core import constants
from ..core.credential_provider_manager import (
    CredentialProviderManager,
    CommandResult,
)
from ..core import exceptions
from ..core import utils


class GetApplicationPasswordValue(Action):
    def __init__(self) -> None:
        super().__init__(constants.GET_APPLICATION_PASSWORD_VALUE_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = (
            "Error executing action "
            f'"{constants.GET_APPLICATION_PASSWORD_VALUE_SCRIPT_NAME}".'
        )
        self.result_value: bool = True

    def _extract_action_parameters(self) -> None:
        self.params.integration_parameters = utils.get_integration_parameters(
            self.soar_action
        )
        self.params.application_id = extract_action_param(
            self.soar_action,
            param_name="Application",
            print_value=True,
            is_mandatory=True,
        )
        self.params.safe_name = extract_action_param(
            self.soar_action,
            param_name="Safe Name",
            print_value=True,
            is_mandatory=True,
        )
        self.params.folder_name = extract_action_param(
            self.soar_action,
            param_name="Folder Name",
            print_value=True,
            is_mandatory=False,
        )
        self.params.object_name = extract_action_param(
            self.soar_action,
            param_name="Object Name",
            print_value=True,
            is_mandatory=True,
        )
        self.params.output_field = extract_action_param(
            self.soar_action,
            param_name="Output",
            default_value=constants.PASSWORD_OUTPUT_FIELD,
            print_value=True,
            is_mandatory=True,
        )

    def _init_api_clients(self) -> CredentialProviderManager:
        return CredentialProviderManager(
            integration_parameters=self.params.integration_parameters
        )

    def _validate_params(self) -> None:
        utils.validate_ip_address(self.params.integration_parameters.docker_gateway_ip)

        param_validator: ParameterValidator = ParameterValidator(self.soar_action)
        self.params.new_output_field = param_validator.validate_csv(
            param_name="Output",
            csv_string=self.params.output_field,
        )

        if (
            self.params.integration_parameters.ssh_private_key_path
            and not self.params.integration_parameters.ssh_private_key_path.is_file()
        ):
            raise exceptions.CyberArkCredentialProviderValidationError(
                "SSH private key file not found at: "
                f"{self.params.integration_parameters.ssh_private_key_path}"
            )

    def _perform_action(self, _) -> None:
        result: CommandResult = self.api_client.get_application_password(
            application_id=self.params.application_id,
            safe_name=self.params.safe_name,
            folder_name=self.params.folder_name,
            object_name=self.params.object_name,
            output_field=convert_list_to_comma_string(self.params.new_output_field),
        )

        if result.error:
            raise exceptions.CyberArkCredentialProviderManagerError(result.error)

        if result.output:
            self.soar_action.result.add_result_json({"result": result.output})
            self.output_message: str = (
                "Successfully fetched password value for the application ID "
                f"{self.params.application_id}."
            )
            return

        self.result_value: bool = False
        self.output_message: str = (
            "The password value for the "
            f"application ID {self.params.application_id} "
            "was not found in the CyberArk Credential Provider."
        )

        return


def main() -> NoReturn:
    GetApplicationPasswordValue().run()


if __name__ == "__main__":
    main()
