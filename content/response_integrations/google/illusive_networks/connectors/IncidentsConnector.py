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

import os
import sys
import uuid

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_connector_param, validate_map_file

from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    RATE_LIMIT_ERROR_IDENTIFIER,
    TIMEOUT_THRESHOLD,
)
from ..core.IllusiveNetworksManager import IllusiveNetworksManager
from ..core.Utils import (
    filter_old_alerts,
    get_environment_common,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    pass_whitelist_filter,
    priority_text_to_value,
    read_ids,
    save_timestamp,
    write_ids,
)

MAP_FILE = "map.json"
INCIDENT_NAME = "Incident:{}"


@output_handler
def main(is_test_run):
    processed_incidents = []
    all_incidents = []
    existing_ids = []
    connector_starting_time = unix_now()
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            "***** This is an 'IDE Play Button' 'Run Connector once' test run ******"
        )

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        is_mandatory=False,
        print_value=True,
    )

    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        is_mandatory=False,
        print_value=True,
    )

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )

    api_key = extract_connector_param(
        siemplify, param_name="API Key", is_mandatory=True
    )

    alert_severity = extract_connector_param(
        siemplify, param_name="Alert Severity", print_value=True, is_mandatory=True
    )

    max_hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=1,
        print_value=True,
    )

    max_incidents_to_fetch = extract_connector_param(
        siemplify,
        param_name="Max Incidents To Fetch",
        input_type=int,
        default_value=10,
        print_value=True,
    )

    use_whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        input_type=bool,
        default_value=True,
        print_value=True,
    )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
        is_mandatory=True,
        print_value=True,
    )
    ca_certificate = extract_connector_param(
        siemplify, param_name="CA Certificate File"
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    map_file_path = os.path.join(siemplify.run_folder, MAP_FILE)
    validate_map_file(siemplify, map_file_path)

    try:
        severity_value = priority_text_to_value(alert_severity)
        environment_common = get_environment_common(
            siemplify, environment_field_name, environment_regex_pattern
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            date_time_format="%Y-%m-%dT%H:%M:%S.000Z",
            offset_with_metric={"hours": max_hours_backwards},
        )

        illusive_networks_manager = IllusiveNetworksManager(
            api_root=api_root,
            api_key=api_key,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")
        incidents = illusive_networks_manager.get_incidents(
            start_date=last_success_time
        )
        filtered_incidents = filter_old_alerts(
            siemplify.LOGGER, incidents, existing_ids, "incident_id"
        )

        siemplify.LOGGER.info(
            f"Alert to process after filtering already processed once "
            f"{len(filtered_incidents)} out of {len(incidents)} received from the API"
        )

        for incident in filtered_incidents:
            siemplify.LOGGER.info("\n")
            try:
                if is_approaching_timeout(
                    python_process_timeout, connector_starting_time, TIMEOUT_THRESHOLD
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if is_test_run and processed_incidents:
                    siemplify.LOGGER.info(
                        "Maximum incidents count (1) for test run reached!"
                    )
                    break
                if len(processed_incidents) >= max_incidents_to_fetch:
                    siemplify.LOGGER.info(
                        f"Maximum incidents count ({max_incidents_to_fetch}) "
                        f"reached! Stopping..."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Starting incident with id: {incident.incident_id}"
                )

                all_incidents.append(incident)

                if not pass_whitelist_filter(
                    siemplify, use_whitelist_as_a_blacklist, incident, "incident_types"
                ):
                    continue

                siemplify.LOGGER.info(
                    f"Processing incident with id: {incident.incident_id}"
                )
                incident.set_event(
                    illusive_networks_manager.get_incident_timeline(
                        incident_id=incident.incident_id
                    )
                )
                alert_info = create_alert_info(
                    siemplify, environment_common, incident, severity_value
                )
                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-"
                        f"{alert_info.environment}-{alert_info.device_product} "
                        f"found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
                    continue

                processed_incidents.append(alert_info)
                siemplify.LOGGER.info(
                    f"Incident with id {incident.incident_id} was created."
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process incident with id {incident.incident_id}"
                )
                siemplify.LOGGER.exception(e)
                if RATE_LIMIT_ERROR_IDENTIFIER in e:
                    siemplify.LOGGER.info(
                        "Stopping connector execution because of api error"
                    )
                    all_incidents.pop()
                    raise
                if is_test_run:
                    raise
            siemplify.LOGGER.info("\n")
    except Exception as e:
        siemplify.LOGGER.error(f"General error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    if not is_test_run and all_incidents:
        siemplify.LOGGER.info("Saving existing ids.")
        write_ids(
            siemplify,
            existing_ids + [incident.incident_id for incident in all_incidents],
        )
        save_timestamp(siemplify=siemplify, alerts=all_incidents)

    siemplify.LOGGER.info(
        f"Incidents processed: {len(processed_incidents)} out of {len(all_incidents)}"
    )
    siemplify.LOGGER.info(f"Created total of {len(processed_incidents)} alerts")

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_incidents)


def create_alert_info(siemplify, environment_common, incident, severity_value):
    siemplify.LOGGER.info(f"Creating alert info for incident {incident.incident_id}")

    alert_info = AlertInfo()
    alert_info.ticket_id = incident.incident_id
    alert_info.display_id = str(uuid.uuid4())
    alert_info.rule_generator = ", ".join(incident.incident_types)
    alert_info.name = INCIDENT_NAME.format(alert_info.rule_generator)
    alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
    alert_info.device_product = DEFAULT_DEVICE_PRODUCT
    alert_info.priority = severity_value
    alert_info.end_time = alert_info.start_time = incident.timestamp
    alert_info.events = incident.to_events()
    environment_dict = incident.to_flat_dict()
    if alert_info.events:
        environment_dict.update(alert_info.events[0])
    alert_info.environment = environment_common.get_environment(environment_dict)

    siemplify.LOGGER.info(f"Alert info created for incident {incident.incident_id}")

    return alert_info


if __name__ == "__main__":
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
