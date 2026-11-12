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

from typing import TYPE_CHECKING

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler
from TIPCommon.exceptions import InternalJSONDecoderError
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import get_case_overview_details

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

ACTION_NAME = "Get Case SLA"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CASE_EXPAND_FIELDS: list[str] = ["sla"]


def _extract_valid_timestamp(*candidates: int | str | None) -> int | None:
    """Return the first positive Unix timestamp from the provided candidates."""
    for candidate in candidates:
        if isinstance(candidate, bool) or candidate in (None, ""):
            continue
        timestamp = int(candidate)
        if timestamp > 0:
            return timestamp
    return None


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    siemplify.LOGGER.info("----------------- Main - Param init -----------------")
    dt_format: str = extract_action_param(
        siemplify,
        param_name="DateTime Format",
        default_value=DATETIME_FORMAT,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        response = get_case_overview_details(
            chronicle_soar=siemplify,
            case_id=siemplify.case_id,
            case_expand=CASE_EXPAND_FIELDS,
        )
        case_data: SingleJson = response.to_json()
        sla_data: SingleJson = case_data.get("sla") or {}
        stage_sla_data: SingleJson = case_data.get("stageSla") or {}

        case_sla = _extract_valid_timestamp(
            sla_data.get("slaExpirationTime"),
            stage_sla_data.get("slaExpirationTime"),
            case_data.get("slaExpirationUnixTime"),
            case_data.get("stageSlaExpirationUnixTimeInMs"),
        )
        case_critical_sla = _extract_valid_timestamp(
            sla_data.get("criticalExpirationTime"),
            stage_sla_data.get("criticalExpirationTime"),
            case_data.get("slaCriticalExpirationUnixTime"),
            case_data.get("stageSlaCriticalExpirationUnixTimeInMs"),
        )

        if case_sla is None:
            result_value = False
            output_message = f"SLA was not set for case {siemplify.case_id}."
            siemplify.LOGGER.info(output_message)
        else:
            dt_case_sla = convert_unixtime_to_datetime(case_sla).strftime(dt_format)
            siemplify.LOGGER.info(f"stage SLA: {dt_case_sla}")

            dt_case_critical_sla = (
                convert_unixtime_to_datetime(case_critical_sla).strftime(dt_format)
                if case_critical_sla is not None
                else None
            )
            siemplify.LOGGER.info(f"critical stage SLA: {dt_case_critical_sla}")

            json_result: SingleJson = {
                "SLA_unix": case_sla,
                "SLA": dt_case_sla,
                "critical_SLA_unix": case_critical_sla,
                "critical_SLA": dt_case_critical_sla,
            }
            siemplify.result.add_result_json(json_result)
            output_message = f"Stage SLA: {dt_case_sla}, Critical Stage SLA: {dt_case_critical_sla}"

    except (
        requests.RequestException,
        InternalJSONDecoderError,
        ValueError,
        TypeError,
        KeyError,
    ) as e:
        output_message = f'Error executing action "{ACTION_NAME}". Reason: {e}'
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
