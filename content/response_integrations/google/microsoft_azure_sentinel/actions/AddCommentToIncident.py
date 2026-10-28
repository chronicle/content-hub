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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager
from ..core.constants import (
    ADD_COMMENT_TO_INCIDENT_SCRIPT_NAME,
    INTEGRATION_NAME,
    PRODUCT_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_INCIDENT_SCRIPT_NAME
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
        param_name="Incident Number",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    comment = extract_action_param(
        siemplify, param_name="Comment to Add", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    output_message = (
        f"Microsoft Azure Sentinel incident {incident_number} was not found!"
    )
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
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

        incident = manager.get_incident_by_incident_number(
            incident_number=incident_number
        )

        if incident:
            incident_comment_data = manager.add_comment_to_incident(
                incident_name=incident.name, comment=comment
            )
            siemplify.result.add_result_json(incident_comment_data.to_json())
            result_value = True
            output_message = f"Successfully added a comment to {PRODUCT_NAME} incident {incident_number}"

    except Exception as e:
        output_message = f"Error executing action '{ADD_COMMENT_TO_INCIDENT_SCRIPT_NAME}'. Reason: {e}"
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
