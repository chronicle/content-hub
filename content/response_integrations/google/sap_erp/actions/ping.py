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

import requests
from TIPCommon.base.action import Action, ExecutionState
from TIPCommon.extraction import extract_configuration_param
from ..core.sap_erp_manager import SapErpAuthError, SapErpManager


INTEGRATION_DISPLAY_NAME = "SAP ERP"
SUCCESS_MESSAGE = (
    f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} gateway "
    "with the provided connection parameters!"
)
FAILURE_PREFIX = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} gateway!"


class PingAction(Action):
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
            raise ValueError("Cloud Run Service URL is missing.")

    def _init_api_clients(self) -> SapErpManager:
        return SapErpManager(
            cloud_run_url=self.cloud_run_url, verify_ssl=self.verify_ssl
        )

    def _perform_action(self, _: None = None) -> None:
        self.result_value = False
        manager = self.api_client

        try:
            response = manager.ping()
        except SapErpAuthError as e:
            self.logger.error(f"Authentication token generation failed: {e}")
            self.execution_state = ExecutionState.FAILED
            self.output_message = (
                f"{FAILURE_PREFIX} Failed to generate Google Cloud authentication "
                "token. Verify service account credentials and permissions."
            )
            return
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error connecting to Cloud Run service: {e}")
            self.execution_state = ExecutionState.FAILED
            self.output_message = f"{FAILURE_PREFIX} Network error: {e}"
            return

        if response.status_code in (401, 403):
            self.logger.error(
                f"Cloud Run IAM authentication failed with HTTP {response.status_code}."
            )
            self.execution_state = ExecutionState.FAILED
            self.output_message = (
                f"{FAILURE_PREFIX} Authentication to Cloud Run failed "
                f"(HTTP {response.status_code}). "
                "Verify the caller has roles/run.invoker on the service."
            )
            return

        # GatewayHttpHandler only accepts POST and returns HTTP 405 with
        # {"error": "Only POST requests are supported."} on GET when healthy.
        if response.status_code not in (200, 405):
            error_detail = manager.extract_error_detail(response)
            self.logger.error(
                f"Unexpected status from Cloud Run service (HTTP {response.status_code}): {error_detail}"
            )
            self.execution_state = ExecutionState.FAILED
            self.output_message = (
                f"{FAILURE_PREFIX} Cloud Run service returned unexpected "
                f"HTTP {response.status_code}: {error_detail}"
            )
            return

        self.logger.info("Successfully pinged SAP ERP Cloud Run service.")
        self.result_value = True
        self.execution_state = ExecutionState.COMPLETED
        self.output_message = SUCCESS_MESSAGE


def main() -> None:
    PingAction(name="Ping").run()


if __name__ == "__main__":
    main()