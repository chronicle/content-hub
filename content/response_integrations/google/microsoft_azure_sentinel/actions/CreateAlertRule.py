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
from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.constants import CREATE_ALERT_RULE_SCRIPT_NAME, INTEGRATION_NAME, PRODUCT_NAME
from ..core.utils import string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_ALERT_RULE_SCRIPT_NAME
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

    enable_alert_rule = extract_action_param(
        siemplify,
        param_name="Enable Alert Rule",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )
    severity = extract_action_param(
        siemplify, param_name="Severity", is_mandatory=True, print_value=True
    )
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    frequency = extract_action_param(
        siemplify, param_name="Frequency", is_mandatory=True, print_value=True
    )
    lookup_period = extract_action_param(
        siemplify,
        param_name="Period of Lookup Data",
        is_mandatory=True,
        print_value=True,
    )
    trigger_operator = extract_action_param(
        siemplify, param_name="Trigger Operator", is_mandatory=True, print_value=True
    )
    trigger_threshold = extract_action_param(
        siemplify,
        param_name="Trigger Threshold",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )
    enable_suppression = extract_action_param(
        siemplify,
        param_name="Enable Suppression",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    suppression_duration = extract_action_param(
        siemplify,
        param_name="Suppression Duration",
        is_mandatory=True,
        print_value=True,
    )
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    tactics = string_to_multi_value(
        extract_action_param(siemplify, param_name="Tactics", print_value=True)
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = f"Successfully created {PRODUCT_NAME} alert rule!"
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        MicrosoftAzureSentinelManager.validate_tactics(tactics=tactics)
        MicrosoftAzureSentinelManager.validate_alert_rule_severities(
            severities=[severity]
        )
        MicrosoftAzureSentinelManager.validate_trigger_operators(
            trigger_operators=[trigger_operator]
        )
        MicrosoftAzureSentinelManager.validate_duration(frequency)
        MicrosoftAzureSentinelManager.validate_duration(lookup_period)
        MicrosoftAzureSentinelManager.validate_duration(suppression_duration)

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

        alert_rule = manager.create_alert_rule(
            enable_alert_rule=enable_alert_rule,
            name=name,
            severity=severity,
            query=query,
            frequency=frequency,
            lookup_period=lookup_period,
            trigger_operator=trigger_operator,
            trigger_threshold=trigger_threshold,
            enable_suppression=enable_suppression,
            suppression_duration=suppression_duration,
            description=description,
            tactics=tactics,
        )

        siemplify.result.add_result_json(alert_rule.to_json())
        siemplify.LOGGER.info(output_message)
    except Exception as e:
        output_message = (
            f"Error executing action '{CREATE_ALERT_RULE_SCRIPT_NAME}'. Reason: {e}"
        )
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
