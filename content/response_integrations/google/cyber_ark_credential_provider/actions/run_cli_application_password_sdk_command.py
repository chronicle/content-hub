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
from ..core import constants
from ..core.credential_provider_manager import (
    CredentialProviderManager,
    CommandResult,
)
from ..core import exceptions
from ..core import utils


class RunCLIApplicationPasswordSDKCommand(Action):
    def __init__(self) -> None:
        super().__init__(constants.RUN_CLI_APP_PASSWORD_SDK_COMMAND_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = (
            "Error executing action "
            f'"{constants.RUN_CLI_APP_PASSWORD_SDK_COMMAND_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.integration_parameters = utils.get_integration_parameters(
            self.soar_action
        )
        self.params.custom_sdk_command = extract_action_param(
            self.soar_action,
            param_name="clipasswordsdk Command",
            print_value=True,
            is_mandatory=True,
        )

    def _init_api_clients(self) -> CredentialProviderManager:
        return CredentialProviderManager(
            integration_parameters=self.params.integration_parameters
        )

    def _validate_params(self) -> None:
        utils.validate_ip_address(self.params.integration_parameters.docker_gateway_ip)

        if (
            self.params.integration_parameters.ssh_private_key_path
            and not self.params.integration_parameters.ssh_private_key_path.is_file()
        ):
            raise exceptions.CyberArkCredentialProviderValidationError(
                "SSH private key file not found at: "
                f"{self.params.integration_parameters.ssh_private_key_path}"
            )

    def _perform_action(self, _) -> None:
        result: CommandResult = self.api_client.execute_custom_sdk_command(
            command=self.params.custom_sdk_command
        )

        if result.error:
            self.error_output_message = (
                "Error executing the following command: "
                f"{self.params.custom_sdk_command}. "
            )
            raise exceptions.CyberArkCredentialProviderSDKCommandError(result.error)

        self.output_message = (
            "Successfully executed the following CLI Application Password SDK command "
            f"{self.params.custom_sdk_command}."
        )
        self.soar_action.result.add_result_json({"result": result.output})


def main() -> NoReturn:
    RunCLIApplicationPasswordSDKCommand().run()


if __name__ == "__main__":
    main()
