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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    POSSIBLE_INDICATOR_TYPES,
    POSSIBLE_ACTION_TYPES,
    POSSIBLE_SEVERITIES,
    LOGIN_API_ROOT_DEFAULT,
    PROVIDER_NAME,
    LIST_INDICATORS_SCRIPT_NAME,
)
from ..core.MicrosoftDefenderATPManager import MicrosoftDefenderATPManager

TABLE_NAME = "Found Indicators"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_INDICATORS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
    )

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        input_type=str,
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
        is_mandatory=True,
    )
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Azure Active Directory ID",
        input_type=str,
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
    )

    indicator_values = extract_action_param(
        siemplify, param_name="Indicators", input_type=str, is_mandatory=False
    )
    indicator_types = extract_action_param(
        siemplify, param_name="Indicator Types", input_type=str, is_mandatory=False
    )
    actions = extract_action_param(
        siemplify, param_name="Actions", input_type=str, is_mandatory=False
    )
    severities = extract_action_param(
        siemplify, param_name="Severity", input_type=str, is_mandatory=False
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        print_value=True,
        default_value=50,
        input_type=int,
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    indicator_values = MicrosoftDefenderATPManager.convert_comma_separated_to_list(
        indicator_values
    )
    indicator_types = MicrosoftDefenderATPManager.convert_comma_separated_to_list(
        indicator_types
    )
    actions = MicrosoftDefenderATPManager.convert_comma_separated_to_list(actions)
    severities = MicrosoftDefenderATPManager.convert_comma_separated_to_list(severities)

    try:
        if limit and limit <= 0:
            raise Exception(
                'Invalid value was provided for "Max Results to Return". '
                "Positive number should be provided"
            )

        invalid_ind_types = [
            ind_type
            for ind_type in indicator_types
            if ind_type.lower() not in [t.lower() for t in POSSIBLE_INDICATOR_TYPES]
        ]

        if invalid_ind_types:
            raise Exception(
                'invalid value provided for the parameter "Indicator Types". Possible values: '
                "{}.".format(
                    MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                        POSSIBLE_INDICATOR_TYPES
                    )
                )
            )

        invalid_actions = [
            act
            for act in actions
            if act.lower() not in [a.lower() for a in POSSIBLE_ACTION_TYPES]
        ]

        if invalid_actions:
            raise Exception(
                'invalid value provided for the parameter "Actions". Possible values: '
                "{}.".format(
                    MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                        POSSIBLE_ACTION_TYPES
                    )
                )
            )

        invalid_severities = [
            sev
            for sev in severities
            if sev.lower() not in [s.lower() for s in POSSIBLE_SEVERITIES]
        ]

        if invalid_severities:
            raise Exception(
                'invalid value provided for the parameter "Severity". Possible values: '
                "{}.".format(
                    MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                        POSSIBLE_SEVERITIES
                    )
                )
            )

        microsoft_defender_atp = MicrosoftDefenderATPManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            resource=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            entities_scope=True,
        )

        indicators = microsoft_defender_atp.get_entities(
            entities=indicator_values,
            types=indicator_types,
            actions=actions,
            severities=severities,
        )
        indicators = indicators[:limit] if limit else indicators
        if indicators:
            output_message = "Successfully found indicators for the provided criteria in Microsoft Defender ATP"
            siemplify.result.add_result_json(
                [indicator.to_json() for indicator in indicators]
            )
            siemplify.result.add_data_table(
                title=TABLE_NAME,
                data_table=construct_csv(
                    [indicator.to_table() for indicator in indicators]
                ),
            )
        else:
            output_message = "No indicators were found for the provided criteria in Microsoft Defender ATP."
            result_value = False

    except Exception as e:
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
