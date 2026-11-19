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

from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon.extraction import extract_configuration_param
from ..core import constants
from ..core.IntezerManager import IntezerManager


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            "Successfully connected to the "
            f"{constants.INTEGRATION_DISPLAY_NAME} server with the provided "
            "connection parameters!"
        )
        self.error_output_message = (
            "Failed to connect to the " f"{constants.INTEGRATION_DISPLAY_NAME} service!"
        )

    def _extract_parameters(self) -> None:
        # Configuration Parameters
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        )
        self.params.api_key = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API key",
            is_mandatory=True,
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

    def _validate_params(self) -> None:
        return

    def _init_managers(self) -> IntezerManager:
        return IntezerManager(
            api_root=self.params.api_root,
            api_key=self.params.api_key,
            verify_ssl=self.params.verify_ssl,
            siemplify_logger=self.logger,
        )

    def _perform_action(self, manager: IntezerManager, _=None) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)

        self.logger.info("Testing connectivity")
        manager.test_connectivity()
        self.logger.info("Successfully connected to Intezer")


def main() -> None:
    Ping(constants.PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
