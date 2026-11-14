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
from TIPCommon.transformation import flat_dict_to_csv
from ..core.constants import (
    GET_ALERT_RULE_DETAILS_SCRIPT_NAME,
    INTEGRATION_NAME,
    ALERT_RULE_DETAILS_TABLE,
)
from ..core.MicrosoftAzureSentinelManager import (
    MicrosoftAzureSentinelManager,
    MicrosoftAzureSentinelManagerError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ALERT_RULE_DETAILS_SCRIPT_NAME
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
    alert_rule_id = extract_action_param(
        siemplify, param_name="Alert Rule ID", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = f"No alert rule was found with Alert Rule ID: {alert_rule_id}"
    result_value = True
    status = EXECUTION_STATE_COMPLETED

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
            force_check_connectivity=True,
        )

        alert_rule = manager.get_alert_rule(alert_rule_id=alert_rule_id)
        if alert_rule:
            siemplify.result.add_result_json(alert_rule.to_json())
            siemplify.result.add_data_table(
                title=ALERT_RULE_DETAILS_TABLE,
                data_table=flat_dict_to_csv(alert_rule.to_table()),
            )
            output_message = f"Successfully returned Microsoft Azure Sentinel alert rule {alert_rule_id} details"

        siemplify.LOGGER.info(output_message)

    except MicrosoftAzureSentinelManagerError as e:
        output_message = f"Error executing action '{GET_ALERT_RULE_DETAILS_SCRIPT_NAME}'. Reason: {e}"
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
