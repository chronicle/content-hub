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
from soar_sdk.SiemplifyUtils import output_handler, utc_now, convert_datetime_to_unix_time
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.EndgameManager import EndgameManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
import datetime

INTEGRATION_NAME = "Endgame"
SCRIPT_NAME = "List Investigations"
DEFAULT_OS = "Solaris, Windows, MacOs, Linux"


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

    os_filters = extract_action_param(
        siemplify,
        param_name="OS",
        is_mandatory=False,
        input_type=str,
        print_value=True,
        default_value=DEFAULT_OS,
    )
    max_hours_backwards = extract_action_param(
        siemplify,
        param_name="Fetch investigations for the last X hours",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )
    results_limit = extract_action_param(
        siemplify,
        param_name="Max Investigation to Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    os_filters = (
        [os_filter.strip() for os_filter in os_filters.split(",")] if os_filters else []
    )
    created_from = None

    if max_hours_backwards:
        created_from = convert_datetime_to_unix_time(
            utc_now() - datetime.timedelta(hours=max_hours_backwards)
        )
        siemplify.LOGGER.info(f"Setting create_from filter to {created_from}")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = {}
    output_message = ""
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    try:
        endgame_manager = EndgameManager(api_root, username, password, verify_ssl)
        investigations = endgame_manager.get_investigations(
            os_filters=os_filters, created_from=created_from, limit=results_limit
        )

        if investigations:
            siemplify.result.add_data_table(
                "Endgame Investigation List",
                construct_csv(
                    [investigation.as_csv() for investigation in investigations]
                ),
            )
            json_results = [investigation.raw_data for investigation in investigations]
            output_message = "Successfully listed Endgame Investigations."
        else:
            output_message = "There are no investigations right now"

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to get Endgame Investigations! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to get Endgame Investigations! Error is {e}"

    finally:
        try:
            endgame_manager.logout()
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
