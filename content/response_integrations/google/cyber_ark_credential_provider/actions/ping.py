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
from ..core import constants
from ..core.credential_provider_manager import (
    CredentialProviderManager,
    CommandResult,
)
from ..core import exceptions
from ..core import utils


class Ping(Action):
    def __init__(self) -> None:
        super().__init__(constants.PING_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = "Failed to connect to CyberArk Credential Provider!"

    def _extract_action_parameters(self) -> None:
        self.params.integration_parameters = utils.get_integration_parameters(
            self.soar_action
        )

    def _init_api_clients(self) -> CredentialProviderManager:
        return CredentialProviderManager(
            integration_parameters=self.params.integration_parameters
        )

    def _validate_params(self) -> None:
        if (
            self.params.integration_parameters.ssh_private_key_path
            and not self.params.integration_parameters.ssh_private_key_path.is_file()
        ):
            raise exceptions.CyberArkCredentialProviderValidationError(
                "SSH private key file not found at: "
                f"{self.params.integration_parameters.ssh_private_key_path}"
            )

    def _perform_action(self, _) -> None:
        result: CommandResult = self.api_client.test_connectivity()

        if result.exit_code != 0:
            raise exceptions.CyberArkCredentialProviderManagerError(
                f"{self.error_output_message}. Error is {result.error}"
            )
        self.output_message = (
            "Successfully connected to CyberArk Credential Provider "
            "with the provided connection parameters!"
        )
        self.logger.info(self.output_message)
        self.logger.info("Starting action finalizing steps")


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
