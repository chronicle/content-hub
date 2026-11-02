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
import sys
import uuid

from EnvironmentCommon import GetEnvironmentCommonFactory

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_unixtime_to_datetime,
    convert_string_to_unix_time,
    unix_now,
)

from TIPCommon.extraction import extract_connector_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.utils import is_overflowed

from crowd_strike_falcon.core.constants import (
    ADDITIONAL_TYPES_MAPPING,
    API_ROOT_DEFAULT,
    EVENT_STREAMING_CONNECTOR_NAME,
    SIEMPLIFY_PREFIX_FOR_APP,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import CrowdStrikeStreamError
from crowd_strike_falcon.core.utils import (
    get_formatted_last_success_time,
    get_offset,
    store_offset,
    is_approaching_timeout,
)


DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
connector_starting_time = unix_now()


@output_handler
def main(is_test_run: bool) -> None:
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = EVENT_STREAMING_CONNECTOR_NAME
    processed_alerts, all_alerts = [], []

    if is_test_run:
        siemplify.LOGGER.info(
            "***** This is an 'IDE Play Button' 'Run Connector once' test run ******"
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    environment = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )
    environment_regex = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )

    api_root = extract_connector_param(
        siemplify,
        param_name="API Root",
        print_value=True,
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=True
    )
    customer_id = extract_connector_param(
        siemplify, param_name="Customer ID", print_value=True
    )
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret", is_mandatory=True
    )

    event_types = string_to_multi_value(
        extract_connector_param(siemplify, param_name="Event types", print_value=True)
    )

    limit = extract_connector_param(
        siemplify,
        param_name="Max Events per Cycle",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    limit = 1 if is_test_run else limit

    max_days_backwards = extract_connector_param(
        siemplify, param_name="Max Day Backwards", input_type=int, print_value=True
    )
    min_severity = extract_connector_param(
        siemplify, param_name="Min Severity", input_type=int, print_value=True
    )

    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", input_type=bool, print_value=True
    )
    disable_overflow = extract_connector_param(
        siemplify,
        param_name="Disable Overflow",
        input_type=bool,
        default_value=False,
        print_value=True
    )
    app_name = f"{SIEMPLIFY_PREFIX_FOR_APP}{str(uuid.uuid4()).replace('-', '')}"[:30]

    alert_name_template = extract_connector_param(
        siemplify, param_name="Alert Name Template", print_value=True
    )
    rule_generator_template = extract_connector_param(
        siemplify, param_name="Rule Generator Template", print_value=True
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    if not event_types:
        siemplify.LOGGER.info(
            '"Event types" parameter were not provided. All event types will be ingested'
        )
    else:
        _event_types = []
        for event_type in event_types:
            if event_type in ADDITIONAL_TYPES_MAPPING:
                event_type = ADDITIONAL_TYPES_MAPPING[event_type]

                if isinstance(event_types, list):
                    _event_types.extend(event_type)
                    continue

            _event_types.append(event_type)

        event_types = _event_types

    try:
        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify, environment, environment_regex
        )

        last_success_time = get_formatted_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"days": max_days_backwards},
            date_time_format=DATETIME_FORMAT,
        )

        offset = 0 if is_test_run else get_offset(siemplify)
        siemplify.LOGGER.info(f"Current offset is {offset}")

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=verify_ssl,
            api_root=api_root,
            logger=siemplify.LOGGER,
            customer_id=customer_id,
        )
        detections_generator = manager.get_stream_detections(
            app_name=app_name,
            offset=offset,
            event_types=event_types,
        )

        for detection in detections_generator:
            try:
                if is_approaching_timeout(
                    python_process_timeout, connector_starting_time
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if detection is None:
                    siemplify.LOGGER.info(
                        "Received a heartbeat from a stream, waiting for detections ..."
                    )
                    continue

                all_alerts.append(detection)
                if event_types and detection.event_type not in event_types:
                    continue

                siemplify.LOGGER.info(
                    f"Starting detection with offset: {detection.offset} and event type: "
                    f"{detection.event_type}"
                )

                if (
                    min_severity
                    and detection.is_detection
                    and detection.severity < min_severity
                ):
                    siemplify.LOGGER.info(
                        f"Skipping detection with severity {detection.severity} which is less "
                        f"than {min_severity}"
                    )
                    continue

                siemplify.LOGGER.info(
                    f"Create Time: {convert_unixtime_to_datetime(detection.event_creation_time).isoformat()}"
                )

                if last_success_time and not detection.has_creation_time_newer_than(
                    convert_string_to_unix_time(last_success_time)
                ):
                    siemplify.LOGGER.info(
                        f"Skipping detection with event creation time {detection.event_creation_time} "
                        f"which is older than minimum event creation time {last_success_time} "
                        f"calculated with max days backwards {max_days_backwards}"
                    )
                    continue

                if detection.is_api_stream_action(client_id, SIEMPLIFY_PREFIX_FOR_APP):
                    siemplify.LOGGER.info(
                        f"Skipping detection with offset {detection.offset} made by stream "
                        f"connector with App ID {app_name}"
                    )
                    continue

                siemplify.LOGGER.info(
                    f"Processing detection with offset {detection.offset}"
                )
                alert_info = detection.get_alert_info(
                    environment_common, alert_name_template, rule_generator_template
                )

                if (
                        not disable_overflow
                        and is_overflowed(siemplify, alert_info, is_test_run)
                ):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-"
                        f"{alert_info.environment}-{alert_info.device_product} "
                        "found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(
                    f"Detection with offset {detection.offset} was created."
                )

                if len(processed_alerts) >= limit:
                    siemplify.LOGGER.info(
                        "Reached maximum amount of detection's to process."
                    )
                    break

            except Exception as error:
                siemplify.LOGGER.error(
                    f"Failed to process detection with offset {detection.offset}"
                )
                siemplify.LOGGER.exception(error)

                if is_test_run:
                    raise

    except CrowdStrikeStreamError as error:
        siemplify.LOGGER.info(error)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    if not is_test_run and all_alerts:
        last_offset = sorted(all_alerts, key=lambda det: det.offset)[-1].offset
        # increment offset to avoid duplication
        offset_to_store = last_offset + 1
        store_offset(siemplify, offset_to_store)

        siemplify.LOGGER.info(f"New offset {offset_to_store} stored")

    siemplify.LOGGER.info(
        f"Detections processed: {len(processed_alerts)} of {len(all_alerts)}"
    )
    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
