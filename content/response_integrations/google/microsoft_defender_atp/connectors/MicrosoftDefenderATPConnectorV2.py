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

from EnvironmentCommon import GetEnvironmentCommonFactory

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_time import (
    save_timestamp,
    get_last_success_time,
    is_approaching_timeout,
)
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_overflowed

from ..core.constants import (
    AVAILABLE_STATUSES,
    AVAILABLE_SEVERITIES,
    STORED_IDS_LIMIT,
    LOGIN_API_ROOT_DEFAULT,
)
from ..core.MicrosoftDefenderATPManager import MicrosoftDefenderATPManager
from ..core.MicrosoftDefenderATPTransformationLayer import (
    MicrosoftDefenderATPTransformationLayer,
)
from ..core.UtilsManager import (
    DefenderATPManagerConfig,
    init_defender_atp_manager,
    pass_whitelist_filter,
    UNIX_FORMAT,
)

connector_starting_time = unix_now()
CONNECTOR_NAME = "Microsoft Defender ATP Connector V2"


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    processed_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    login_api_root = extract_connector_param(
        siemplify,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
        print_value=True,
    )

    defender_atp_api_root = extract_connector_param(
        siemplify,
        param_name="Defender ATP API Root",
        is_mandatory=True,
        print_value=True,
    )

    defender_api_root = extract_connector_param(
        siemplify,
        param_name="365 Defender API Root",
        is_mandatory=True,
        print_value=True,
    )

    graph_api_root = extract_connector_param(
        siemplify,
        param_name="Graph API Root",
        print_value=True,
    )

    use_v2_api = bool(graph_api_root)

    directory_id = extract_connector_param(
        siemplify,
        param_name="Azure Active Directory ID",
        is_mandatory=True,
        print_value=True,
    )

    client_id = extract_connector_param(
        siemplify,
        param_name="Integration Client ID",
        is_mandatory=True,
        print_value=False,
    )

    client_secret = extract_connector_param(
        siemplify,
        param_name="Integration Client Secret",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=False,
    )

    environment = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )

    environment_regex = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )

    offset_hours = extract_connector_param(
        siemplify,
        param_name="Offset Time In Hours",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )

    limit = extract_connector_param(
        siemplify,
        param_name="Max Alerts per Cycle",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )

    statuses = extract_connector_param(
        siemplify,
        param_name="Alert Statuses to Fetch",
        is_mandatory=True,
        print_value=True,
    )

    severities = extract_connector_param(
        siemplify,
        param_name="Alert Severities to Fetch",
        is_mandatory=True,
        print_value=True,
    )

    disable_overflow = extract_connector_param(
        siemplify, param_name="Disable Overflow", input_type=bool, print_value=True
    )

    whitelist_as_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        input_type=bool,
        print_value=True,
    )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    device_product_field = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=True
    )

    statuses = MicrosoftDefenderATPManager.convert_comma_separated_to_list(statuses)
    severities = MicrosoftDefenderATPManager.convert_comma_separated_to_list(severities)
    common_environment = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify, environment, environment_regex
    )

    config = DefenderATPManagerConfig(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=directory_id,
        resource=defender_atp_api_root,
        login_api_root=login_api_root,
        verify_ssl=verify_ssl,
        chronicle_soar=siemplify,
        microsoft_graph_url=graph_api_root,
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if not all(status in AVAILABLE_STATUSES for status in statuses):
            raise Exception(
                f'Invalid value provided for "Alert Statuses to Fetch" parameter. Possible values: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(AVAILABLE_STATUSES)}'
            )

        if not all(severity in AVAILABLE_SEVERITIES for severity in severities):
            raise Exception(
                f'Invalid value provided for "Alert Severities to Fetch" parameter. Possible values: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(AVAILABLE_SEVERITIES)}'
            )

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        client = init_defender_atp_manager(
            config=config,
        )
        defender_api_client = MicrosoftDefenderATPManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=directory_id,
            resource=defender_atp_api_root,
            login_api_root=login_api_root,
            defender_api_resource=defender_api_root,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        fetched_alerts = []
        filtered_alerts = client.get_filtered_alerts(
            existing_ids=existing_ids,
            limit=limit,
            start_timestamp=get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": offset_hours},
                time_format=UNIX_FORMAT,
            ),
            statuses=statuses,
            severities=severities,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing Alert {alert.id}")

                if not pass_filters(
                    siemplify, whitelist_as_blacklist, alert, "detection_source"
                ):
                    # Update existing alerts
                    existing_ids.append(alert.id)
                    fetched_alerts.append(alert)
                    continue

                if not use_v2_api and alert.incident_id:
                    alert.set_events(
                        defender_api_client.get_alert_data(alert.id, alert.incident_id)
                    )

                if not alert.alert_data:
                    alert.alert_data.update({"alert_response": [alert.raw_data]})

                # Update existing alerts
                if alert.id not in existing_ids:
                    existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    common_environment,
                    device_product_field=device_product_field,
                    severity=MicrosoftDefenderATPTransformationLayer.calculate_priority(
                        alert.severity,
                        use_v2_api=use_v2_api,
                    ),
                    use_v2_api=use_v2_api,
                )

                if use_v2_api and not alert_info.events:
                    siemplify.LOGGER.info(
                        f"No events found for alert {alert.id}. Skipping..."
                    )
                    continue

                if not disable_overflow:
                    if is_overflowed(siemplify, alert_info, is_test_run):
                        siemplify.LOGGER.info(
                            f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping..."
                        )
                        # If is overflowed we should skip
                        continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise
            siemplify.LOGGER.info(f"Finished processing alert {alert.id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts,
                timestamp_key="alert_creation_time_timestamp",
            )

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of {len(fetched_alerts)}"
        )

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} alerts")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(siemplify, whitelist_as_a_blacklist, alert, model_key):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    return True


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
