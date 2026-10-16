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
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.sap_erp_manager import SapErpAuthError, SapErpManager


class ActivateAuditLogAction(Action):
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
        self.sap_client_number = str(
            extract_action_param(
                siemplify=self.soar_action,
                param_name="SAP Client Number",
                is_mandatory=True,
                print_value=True,
            )
            or ""
        ).strip()
        self.sap_instance_name = (
            extract_action_param(
                siemplify=self.soar_action,
                param_name="SAP Instance Name",
                is_mandatory=True,
                print_value=True,
            )
            or ""
        ).strip()

    def _validate_params(self) -> None:
        if not self.cloud_run_url:
            raise ValueError("Cloud Run Service URL is missing.")
        if not self.sap_client_number:
            raise ValueError("SAP Client Number is missing.")
        if not self.sap_instance_name:
            raise ValueError("SAP Instance Name is missing.")

    def _init_api_clients(self) -> SapErpManager:
        return SapErpManager(
            cloud_run_url=self.cloud_run_url, verify_ssl=self.verify_ssl
        )

    def _perform_action(self, _: None = None) -> None:
        self.result_value = False
        manager = self.api_client

        try:
            response = manager.execute_function(
                function_id="ACTIVATE_AUDIT_LOG",
                sap_instance=self.sap_instance_name,
                sap_client=self.sap_client_number,
                payload={},
            )
        except SapErpAuthError as e:
            self.logger.error(f"Authentication error calling SAP RFC Gateway: {e}")
            self.execution_state = ExecutionState.FAILED
            self.output_message = f"Authentication error: {e}"
            return
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error calling SAP RFC Gateway: {e}")
            self.execution_state = ExecutionState.FAILED
            self.output_message = f"Failed to communicate with SAP RFC Gateway: {e}"
            return

        if not response.ok:
            error_detail = manager.extract_error_detail(response)
            self.logger.error(
                f"Request failed with status {response.status_code}. Error: {error_detail}"
            )
            self.execution_state = ExecutionState.FAILED
            self.output_message = (
                f"Proxy request failed (HTTP {response.status_code}): {error_detail}"
            )
            return

        try:
            response_json = response.json()
        except ValueError:
            self.logger.error(f"Received non-JSON response. Text: {response.text}")
            self.execution_state = ExecutionState.FAILED
            self.output_message = (
                f"Received unexpected non-JSON response: {response.text}"
            )
            return

        self.soar_action.result.add_result_json(response_json)
        sap_status = response_json.get("status")

        if sap_status == "SUCCESS":
            self.logger.info("Successfully activated SAP audit log.")
            self.result_value = True
            self.execution_state = ExecutionState.COMPLETED
            self.output_message = "Successfully activated SAP audit log."
        else:
            error_messages = [
                ret.get("message", "Unknown error")
                for ret in response_json.get("return", [])
                if isinstance(ret, dict)
            ]
            error_summary = (
                "; ".join(error_messages)
                or response_json.get("error")
                or f"Unexpected SAP status: {sap_status}"
            )
            self.logger.error(f"SAP returned an error: {error_summary}")
            self.execution_state = ExecutionState.FAILED
            self.output_message = (
                f"Failed to activate audit log. SAP Error: {error_summary}"
            )


def main() -> None:
    ActivateAuditLogAction(name="Activate Audit Log").run()


if __name__ == "__main__":
    main()