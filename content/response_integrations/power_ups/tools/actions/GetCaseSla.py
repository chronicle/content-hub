# Copyright 2025 Google LLC
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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler
from TIPCommon.rest.soar_api import get_case_overview_details

ACTION_NAME = "Get Case SLA"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    siemplify.LOGGER.info("----------------- Main - Param init -----------------")
    dt_format = siemplify.extract_action_param(
        "DateTime Format",
        default_value=DATETIME_FORMAT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        response = get_case_overview_details(
            chronicle_soar=siemplify,
            case_id=siemplify.case_id,
        )
        case_data = response.to_json()

        case_sla = int(
            case_data.get("sla", {}).get("slaExpirationTime") or case_data.get("stageSla", {}).get("slaExpirationTime")
        )
        dt_case_sla = convert_unixtime_to_datetime(case_sla).strftime(dt_format)
        siemplify.LOGGER.info(f"stage SLA: {dt_case_sla}")

        case_critical_sla = int(
            case_data.get("sla", {}).get("criticalExpirationTime")
            or case_data.get("stageSla", {}).get("criticalExpirationTime")
        )
        dt_case_critical_sla = convert_unixtime_to_datetime(case_critical_sla).strftime(
            dt_format,
        )
        siemplify.LOGGER.info(f"critical stage SLA: {dt_case_critical_sla}")

        json_result = {
            "SLA_unix": case_sla,
            "SLA": dt_case_sla,
            "critical_SLA_unix": case_critical_sla,
            "critical_SLA": dt_case_critical_sla,
        }
        siemplify.result.add_result_json(json_result)
        output_message = f"Stage SLA: {dt_case_sla}, Criticasl Stage SLA: {dt_case_critical_sla}"

    except Exception as e:
        error_msg = f"SLA was not set for case {siemplify.case_id}" if isinstance(e, TypeError) else str(e)
        output_message = f"Error executing action {ACTION_NAME}. Reason: {error_msg}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
