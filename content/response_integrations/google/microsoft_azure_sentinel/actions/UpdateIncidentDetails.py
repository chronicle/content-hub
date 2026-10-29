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
import time

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager
from ..core.exceptions import MicrosoftAzureSentinelConflictError
from ..core.constants import (
    UPDATE_INCIDENT_DETAILS_SCRIPT_NAME,
    PRODUCT_NAME,
    INTEGRATION_NAME,
)

ADDITIONAL_DEFAULT_FOR_VALIDATION = ["Not Updated"]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    login_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="OAUTH2 Login Endpoint Url",
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Secret"
    )
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure Active Directory ID",
    )
    workspace_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure Sentinel Workspace Name",
    )
    resource = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Azure Resource Group"
    )
    subscription_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Azure Subscription ID"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    incident_number = extract_action_param(
        siemplify,
        param_name="Incident Case Number",
        is_mandatory=True,
        print_value=True,
    )
    title = extract_action_param(siemplify, param_name="Title", print_value=True)
    incident_status = extract_action_param(
        siemplify, param_name="Status", print_value=True
    )
    severity = extract_action_param(siemplify, param_name="Severity", print_value=True)
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    assigned_to = extract_action_param(
        siemplify, param_name="Assigned To", print_value=True
    )
    close_reason = extract_action_param(
        siemplify, param_name="Closed Reason", print_value=True
    )
    closing_comment = extract_action_param(
        siemplify, param_name="Closing Comment", print_value=True
    )

    number_of_retries = extract_action_param(
        siemplify,
        param_name="Number of retries",
        print_value=True,
        input_type=int,
        default_value=1,
    )
    retry_every = extract_action_param(
        siemplify,
        param_name="Retry Every",
        print_value=True,
        input_type=int,
        default_value=20,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    if number_of_retries in ["", None, [], {}]:
        number_of_retries = 1

    if retry_every in ["", None, [], {}]:
        retry_every = 20

    output_message = (
        f"{PRODUCT_NAME} Incident with case number {incident_number} was not found!"
    )
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        MicrosoftAzureSentinelManager.validate_severities(
            [severity], ADDITIONAL_DEFAULT_FOR_VALIDATION
        )
        MicrosoftAzureSentinelManager.validate_statuses(
            [incident_status], ADDITIONAL_DEFAULT_FOR_VALIDATION
        )
        MicrosoftAzureSentinelManager.validate_close_reasons(
            [close_reason], ADDITIONAL_DEFAULT_FOR_VALIDATION
        )

        manager = MicrosoftAzureSentinelManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            resource=resource,
            subscription_id=subscription_id,
            login_url=login_url,
            verify_ssl=verify_ssl,
        )
        number_of_tries = 1
        while True:
            try:
                incident = manager.update_incident(
                    incident_number=incident_number,
                    title=title,
                    status=incident_status,
                    severity=severity,
                    description=description,
                    assigned_to=assigned_to,
                    close_reason=close_reason,
                    closing_comment=closing_comment,
                )
                break
            except MicrosoftAzureSentinelConflictError as error:
                if number_of_tries > number_of_retries:
                    raise
                number_of_tries += 1
                siemplify.LOGGER.error(str(error))
                siemplify.LOGGER.info(
                    f"Retrying update of Microsoft Azure Sentinel incident {incident_number}"
                )
                time.sleep(retry_every)

        if incident:
            output_message = f"Successfully updated Microsoft Azure Sentinel incident {incident.name}"
            siemplify.result.add_result_json(incident.to_json())

        siemplify.LOGGER.info(output_message)

    except Exception as e:
        output_message = f"Error executing action '{UPDATE_INCIDENT_DETAILS_SCRIPT_NAME}'. Reason: {e}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
