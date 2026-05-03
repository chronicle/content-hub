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
from soar_sdk.SiemplifyJob import SiemplifyJob
from ..core.LogRhythmManager import LogRhythmRESTManager
from soar_sdk.SiemplifyUtils import utc_now, convert_datetime_to_unix_time
from ..core.constants import (
    SYNC_CLOSED_CASES_SCRIPT_NAME,
    DEFAULT_DEVICE_PRODUCT,
    CASE_STATUS_OPEN,
    LOGRHYTHM_COMPLETED_STATUS,
    LOGRHYTHM_RESOLVED_STATUS,
    CASE_STATUS_MAPPING,
    ROOT_CAUSE,
    REASON,
    COMMENT,
)
from TIPCommon import validate_timestamp
from ..core.exceptions import LogRhythmManagerBadRequestError


def get_alert_and_case_ids(case, logrhythm_case_id):
    for alert in case.get("cyber_alerts", {}):
        if logrhythm_case_id in [
            alert.get("external_id"),
            alert.get("additional_data"),
        ]:
            return case.get("identifier"), alert.get("identifier")


@output_handler
def main():
    siemplify = SiemplifyJob()

    try:
        siemplify.script_name = SYNC_CLOSED_CASES_SCRIPT_NAME

        api_root = siemplify.extract_job_param(param_name="Api Root", is_mandatory=True)
        api_token = siemplify.extract_job_param(
            param_name="Api Token", is_mandatory=True
        )
        verify_ssl = siemplify.extract_job_param(
            param_name="Verify SSL", is_mandatory=True, input_type=bool
        )
        hours_backwards = siemplify.extract_job_param(
            param_name="Max Hours Backwards", input_type=int, default_value=24
        )
        siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        last_successful_execution_time = siemplify.fetch_timestamp(datetime_format=True)
        last_successful_execution_time = validate_timestamp(
            last_successful_execution_time, hours_backwards
        )
        siemplify.LOGGER.info(
            f"Last successful execution run: {last_successful_execution_time}"
        )

        new_timestamp = utc_now()

        ticket_ids_for_closed_cases = (
            siemplify.get_alerts_ticket_ids_from_cases_closed_since_timestamp(
                convert_datetime_to_unix_time(last_successful_execution_time), None
            )
        )
        filtered_closed_cases = []
        open_cases = []
        for ticket_id in ticket_ids_for_closed_cases:
            try:
                cases_ids = siemplify.get_cases_by_filter(
                    ticked_ids_free_search=ticket_id,
                    case_names=[DEFAULT_DEVICE_PRODUCT],
                )
                filtered_closed_cases.extend(
                    [siemplify._get_case_by_id(case_id) for case_id in cases_ids]
                )
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to fetch case with ticket id {ticket_id}. Reason {e}"
                )

        siemplify.LOGGER.info(
            f"Found {len(filtered_closed_cases)} closed cases to process"
        )

        siemplify.LOGGER.info("--- Start Closing cases in LogRhythm ---")
        logrhythm_events_ids = []
        for case in filtered_closed_cases:
            for alert in case.get("cyber_alerts", []):
                logrhythm_case_id = None
                if alert.get("reporting_product") == DEFAULT_DEVICE_PRODUCT:
                    if alert.get("additional_properties", {}).get("number") is not None:
                        logrhythm_case_id = alert.get("additional_properties", {}).get(
                            "TicketId"
                        )
                else:
                    logrhythm_case_id = alert.get("additional_data")
                if logrhythm_case_id:
                    try:
                        logrhythm_case = manager.get_case_status(
                            case_id=logrhythm_case_id
                        )
                        if logrhythm_case:
                            if CASE_STATUS_MAPPING.get(logrhythm_case.status) not in [
                                LOGRHYTHM_COMPLETED_STATUS,
                                LOGRHYTHM_RESOLVED_STATUS,
                            ]:
                                logrhythm_events_ids.append(logrhythm_case_id)
                            else:
                                siemplify.LOGGER.info(
                                    f"Case with id {logrhythm_case_id} is already have "
                                    f"{logrhythm_case.status} status in LogRhythm"
                                )
                    except Exception as e:
                        siemplify.LOGGER.error(
                            f"Failed to get details for case {logrhythm_case_id}."
                        )
                else:
                    siemplify.LOGGER.error(
                        f'Can not get case id from case {case.get("identifier")}.'
                    )
        if logrhythm_events_ids:
            for case_id in logrhythm_events_ids:
                try:
                    manager.close_case(case_id=case_id)
                    siemplify.LOGGER.info(f"LogRhythm case {case_id} was closed.")
                except LogRhythmManagerBadRequestError as err:
                    siemplify.LOGGER.info(
                        "Can't change the status to completed, changing it to resolved."
                    )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to close case {case_id} in LogRhythm. Reason: {e}"
                    )

        siemplify.LOGGER.info(
            "--- Finished synchronizing closed cases from "
            "Siemplify to LogRhythm cases ---"
        )
        cases_id = siemplify.get_cases_by_filter(
            case_names=[DEFAULT_DEVICE_PRODUCT], statuses=[CASE_STATUS_OPEN]
        )
        for case_id in cases_id:
            case = siemplify._get_case_by_id(case_id)
            open_cases.append(case)

        siemplify.LOGGER.info(f"Found {len(open_cases)} open cases to process")

        siemplify.LOGGER.info("--- Start Closing Alerts in Siemplify ---")

        for case in open_cases:
            for alert in case.get("cyber_alerts", []):
                logrhythm_case_id = None
                if alert.get("reporting_product") == DEFAULT_DEVICE_PRODUCT:
                    if alert.get("additional_properties", {}).get("number") is not None:
                        logrhythm_case_id = alert.get("additional_properties", {}).get(
                            "TicketId"
                        )
                else:
                    logrhythm_case_id = alert.get("additional_data")
                if logrhythm_case_id:
                    try:
                        logrhythm_case = manager.get_case_status(
                            case_id=logrhythm_case_id
                        )
                        if logrhythm_case:
                            if CASE_STATUS_MAPPING.get(logrhythm_case.status) in [
                                LOGRHYTHM_COMPLETED_STATUS,
                                LOGRHYTHM_RESOLVED_STATUS,
                            ]:
                                case_id, alert_id = get_alert_and_case_ids(
                                    case, logrhythm_case_id
                                )
                                siemplify.close_alert(
                                    root_cause=ROOT_CAUSE,
                                    reason=REASON,
                                    comment=COMMENT.format(logrhythm_case.status),
                                    case_id=case_id,
                                    alert_id=alert_id,
                                )

                                siemplify.LOGGER.info(
                                    f"Alert with case id {logrhythm_case_id} was closed"
                                )
                            else:
                                siemplify.LOGGER.info(
                                    f"Case with id {logrhythm_case_id} "
                                    f"is not close in LogRhythm"
                                )
                    except Exception as e:
                        siemplify.LOGGER.error(
                            f"Failed to get details for case {logrhythm_case_id}."
                        )
        siemplify.save_timestamp(new_timestamp=new_timestamp)
        siemplify.LOGGER.info(
            " --- Finished synchronizing closed cases from "
            "LogRhythm to Siemplify alerts --- "
        )
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
