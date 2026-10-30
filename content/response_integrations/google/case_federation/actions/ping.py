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

import os

from google.auth.transport.requests import Request
from TIPCommon.base.action import Action
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.auth import get_secops_siem_tenant_credentials

from ..core.constants import (
    GCP_PROJECT_ID_ENV_VAR,
    INTEGRATION_NAME,
    PING_SCRIPT_NAME,
)

SUCCESS_MESSAGE: str = "Successfully connected to the API Service server with the provided connection parameters!"
ERROR_MESSAGE: str = "Failed to connect to the API Service server!"


class Ping(Action):
    def _extract_action_parameters(self) -> None:
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            is_mandatory=False,
            default_value=True,
            input_type=bool,
            print_value=True,
        )

    def _validate_params(self) -> None:
        pass

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _: str | None = None) -> None:
        self.error_output_message = ERROR_MESSAGE
        project_id = os.getenv(GCP_PROJECT_ID_ENV_VAR)
        credentials = get_secops_siem_tenant_credentials(chronicle_soar=self.soar_action, quota_project_id=project_id)
        auth_session = CreateSession.create_session()
        auth_session.verify = getattr(self.params, "verify_ssl", True)
        credentials.refresh(Request(session=auth_session))
        self.output_message = SUCCESS_MESSAGE


def main() -> None:
    """Run the ping action script."""
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
