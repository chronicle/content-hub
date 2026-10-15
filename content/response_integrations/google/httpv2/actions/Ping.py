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
from ..core import api_utils
from ..core import AuthenticationManager as auth_manager
from ..core import HTTPV2Manager as api_manager
from ..core.constants import PING_SCRIPT_NAME, AUTH_METHOD


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = "Successfully tested connectivity."
        self.error_output_message = "Failed to test connectivity."
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params

    def _validate_parameters(self) -> None:
        api_utils.validate_configuration_params(
            soar_action=self.soar_action, auth_params=self.params.auth_params
        )
        self.params.api_params.auth_method = api_utils.get_auth_method(
            self.params.auth_params
        )

    def _init_api_clients(self) -> api_manager.ApiManager:
        self._validate_parameters()
        session, _ = auth_manager.get_authenticated_session(
            chronicle_soar=self.soar_action,
            auth_method=self.params.api_params.auth_method,
            auth_params=self.params.auth_params,
        )

        return api_manager.ApiManager(
            session=session, api_params=self.params.api_params, logger=self.logger
        )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()

        self.json_results = {
            "endpoint": (
                self.params.auth_params.auth_api_request_url
                if self.params.api_params.auth_method == AUTH_METHOD.get("ACCESS_TOKEN")
                else self.params.api_params.test_url
            )
        }


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
