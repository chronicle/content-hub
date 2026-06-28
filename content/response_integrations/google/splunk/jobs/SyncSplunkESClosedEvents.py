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
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from soar_sdk.SiemplifyUtils import output_handler
from splunk.core.SplunkManager import SplunkManager
from TIPCommon.extraction import extract_action_param
from splunk.core.UtilsManager import validate_timestamp
from splunk.core.constants import (
    SYNC_CLOSURE_SCRIPT_NAME,
    DEFAULT_DEVICE_PRODUCT,
    CASE_STATUS_CLOSED,
    CASE_STATUS_OPEN,
    SPLUNK_CLOSED_STATUS,
    SPLUNK_RESOLVED_STATUS,
    ROOT_CAUSE,
    REASON,
    COMMENT,
    SPLUNK_EVENT_TYPE,
)


def get_alert_and_case_ids(case, event_id):
    for alert in case.get("cyber_alerts", {}):
        if event_id in [alert.get("external_id"), alert.get("additional_data")]:
            return case.get("identifier"), alert.get("identifier")


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SYNC_CLOSURE_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

    server_address = extract_action_param(
        siemplify=siemplify,
        param_name="Server Address",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_action_param(
        siemplify=siemplify, param_name="Username", print_value=False
    )

    password = extract_action_param(
        siemplify=siemplify, param_name="Password", print_value=False
    )

    ca_certificate = extract_action_param(
        siemplify=siemplify, param_name="CA Certificate File", print_value=False
    )
    verify_ssl = extract_action_param(
        siemplify=siemplify, input_type=bool, param_name="Verify SSL"
    )
    api_token = extract_action_param(
        siemplify=siemplify, param_name="API Token", print_value=False
    )

    hours_backwards = extract_action_param(
        siemplify=siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        print_value=True,
    )

    # Get last Successful execution time.
    last_successful_execution_time = siemplify.fetch_timestamp(datetime_format=True)
    last_successful_execution_time = validate_timestamp(
        last_successful_execution_time, hours_backwards
    )
    siemplify.LOGGER.info(
        f"Last successful execution run: {last_successful_execution_time}"
    )

    try:
        closed_cases = []
        open_cases = []

        manager = SplunkManager(
            server_address=server_address,
            username=username,
            password=password,
            api_token=api_token,
            ca_certificate=ca_certificate,
            siemplify_logger=siemplify.LOGGER,
            verify_ssl=verify_ssl,
        )

        cases_id = {
            "by_event_type": siemplify.get_cases_by_filter(
                statuses=[CASE_STATUS_CLOSED],
                start_time_unix_time_in_ms=convert_datetime_to_unix_time(
                    last_successful_execution_time
                ),
            ),
            "by_device_product": siemplify.get_cases_by_filter(
                products=[DEFAULT_DEVICE_PRODUCT],
                statuses=[CASE_STATUS_CLOSED],
                start_time_unix_time_in_ms=convert_datetime_to_unix_time(
                    last_successful_execution_time
                ),
            ),
        }

        for case_id in list(
            set(cases_id["by_event_type"] + cases_id["by_device_product"])
        ):
            case = siemplify._get_case_by_id(case_id)

            if case_id in cases_id["by_device_product"] or [
                alert
                for alert in case.get("cyber_alerts", [])
                if alert.get("additional_properties", {}).get("splunk_event_type")
                == SPLUNK_EVENT_TYPE
            ]:
                closed_cases.append(case)

        siemplify.LOGGER.info(f"Found {len(closed_cases)} closed cases to process")

        siemplify.LOGGER.info("--- Start Closing Issues in Splunk ---")

        splunk_events_to_close = []
        splunk_events_ids = []

        for case in closed_cases:
            for alert in case.get("cyber_alerts", []):
                event_id = (
                    alert.get("additional_data")
                    if alert.get("reporting_product") != DEFAULT_DEVICE_PRODUCT
                    else alert.get("additional_properties", {}).get("TicketId")
                )

                if event_id:
                    try:
                        events = manager.get_events_by_filter(event_ids=[event_id])
                        if events:
                            if events[0].status not in [
                                SPLUNK_CLOSED_STATUS,
                                SPLUNK_RESOLVED_STATUS,
                            ]:
                                splunk_events_ids.append(event_id)
                                splunk_events_to_close.append(events[0])
                    except Exception as e:
                        siemplify.LOGGER.error(
                            f"Failed to get details for event {event_id}."
                        )

        if splunk_events_ids:
            try:
                manager.close_events(splunk_events_ids)
                siemplify.LOGGER.info(
                    "Following Splunk events were closed: {}".format(
                        "\n".join([event for event in splunk_events_ids])
                    )
                )
            except Exception as e:
                siemplify.LOGGER.error(
                    "Failed to close following events in "
                    "Splunk: {}. \nReason: {}".format(
                        "\n".join([event for event in splunk_events_ids]), e
                    )
                )

        siemplify.LOGGER.info(
            "--- Finished synchronizing closed events from "
            "Siemplify to Splunk events ---"
        )

        cases_id = {
            "by_event_type": siemplify.get_cases_by_filter(statuses=[CASE_STATUS_OPEN]),
            "by_device_product": siemplify.get_cases_by_filter(
                products=[DEFAULT_DEVICE_PRODUCT], statuses=[CASE_STATUS_OPEN]
            ),
        }

        for case_id in list(
            set(cases_id["by_event_type"] + cases_id["by_device_product"])
        ):
            case = siemplify._get_case_by_id(case_id)

            if case_id in cases_id["by_device_product"] or [
                alert
                for alert in case.get("cyber_alerts", [])
                if alert.get("additional_properties", {}).get("splunk_event_type")
                == SPLUNK_EVENT_TYPE
            ]:
                open_cases.append(case)

        siemplify.LOGGER.info(f"Found {len(open_cases)} open cases to process")

        siemplify.LOGGER.info("--- Start Closing Alerts in Siemplify ---")

        for case in open_cases:
            for alert in case.get("cyber_alerts", []):
                event_id = (
                    alert.get("additional_data")
                    if alert.get("reporting_product") != DEFAULT_DEVICE_PRODUCT
                    else alert.get("additional_properties", {}).get("TicketId")
                )

                if event_id:
                    try:
                        events = manager.get_events_by_filter(event_ids=[event_id])
                        if events:
                            if events[0].status in [
                                SPLUNK_CLOSED_STATUS,
                                SPLUNK_RESOLVED_STATUS,
                            ]:
                                case_id, alert_id = get_alert_and_case_ids(
                                    case, event_id
                                )
                                siemplify.close_alert(
                                    root_cause=ROOT_CAUSE,
                                    reason=REASON,
                                    comment=COMMENT,
                                    case_id=case_id,
                                    alert_id=alert_id,
                                )

                                siemplify.LOGGER.info(
                                    f"Alert with event id {event_id} was closed"
                                )
                    except Exception as e:
                        siemplify.LOGGER.error(
                            f"Failed to get details for event {event_id}."
                        )

        if splunk_events_ids:
            # Update last successful run time with new_timestamp.
            new_timestamp = sorted(splunk_events_to_close, key=lambda ev: ev.timestamp)[
                -1
            ].timestamp
            siemplify.save_timestamp(new_timestamp=int(new_timestamp))
            siemplify.LOGGER.info("Update Job last execution timestamp")
        siemplify.LOGGER.info(
            " --- Finished synchronizing closed events from "
            "Splunk to Siemplify alerts --- "
        )
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
