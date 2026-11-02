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
    LIST_ALERT_RULES_SCRIPT_NAME,
    INTEGRATION_NAME,
    PRODUCT_NAME,
    ALERT_RULES_TABLE_NAME,
)
from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager
from ..core.utils import string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ALERT_RULES_SCRIPT_NAME
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

    severities = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Alert Rule Severity", print_value=True
        )
    )
    types = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Fetch Specific Alert Rule Types", print_value=True
        )
    )
    tactics = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Fetch Specific Alert Rule Tactics", print_value=True
        )
    )
    enabled_alert_rules = extract_action_param(
        siemplify,
        param_name="Fetch only Enabled Alert Rules",
        print_value=True,
        input_type=bool,
    )
    max_rules_to_return = extract_action_param(
        siemplify, param_name="Max rules to return", print_value=True, input_type=int
    )
    max_rules_to_return = (
        max_rules_to_return if max_rules_to_return and max_rules_to_return > 0 else None
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = "No alert rules were found"

    try:
        MicrosoftAzureSentinelManager.validate_severities(severities=severities)
        MicrosoftAzureSentinelManager.validate_tactics(tactics=tactics)

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

        alert_rules = manager.get_alert_rules(
            severities=severities,
            types=types,
            tactics=tactics,
            only_enabled_rules=enabled_alert_rules,
            limit=max_rules_to_return,
        )

        if alert_rules:
            siemplify.result.add_result_json(
                [alert_rule.to_json() for alert_rule in alert_rules]
            )
            siemplify.result.add_data_table(
                title=ALERT_RULES_TABLE_NAME,
                data_table=construct_csv(
                    [alert_rule.to_table() for alert_rule in alert_rules]
                ),
            )

            output_message = (
                f"Successfully listed {PRODUCT_NAME} alert rules configured"
            )

        siemplify.LOGGER.info(output_message)

    except Exception as e:
        output_message = (
            f"Error executing action '{LIST_ALERT_RULES_SCRIPT_NAME}'. Reason: {e}"
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
