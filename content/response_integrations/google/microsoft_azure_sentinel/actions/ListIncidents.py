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
from TIPCommon.transformation import construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    LIST_INCIDENTS_SCRIPT_NAME,
    INCIDENTS_TABLE_NAME,
)
from ..core.utils import string_to_multi_value
from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_INCIDENTS_SCRIPT_NAME
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", print_value=True, input_type=int
    )
    statuses = string_to_multi_value(
        extract_action_param(siemplify, param_name="Status", print_value=True)
    )
    severities = string_to_multi_value(
        extract_action_param(siemplify, param_name="Severity", print_value=True)
    )
    limit = extract_action_param(
        siemplify,
        param_name="How Many Incidents to Fetch",
        print_value=True,
        input_type=int,
    )
    limit = limit if limit and limit > 0 else None

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = "Action was not able to find any incidents"

    try:
        MicrosoftAzureSentinelManager.validate_statuses(statuses)

        MicrosoftAzureSentinelManager.validate_severities(severities)

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

        incidents = manager.get_incidents_by_filter(
            time_frame=time_frame, statuses=statuses, severities=severities, limit=limit
        )

        if incidents:
            siemplify.result.add_result_json(
                [incident.to_json() for incident in incidents]
            )
            siemplify.result.add_data_table(
                title=INCIDENTS_TABLE_NAME,
                data_table=construct_csv([incident.to_csv() for incident in incidents]),
            )

            output_message = f"Successfully returned {PRODUCT_NAME} incidents"

    except Exception as e:
        output_message = (
            f"Error executing action '{LIST_INCIDENTS_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
