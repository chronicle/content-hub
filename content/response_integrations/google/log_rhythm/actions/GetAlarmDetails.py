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
from ..core.LogRhythmManager import LogRhythmRESTManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    GET_ALARM_DETAILS_SCRIPT_NAME,
    ALARM_EVENT_TABLE_NAME,
)
from ..core.utils import string_to_multi_value, validate_positive_integer


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ALARM_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    alarm_ids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Alarm IDs", print_value=True)
    )
    max_events_to_etch = extract_action_param(
        siemplify,
        param_name="Max Events To Fetch",
        default_value=50,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_ids, failed_ids, csv_output, json_results = [], [], [], []

    try:
        validate_positive_integer(
            max_events_to_etch,
            err_msg="'Max Events To Fetch' parameter should be positive " "number.",
        )
        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        for id in alarm_ids:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                siemplify.LOGGER.info(f"Started processing alarm: {id}")
                alarm_details = manager.get_alarm_details(alarm_id=id)
                if not alarm_details:
                    failed_ids.append(id)
                    continue
                alarm_events = manager.get_alarm_events(
                    alarm_id=id, limit=max_events_to_etch
                )
                successful_ids.append(id)
                csv_output = [alarm_event.to_csv() for alarm_event in alarm_events]
                if csv_output:
                    siemplify.result.add_data_table(
                        ALARM_EVENT_TABLE_NAME.format(id=id), construct_csv(csv_output)
                    )

                alarm_drilldown = None
                try:
                    alarm_drilldown = manager.get_alarm_drilldown(alarm_id=id)
                    if not alarm_drilldown.as_json():
                        siemplify.LOGGER.info(
                            f"Alert drilldown data for alarm with id {id} was not found"
                        )
                except Exception as alarm_drilldown_error:
                    siemplify.LOGGER.error(
                        f"Failed to get alarm drilldown data for alarm with id {id}: "
                        f"{alarm_drilldown_error}"
                    )

                json_results.append(
                    alarm_details.to_json(alarm_events, alarm_drilldown)
                )
                siemplify.LOGGER.info(f"Finished processing alarm {id}")
            except Exception as e:
                failed_ids.append(id)
                siemplify.LOGGER.error(f"An error occurred on alarm {id}")
                siemplify.LOGGER.exception(e)

        if successful_ids:
            output_message = (
                f"Successfully retrieved details for the following alarms in "
                f"{INTEGRATION_NAME}:\n {', '.join(successful_ids)}\n"
            )
            siemplify.result.add_result_json(json_results)
            if failed_ids:
                output_message += (
                    f"The following alarms were not found in {INTEGRATION_NAME}: "
                    f"\n {', '.join(failed_ids)} \n"
                )
        else:
            output_message = (
                f"None of the provided alarms were found in {INTEGRATION_NAME}. \n"
            )
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {GET_ALARM_DETAILS_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"is_success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
