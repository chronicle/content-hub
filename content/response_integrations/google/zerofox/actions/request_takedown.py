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
from ..core import action_init
from ..core import constants
from ..core import exceptions
from ..core import zerofox_manager as api_manager


class RequestTakedown(Action):

    def __init__(self) -> None:
        super().__init__(constants.REQUEST_TAKEDOWN_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False
        self.error_output_message: str = (
            f'Error executing action "{constants.REQUEST_TAKEDOWN_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.alert_id: str = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        pass

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        try:
            self.api_client.request_takedown(alert_id=self.params.alert_id)
            self.result_value = True
            self.output_message = (
                "Successfully requested takedown for alert with ID "
                f"{self.params.alert_id}."
            )

        except exceptions.ZerofoxManagerError as error:
            raise exceptions.AlertNotFoundError(
                f"Alert with ID {self.params.alert_id} wasn't found in "
                "Zerofox."
            ) from error


def main() -> NoReturn:
    RequestTakedown().run()


if __name__ == "__main__":
    main()
