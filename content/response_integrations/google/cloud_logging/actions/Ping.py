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
from cloud_logging.core import consts
from cloud_logging.core.CloudLoggingApiManager import CloudLoggingApiManager
from cloud_logging.core.CloudLoggingAuthManager import build_api_manager_params, build_auth_manager


class Ping(Action):

    def __init__(self) -> None:
        super().__init__(consts.PING_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{consts.PING_SCRIPT_NAME}".'
        )

    def _init_api_clients(self) -> CloudLoggingApiManager:
        auth_manager = build_auth_manager(self.soar_action)
        api_params = build_api_manager_params(auth_manager)

        return CloudLoggingApiManager(auth_manager.prepare_session(), api_params)

    def _perform_action(self, _: None) -> None:

        self.logger.info("Testing connectivity")
        self.api_client.test_connectivity()
        message = (
            f"Successfully connected to the {consts.INTEGRATION_DISPLAY_NAME} "
            "server with the provided connection parameters!"
        )
        self.logger.info(message)
        self.output_message = message


def main() -> None:
    Ping().run()


if __name__ == "__main__":
    main()
