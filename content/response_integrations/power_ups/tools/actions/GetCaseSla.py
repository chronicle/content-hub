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

import dataclasses
import datetime
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
PAUSED_STATUS_LABEL = "Paused"
PAUSED_STATUS_KEY = "paused"
NO_SLA_STATUS_LABEL = "NoSla"
NO_SLA_STATUS_KEYS = frozenset({"nosla", "no_sla"})
LEGACY_NO_SLA_STATUS = 2
MS_PER_SECOND = 1000


@dataclasses.dataclass(frozen=True, slots=True)
class _CaseSlaDetails:
    sla_expiration: int | None
    critical_expiration: int | None
    expiration_status: str | int | None
    remaining_time_ms: int | None
    is_paused: bool


def _extract_valid_timestamp(*candidates: float | str | None, min_value: int = 1) -> int | None:
    """Return the first numeric candidate meeting min_value."""
    for candidate in candidates:
        if isinstance(candidate, bool) or candidate is None or candidate == "":
            continue
        try:
            timestamp = int(float(candidate))
        except (ValueError, TypeError, OverflowError):
            continue
        if timestamp >= min_value:
            return timestamp
    return None


def _extract_expiration_status(sla_obj: SingleJson) -> str | int | None:
    """Return a normalized SLA expiration status, or None when unset."""
    status = sla_obj.get("expirationStatus")
    if isinstance(status, bool) or status is None:
        return None
    if isinstance(status, str):
        return status.strip() or None
    if isinstance(status, int) and status >= 0:
        return status
    return None


def _extract_remaining_time_ms(sla_obj: SingleJson, *, min_value: int = 1) -> int | None:
    """Return remaining SLA time in milliseconds since the last pause."""
    return _extract_valid_timestamp(
        sla_obj.get("remainingTimeSinceLastPause"),
        sla_obj.get("lastPauseRemainingTimeMs"),
        min_value=min_value,
    )


def _is_paused_sla(sla_obj: SingleJson) -> bool:
    """Return True when an SLA object indicates a paused SLA timer."""
    status = _extract_expiration_status(sla_obj)
    if isinstance(status, str):
        normalized = status.lower()
        if normalized == PAUSED_STATUS_KEY:
            return True
        if normalized in NO_SLA_STATUS_KEYS:
            return False
    elif status == LEGACY_NO_SLA_STATUS:
        return False
    return _extract_remaining_time_ms(sla_obj) is not None


def _extract_case_sla_details(case_data: SingleJson) -> _CaseSlaDetails:
    """Extract SLA timestamps, pause state, and status metadata from case overview data."""
    sla_data: SingleJson = case_data.get("sla") or {}
    stage_sla_data: SingleJson = case_data.get("stageSla") or {}
    case_critical_sla = _extract_valid_timestamp(
        sla_data.get("criticalExpirationTime"),
        stage_sla_data.get("criticalExpirationTime"),
        case_data.get("slaCriticalExpirationUnixTime"),
        case_data.get("stageSlaCriticalExpirationUnixTimeInMs"),
    )

    for source_sla in (sla_data, stage_sla_data):
        active_sla = _extract_valid_timestamp(
            source_sla.get("expirationTime"),
            source_sla.get("slaExpirationTime"),
        )
        if active_sla is not None:
            return _CaseSlaDetails(
                sla_expiration=active_sla,
                critical_expiration=case_critical_sla,
                expiration_status=_extract_expiration_status(source_sla),
                remaining_time_ms=_extract_remaining_time_ms(source_sla),
                is_paused=False,
            )

    legacy_sla = _extract_valid_timestamp(
        case_data.get("slaExpirationUnixTime"),
        case_data.get("stageSlaExpirationUnixTimeInMs"),
    )
    if legacy_sla is not None:
        return _CaseSlaDetails(
            sla_expiration=legacy_sla,
            critical_expiration=case_critical_sla,
            expiration_status=None,
            remaining_time_ms=None,
            is_paused=False,
        )

    for candidate_sla in (sla_data, stage_sla_data):
        if _is_paused_sla(candidate_sla):
            return _CaseSlaDetails(
                sla_expiration=None,
                critical_expiration=None,
                expiration_status=PAUSED_STATUS_LABEL,
                remaining_time_ms=_extract_remaining_time_ms(candidate_sla, min_value=0),
                is_paused=True,
            )

    return _CaseSlaDetails(
        sla_expiration=None,
        critical_expiration=None,
        expiration_status=NO_SLA_STATUS_LABEL,
        remaining_time_ms=None,
        is_paused=False,
    )


def _format_duration_ms(duration_ms: int) -> str:
    """Format a non-negative millisecond duration as a human-readable string."""
    total_seconds = duration_ms // MS_PER_SECOND
    if total_seconds == 0 and duration_ms > 0:
        return f"{duration_ms} ms"
    return str(datetime.timedelta(seconds=total_seconds))


def _build_sla_result(sla_details: _CaseSlaDetails, dt_format: str) -> SingleJson:
    """Format extracted case SLA details into the action JSON result payload."""
    dt_case_sla = (
        convert_unixtime_to_datetime(sla_details.sla_expiration).strftime(dt_format)
        if sla_details.sla_expiration is not None
        else None
    )
    dt_case_critical_sla = (
        convert_unixtime_to_datetime(sla_details.critical_expiration).strftime(dt_format)
        if sla_details.critical_expiration is not None
        else None
    )
    remaining_formatted = (
        _format_duration_ms(sla_details.remaining_time_ms) if sla_details.remaining_time_ms is not None else None
    )
    return {
        "SLA_unix": sla_details.sla_expiration,
        "SLA": dt_case_sla,
        "critical_SLA_unix": sla_details.critical_expiration,
        "critical_SLA": dt_case_critical_sla,
        "expiration_status": sla_details.expiration_status,
        "remaining_time_since_last_pause_ms": sla_details.remaining_time_ms,
        "remaining_time_since_last_pause": remaining_formatted,
    }


def _format_output_message(
    case_id: str | int,
    sla_details: _CaseSlaDetails,
    json_result: SingleJson,
) -> str:
    """Build the output message for an active, paused, or unset case SLA."""
    if sla_details.is_paused:
        if json_result["remaining_time_since_last_pause"] is not None:
            return (
                f"SLA is paused for case {case_id}. "
                f"Remaining time since last pause: {json_result['remaining_time_since_last_pause']}."
            )
        return f"SLA is paused for case {case_id}."
    if sla_details.sla_expiration is None:
        return f"SLA was not set for case {case_id}."
    return f"Stage SLA: {json_result['SLA']}, Critical Stage SLA: {json_result['critical_SLA']}"


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
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        response = get_case_overview_details(
            chronicle_soar=siemplify,
            case_id=siemplify.case_id,
            case_expand=CASE_EXPAND_FIELDS,
        )
        sla_details = _extract_case_sla_details(response.to_json())
        json_result = _build_sla_result(sla_details, dt_format)
        siemplify.result.add_result_json(json_result)
        result_value = sla_details.sla_expiration is not None or sla_details.is_paused
        output_message = _format_output_message(siemplify.case_id, sla_details, json_result)
        siemplify.LOGGER.info(output_message)

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
