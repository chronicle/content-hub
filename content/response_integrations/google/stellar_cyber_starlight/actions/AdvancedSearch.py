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
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.StellarCyberStarlightConstants import PROVIDER_NAME, ADVANCED_SEARCH_SCRIPT_NAME
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.StellarCyberStarlightManager import StellarCyberStarlightManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.StellarCyberStarlightExceptions import SearchExecutionException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADVANCED_SEARCH_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Key",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Parameters
    index = extract_action_param(
        siemplify, param_name="Index", is_mandatory=True, print_value=True
    )
    dsl_query = extract_action_param(
        siemplify, param_name="DSL Query", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = StellarCyberStarlightManager(
            api_root=api_root,
            username=username,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
        )

        hits = manager.make_advanced_search(index=index, dsl_query=dsl_query)

        output_message = "Successfully executed search in Stellar Cyber Starlight."
        siemplify.result.add_result_json([hit.to_json() for hit in hits])
        result_value = True

    except SearchExecutionException as e:
        output_message = f"Action wasn't able to execute search in Stellar Cyber Starlight. Reasons: {e}"

    except Exception as e:
        output_message = f'Error executing action "Advanced Search". Reason: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
