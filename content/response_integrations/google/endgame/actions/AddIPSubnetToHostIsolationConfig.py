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
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.EndgameManager import EndgameManager
from TIPCommon import extract_configuration_param, extract_action_param

INTEGRATION_NAME = "Endgame"
SCRIPT_NAME = "Add IP Subnet to Host Isolation Config"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    ip_subnet = extract_action_param(
        siemplify,
        param_name="IP Subnet",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    is_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    output_message = ""
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    try:
        endgame_manager = EndgameManager(api_root, username, password, verify_ssl)
        endgame_manager.add_ip_subnet_to_isolation_config(
            subnet=ip_subnet, comment=description
        )

        if is_insight:
            siemplify.create_case_insight(
                triggered_by=INTEGRATION_NAME,
                title=ip_subnet,
                content=f"IP Subnet {ip_subnet} was added to the Host Isolation Config",
                entity_identifier="",
                severity=InsightSeverity.INFO,
                insight_type=InsightType.General,
            )

        output_message = "Successfully added IP subnet to Endgame Host Isolation Config"

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to add IP subnet to Endgame Host Isolation Config Error is {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Failed to add IP subnet to Endgame Host Isolation Config Error is {e}"
        )

    finally:
        try:
            endgame_manager.logout()
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
