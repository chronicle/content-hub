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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from threat_q.core.ThreatQManager import ThreatQManager
from threat_q.core.constants import INTEGRATION_NAME, UPDATE_INDICATOR_SCORE
from threat_q.core.ThreatQUtils import *
from threat_q.core.custom_exceptions import IndicatorScoreException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INDICATOR_SCORE
    # Variables Definitions.
    result_value = True
    execution_status = EXECUTION_STATE_COMPLETED
    output_message = ""

    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)

    server_address = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ServerAddress"
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ClientId"
    )

    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )

    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )

    score = extract_action_param(
        siemplify,
        param_name="Score",
        default_value="7 - Medium",
        is_mandatory=True,
        print_value=True,
    )

    score_validation = extract_action_param(
        siemplify,
        param_name="Score Validation",
        default_value="Highest Score",
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 10 + " Main - Started " + "=" * 10)
    updated_entities = []
    failed_entities = []
    json_results = {}

    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)

        for entity in siemplify.target_entities:

            try:
                indicator_obj = threatq_manager.update_indicator_score(
                    entity.identifier, score, score_validation
                )
                updated_entities.append(entity)
                json_results[entity.identifier] = indicator_obj.to_json()
                siemplify.LOGGER.info(f"Finished processing entity:{entity.identifier}")

            except IndicatorScoreException as e:
                output_message += (
                    f"Unable to get indicators for {entity.identifier}. Reason: {e} \n"
                )
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed processing entity:{entity.identifier}")
                siemplify.LOGGER.exception(e)
                result_value = False
            except Exception as e:
                output_message += f"Unable to get indicators for {entity.identifier} \n"
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed processing entity:{entity.identifier}")
                siemplify.LOGGER.exception(e)
                result_value = False

        if updated_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message = f"Successfully updated score for the indicator with value: {', '.join([entity.identifier for entity in updated_entities])} in ThreatQ."
            result_value = True

        if not updated_entities and not failed_entities:
            output_message = "No data found for entities."
            result_value = False

        if failed_entities:
            output_message += "\nAction was not able to update score for the indicator with value: {0} in ThreatQ.".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

    except Exception as e:
        output_message = f'Error executing action "Update Indicator Score". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        execution_status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("=" * 10 + " Main - Finished " + "=" * 10)
    siemplify.LOGGER.info(
        f"Status: {execution_status}, Result Value: {result_value}, Output Message: {output_message}"
    )
    siemplify.end(output_message, result_value, execution_status)


if __name__ == "__main__":
    main()
