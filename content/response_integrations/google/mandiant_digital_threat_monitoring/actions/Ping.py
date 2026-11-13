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

from typing import Any

from TIPCommon.base.action import Action
from ..core import api_utils
from ..core import constants
from ..core import AuthenticationManager as auth_manager
from ..core import MandiantDTMManager as api_manager


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Successfully connected to the {constants.PROVIDER_NAME} server with the "
            f"provided connection parameters!"
        )
        self.error_output_message = (
            f"Failed to connect to the {constants.PROVIDER_NAME} server!"
        )

    def _extract_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params

    def _validate_params(self) -> None:
        pass

    def _init_managers(self) -> api_manager.ApiManager:
        session = auth_manager.get_authenticated_session(
            auth_params=self.params.auth_params
        )

        return api_manager.ApiManager(
            session=session,
            api_params=self.params.api_params,
            logger=self.logger,
            gti_api_key=self.params.auth_params.gti_api_key,
        )

    def _perform_action(self, manager: Any | None = None, _=None) -> None:
        manager.test_connectivity()


def main() -> None:
    Ping(constants.PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
