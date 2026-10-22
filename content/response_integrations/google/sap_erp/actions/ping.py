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

import requests
from TIPCommon.base.action import ExecutionState

from ..core.base_action import SapErpAction
from ..core.constants import (
    HEALTHY_STATUSES,
    IAM_DENIED_STATUSES,
    INTEGRATION_DISPLAY_NAME,
    PING_SCRIPT_NAME,
)
from ..core.exceptions import SapErpAuthError, SapErpError

# Exact wording required by the repository style guide for Ping actions.
SUCCESS_MESSAGE = (
    f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server "
    "with the provided connection parameters!"
)


class PingAction(SapErpAction):
    """Test authentication to, and reachability of, the SAP RFC Gateway."""

    def __init__(self, name: str = PING_SCRIPT_NAME) -> None:
        super().__init__(name)
        self.error_output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server!"
        )

    def _perform_action(self, _: object = None) -> None:
        """Send an authenticated ping request to the Cloud Run gateway.

        Raises:
            SapErpError: If authentication, network transport, or gateway
                status check fails.

        """
        manager = self.api_client

        try:
            response = manager.ping()
        except SapErpAuthError as e:
            self.logger.exception("Authentication token generation failed")
            msg = (
                "Failed to generate Google Cloud authentication token. "
                "Verify service account credentials and permissions."
            )
            raise SapErpError(msg) from e
        except requests.exceptions.RequestException as e:
            self.logger.exception("Network error connecting to Cloud Run service")
            msg = f"Network error: {e}"
            raise SapErpError(msg) from e

        if response.status_code in IAM_DENIED_STATUSES:
            msg = (
                f"Authentication to Cloud Run failed (HTTP {response.status_code}). "
                "Verify the caller has roles/run.invoker on the service."
            )
            self.logger.error(msg)
            raise SapErpError(msg)

        if response.status_code not in HEALTHY_STATUSES:
            error_detail = manager.extract_error_detail(response)
            msg = (
                f"Cloud Run service returned unexpected HTTP {response.status_code}: "
                f"{error_detail}"
            )
            self.logger.error(msg)
            raise SapErpError(msg)

        self.logger.info("Successfully pinged SAP ERP Cloud Run service.")
        self.result_value = True
        self.execution_state = ExecutionState.COMPLETED
        self.output_message = SUCCESS_MESSAGE


def main() -> None:
    """Run the Ping action."""
    PingAction().run()


if __name__ == "__main__":
    main()
