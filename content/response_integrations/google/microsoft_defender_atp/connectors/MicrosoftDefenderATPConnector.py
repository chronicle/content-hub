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
from datetime import timedelta

from EnvironmentCommon import GetEnvironmentCommonFactory

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, utc_now, convert_string_to_unix_time

from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_time import save_timestamp, get_last_success_time
from TIPCommon.smp_io import read_ids_by_timestamp, write_ids_with_timestamp
from TIPCommon.utils import is_overflowed

from ..core.constants import LOGIN_API_ROOT_DEFAULT
from ..core.MicrosoftDefenderATPCommon import MicrosoftDefenderATPCommon
from ..core.MicrosoftDefenderATPManager import MicrosoftDefenderATPManager
from ..core.MicrosoftDefenderATPTransformationLayer import (
    MicrosoftDefenderATPTransformationLayer,
)


CONNECTOR_NAME = "Microsoft Azure Sentinel Incidents Connector"
VENDOR = "Microsoft Azure Sentinel"
PRODUCT = "DummyProduct"
DEFAULT_VENDOR_NAME = "Microsoft"
DEFAULT_PRODUCT_NAME = "Microsoft Defender ATP"


@output_handler
def main(is_test_run):
    alerts = []
    all_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button" "Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    environment = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    environment_regex = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    login_api_root = extract_connector_param(
        siemplify,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
        print_value=True,
    )

    resource = extract_connector_param(
        siemplify,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    integration_client_id = extract_connector_param(
        siemplify,
        param_name="Integration Client ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    integration_client_secret = extract_connector_param(
        siemplify,
        param_name="Integration Client Secret",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    siem_client_id = extract_connector_param(
        siemplify,
        param_name="SIEM Client ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    siem_client_secret = extract_connector_param(
        siemplify,
        param_name="SIEM Client Secret",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    tenant_id = extract_connector_param(
        siemplify,
        param_name="Azure Active Directory ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    offset_hours = extract_connector_param(
        siemplify,
        param_name="Offset Time In Hours",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    statuses = extract_connector_param(
        siemplify,
        param_name="Alert Statuses to Fetch",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    severities = extract_connector_param(
        siemplify,
        param_name="Alert Severities to Fetch",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    limit = extract_connector_param(
        siemplify,
        param_name="Max Alerts per Cycle",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    statuses = MicrosoftDefenderATPManager.convert_comma_separated_to_list(statuses)
    severities = MicrosoftDefenderATPManager.convert_comma_separated_to_list(severities)

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    environment_common = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify, environment, environment_regex
    )
    microsoft_defender_atp_common = MicrosoftDefenderATPCommon(siemplify.LOGGER)

    if is_test_run:
        siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
        last_success_time_datetime = microsoft_defender_atp_common.validate_timestamp(
            utc_now() - timedelta(hours=offset_hours), offset_hours
        )
    else:
        last_success_time_datetime = get_last_success_time(
            siemplify, offset_with_metric={"hours": offset_hours}
        )

    existing_ids = read_ids_by_timestamp(
        siemplify, offset_in_hours=offset_hours, convert_to_milliseconds=True
    )

    client = MicrosoftDefenderATPManager(
        client_id=integration_client_id,
        client_secret=integration_client_secret,
        tenant_id=tenant_id,
        resource=resource,
        login_api_root=login_api_root,
    )

    siem_client = MicrosoftDefenderATPManager(
        client_id=siem_client_id,
        client_secret=siem_client_secret,
        tenant_id=tenant_id,
        resource="https://graph.windows.net",
        login_api_root=login_api_root,
    )

    if is_test_run:
        siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
        limit = 1

    fetched_alerts = client.get_alerts(
        alert_time_frame=offset_hours,
        statuses=statuses,
        severities=severities,
        limit=limit,
    )

    siemplify.LOGGER.info(
        f"{len(fetched_alerts)} alerts were fetched from timestamp {last_success_time_datetime}"
    )

    fetched_detections = siem_client.get_detections_siem(since_time_frame=offset_hours)
    siemplify.LOGGER.info(
        f"{len(fetched_detections)} detection were fetched from timestamp {last_success_time_datetime}"
    )

    filtered_alerts = filter_old_alerts(siemplify, fetched_alerts, existing_ids, "id")

    siemplify.LOGGER.info(
        f"Found {len(filtered_alerts)} new alert in since {last_success_time_datetime.isoformat()}."
    )

    filtered_alerts = sorted(
        filtered_alerts, key=lambda alert: alert.alert_creation_time
    )

    for alert in filtered_alerts:
        try:
            siemplify.LOGGER.info(f"Processing alert {alert.id}")
            events = list(
                [event for event in fetched_detections if event.alert_id == alert.id]
            )

            if not events:
                siemplify.LOGGER.info(
                    f'Alert with "{alert.id}" with investigation state "{alert.investigation_state}" does not have any events. Skipping'
                )
                continue
            alert_info = create_alert_info(siemplify, environment_common, alert, events)

            if is_overflowed(siemplify, alert_info, is_test_run):
                siemplify.LOGGER.info(
                    f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                )
                continue

            alerts.append(alert_info)
            siemplify.LOGGER.info(f"Alert {alert.id} was created.")
            all_alerts.append(alert_info)
            existing_ids.update({alert.id: alert.alert_creation_time})

        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to process alert {alert.id}", alert_id=alert.id
            )
            siemplify.LOGGER.exception(e)

            if is_test_run:
                raise

    if not is_test_run:
        if all_alerts:
            save_timestamp(siemplify, all_alerts, timestamp_key="start_time")

        write_ids_with_timestamp(siemplify, existing_ids)

    siemplify.LOGGER.info(f"Alerts Processed: {len(alerts)} of {len(all_alerts)}")
    siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


def create_alert_info(siemplify, environment_common, alert, events):
    siemplify.LOGGER.info(
        f"-------------- Started processing Alert {alert.id}", alert_id=alert.id
    )

    alert_info = AlertInfo()

    alert_info.display_id = alert.id
    alert_info.ticket_id = alert.id
    alert_info.name = alert.title
    alert_info.description = alert.description
    alert_info.priority = MicrosoftDefenderATPTransformationLayer.calculate_priority(
        alert.severity
    )
    alert_info.start_time = convert_string_to_unix_time(alert.first_event_time)
    alert_info.end_time = convert_string_to_unix_time(alert.last_event_time)

    alert_info.device_vendor = DEFAULT_VENDOR_NAME
    alert_info.device_product = DEFAULT_PRODUCT_NAME
    alert_info.rule_generator = alert.detection_source

    alert_info.extensions = alert.to_extension()

    alert_info.events = [event.to_json() for event in events]

    alert_info.environment = environment_common.get_environment(alert)

    siemplify.LOGGER.info(
        f"-------------- Finished processing Alert {alert.id}", alert_id=alert.id
    )
    return alert_info


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
