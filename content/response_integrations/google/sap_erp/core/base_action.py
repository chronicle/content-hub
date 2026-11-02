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

"""Base action classes for SAP ERP actions."""

from __future__ import annotations

from abc import ABC
from typing import Any

import requests
from TIPCommon.base.action import Action, ExecutionState
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from .constants import (
    CLOUD_RUN_URL_PARAM,
    INTEGRATION_IDENTIFIER,
    SAP_CLIENT_LENGTH,
    SAP_CLIENT_NUMBER_PARAM,
    SAP_INSTANCE_NAME_PARAM,
    SERVICE_ACCOUNT_JSON_PARAM,
    VERIFY_SSL_PARAM,
    WORKLOAD_IDENTITY_EMAIL_PARAM,
)
from .exceptions import SapErpAuthError, SapErpError
from .sap_erp_manager import SapErpManager


class SapErpAction(Action, ABC):
    """Base action class for all SAP ERP actions."""

    def _extract_integration_config(self) -> None:
        """Extract shared integration configuration parameters."""
        self.cloud_run_url: str = (
            extract_configuration_param(
                siemplify=self.soar_action,
                provider_name=INTEGRATION_IDENTIFIER,
                param_name=CLOUD_RUN_URL_PARAM,
                is_mandatory=True,
                print_value=True,
            )
            or ""
        ).strip()
        self.service_account_json: str | None = extract_configuration_param(
            siemplify=self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name=SERVICE_ACCOUNT_JSON_PARAM,
            is_mandatory=False,
            print_value=False,
        )
        self.workload_identity_email: str | None = extract_configuration_param(
            siemplify=self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name=WORKLOAD_IDENTITY_EMAIL_PARAM,
            is_mandatory=False,
            print_value=True,
        )
        self.verify_ssl: bool = extract_configuration_param(
            siemplify=self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name=VERIFY_SSL_PARAM,
            input_type=bool,
            default_value=True,
            is_mandatory=False,
            print_value=True,
        )

    def _extract_action_parameters(self) -> None:
        """Extract configuration parameters (subclasses append action parameters)."""
        self._extract_integration_config()

    def _init_api_clients(self) -> SapErpManager:
        """Initialize and return the SAP ERP gateway manager.

        Returns:
            SapErpManager: Configured gateway manager instance.

        """
        return SapErpManager(
            cloud_run_url=self.cloud_run_url,
            service_account_json=self.service_account_json,
            workload_identity_email=self.workload_identity_email,
            verify_ssl=self.verify_ssl,
        )


class SapErpRfcAction(SapErpAction, ABC):
    """Base class for SAP ERP actions that invoke an RFC function on the gateway."""

    function_id: str
    success_message: str = ""
    failure_prefix: str = ""

    def _extract_action_parameters(self) -> None:
        """Extract integration config and common SAP RFC parameters."""
        super()._extract_action_parameters()
        self.sap_instance_name: str = (
            extract_action_param(
                siemplify=self.soar_action,
                param_name=SAP_INSTANCE_NAME_PARAM,
                is_mandatory=True,
                print_value=True,
            )
            or ""
        ).strip()
        self.sap_client_number: str = str(
            extract_action_param(
                siemplify=self.soar_action,
                param_name=SAP_CLIENT_NUMBER_PARAM,
                is_mandatory=True,
                print_value=True,
            )
            or ""
        ).strip()
        self._extract_rfc_parameters()

    def _extract_rfc_parameters(self) -> None:
        """Extract function-specific action parameters (optional hook for subclasses)."""

    def _build_payload(self) -> dict[str, Any]:  # ruff: ignore[no-self-use]
        """Build the RFC function payload dictionary.

        Returns:
            Payload dictionary for the gateway request.

        """
        return {}

    def _get_success_message(self) -> str:
        """Return the action output message on SAP RFC success.

        Returns:
            Success output message string.

        """
        return self.success_message

    def _get_failure_prefix(self) -> str:
        """Return the prefix for SAP-level failure messages.

        Returns:
            Failure message prefix string.

        """
        return self.failure_prefix

    def _validate_params(self) -> None:
        """Validate that SAP Client Number (MANDT) is a 3-digit numeric string.

        Raises:
            SapErpError: If ``sap_client_number`` is not a 3-digit number.

        """
        if not (
            self.sap_client_number.isdigit()
            and len(self.sap_client_number) == SAP_CLIENT_LENGTH
        ):
            msg = (
                f"{SAP_CLIENT_NUMBER_PARAM} must be a 3-digit numeric string "
                f"(got '{self.sap_client_number}')."
            )
            raise SapErpError(msg)

    def _perform_action(self, _: object = None) -> None:
        """Execute the configured SAP RFC function and process the gateway response.

        Raises:
            SapErpError: If authentication, HTTP transport, JSON parsing, or SAP
                RFC execution fails.

        """
        manager: SapErpManager = self.api_client

        try:
            response = manager.execute_function(
                function_id=self.function_id,
                sap_instance=self.sap_instance_name,
                sap_client=self.sap_client_number,
                payload=self._build_payload(),
            )
        except SapErpAuthError as e:
            self.logger.exception("Authentication error calling SAP RFC Gateway")
            msg = f"Authentication error: {e}"
            raise SapErpError(msg) from e
        except requests.exceptions.RequestException as e:
            self.logger.exception("Network error calling SAP RFC Gateway")
            msg = f"Failed to communicate with SAP RFC Gateway: {e}"
            raise SapErpError(msg) from e

        if not response.ok:
            error_detail = manager.extract_error_detail(response)
            msg = f"Proxy request failed (HTTP {response.status_code}): {error_detail}"
            self.logger.error(msg)
            raise SapErpError(msg)

        try:
            response_json = response.json()
        except ValueError as e:
            msg = f"Received unexpected non-JSON response: {response.text}"
            self.logger.exception(msg)
            raise SapErpError(msg) from e

        self.soar_action.result.add_result_json(response_json)
        sap_status = response_json.get("status")

        if sap_status != "SUCCESS":
            error_messages = [
                ret.get("message", "Unknown error")
                # "return" may be present but null.
                for ret in (response_json.get("return") or [])
                if isinstance(ret, dict)
            ]
            error_summary = (
                "; ".join(error_messages)
                or response_json.get("error")
                or f"Unexpected SAP status: {sap_status}"
            )
            msg = f"{self._get_failure_prefix()}. SAP Error: {error_summary}"
            self.logger.error(msg)
            raise SapErpError(msg)

        success_message = self._get_success_message()
        self.logger.info(success_message)
        self.result_value = True
        self.execution_state = ExecutionState.COMPLETED
        self.output_message = success_message
