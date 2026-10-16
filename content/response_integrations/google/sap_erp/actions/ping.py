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
from TIPCommon.base.action import Action, ExecutionState
from TIPCommon.extraction import extract_configuration_param

from ..core.sap_erp_manager import SapErpAuthError, SapErpManager

INTEGRATION_DISPLAY_NAME = "SAP ERP"
# Exact wording required by the repository style guide for Ping actions.
SUCCESS_MESSAGE = (
    f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server "
    "with the provided connection parameters!"
)
FAILURE_TEMPLATE = (
    f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {{error}}"
)

IAM_DENIED_STATUSES = {401, 403}
# GatewayHttpHandler only accepts POST, so a healthy gateway answers GET with
# HTTP 405 {"error": "Only POST requests are supported."}.
HEALTHY_STATUSES = {200, 405}


class PingAction(Action):
    """Test authentication to, and reachability of, the SAP RFC Gateway."""

    def _extract_action_parameters(self) -> None:
        self.cloud_run_url = (
            extract_configuration_param(
                siemplify=self.soar_action,
                provider_name="SapErp",
                param_name="Cloud Run Service URL",
                is_mandatory=True,
                print_value=False,
            )
            or ""
        ).strip()
        self.verify_ssl = extract_configuration_param(
            siemplify=self.soar_action,
            provider_name="SapErp",
            param_name="Verify SSL",
            input_type=bool,
            default_value=True,
            is_mandatory=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        if not self.cloud_run_url:
            msg = "Cloud Run Service URL is missing."
            raise ValueError(msg)

    def _init_api_clients(self) -> SapErpManager:
        return SapErpManager(
            cloud_run_url=self.cloud_run_url, verify_ssl=self.verify_ssl
        )

    def _fail(self, error: str) -> None:
        self.execution_state = ExecutionState.FAILED
        self.output_message = FAILURE_TEMPLATE.format(error=error)

    def _perform_action(self, _: None = None) -> None:
        self.result_value = False
        manager = self.api_client

        try:
            response = manager.ping()
        except SapErpAuthError:
            self.logger.exception("Authentication token generation failed")
            self._fail(
                "Failed to generate Google Cloud authentication token. "
                "Verify service account credentials and permissions."
            )
            return
        except requests.exceptions.RequestException as e:
            self.logger.exception("Network error connecting to Cloud Run service")
            self._fail(f"Network error: {e}")
            return

        if response.status_code in IAM_DENIED_STATUSES:
            self.logger.error(
                f"Cloud Run IAM authentication failed with HTTP {response.status_code}."
            )
            self._fail(
                f"Authentication to Cloud Run failed (HTTP {response.status_code}). "
                "Verify the caller has roles/run.invoker on the service."
            )
            return

        if response.status_code not in HEALTHY_STATUSES:
            error_detail = manager.extract_error_detail(response)
            self.logger.error(
                "Unexpected status from Cloud Run service "
                f"(HTTP {response.status_code}): {error_detail}"
            )
            self._fail(
                f"Cloud Run service returned unexpected HTTP {response.status_code}: "
                f"{error_detail}"
            )
            return

        self.logger.info("Successfully pinged SAP ERP Cloud Run service.")
        self.result_value = True
        self.execution_state = ExecutionState.COMPLETED
        self.output_message = SUCCESS_MESSAGE


def main() -> None:
    """Run the Ping action."""
    PingAction(name="Ping").run()


if __name__ == "__main__":
    main()
