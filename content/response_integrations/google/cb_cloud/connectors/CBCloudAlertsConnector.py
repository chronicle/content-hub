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
import sys
import arrow

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import filter_old_ids
from TIPCommon.smp_time import (
    siemplify_fetch_timestamp,
    save_timestamp,
    validate_timestamp,
)
from TIPCommon.smp_io import (
    read_ids_by_timestamp,
    write_ids_with_timestamp,
)

from ..core.exceptions import CBCloudConnectorValidationException
from ..core.CBCloudManager import CBCloudManager
from ..core.constants import DEFAULT_VENDOR, PROVIDER_NAME, ALERTS_CONNECTOR_NAME

TIMESTAMP_FILE = "timestamp.stmp"
MAP_FILE = "map.json"
IDS_FILE = "ids.json"
VALIDATOR_FIELDS = ["type", "category", "policy_name"]


@output_handler
def main(is_test_run):
    alerts = []
    all_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = ALERTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button" "Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    environment = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )

    environment_regex = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )

    org_key = extract_connector_param(
        siemplify, param_name="Organization Key", is_mandatory=True, print_value=True
    )

    api_id = extract_connector_param(siemplify, param_name="API ID", is_mandatory=True)

    api_secret_key = extract_connector_param(
        siemplify, param_name="API Secret Key", is_mandatory=True
    )

    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", input_type=bool, print_value=True
    )

    offset_in_hours = extract_connector_param(
        siemplify,
        param_name="Offset Time In Hours",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    max_alerts_per_cycle = extract_connector_param(
        siemplify,
        param_name="Max Alerts Per Cycle",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    min_severity = extract_connector_param(
        siemplify, param_name="Minimum Severity to Fetch", print_value=True
    )

    alert_name_field_name = extract_connector_param(
        siemplify,
        param_name="What Alert Field to use for Name field",
        is_mandatory=True,
        print_value=True,
    )

    rule_generator_field_name = extract_connector_param(
        siemplify,
        param_name="What Alert Field to use for Rule Generator",
        is_mandatory=True,
        print_value=True,
    )

    validate_alert_name_field_name(alert_name_field_name)
    validate_rule_generator_field_name(rule_generator_field_name)

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    environment_common = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify, environment, environment_regex, MAP_FILE
    )
    if is_test_run:
        siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps.")
        last_success_time_datetime = (
            arrow.utcnow().shift(hours=-offset_in_hours).datetime
        )
    else:
        last_success_time_datetime = validate_timestamp(
            siemplify_fetch_timestamp(siemplify, datetime_format=True), offset_in_hours
        )

    now = arrow.utcnow()

    existing_ids = read_ids_by_timestamp(
        siemplify, offset_in_hours=max(72, 2 * offset_in_hours)
    )

    manager = CBCloudManager(
        api_root=api_root,
        org_key=org_key,
        api_id=api_id,
        api_secret_key=api_secret_key,
        verify_ssl=verify_ssl,
    )

    if min_severity:
        siemplify.LOGGER.info(
            f"Fetching alerts from {last_success_time_datetime.strftime('%Y-%m-%d %H:%M:%SZ')} to {now.isoformat()} with min. severity of {min_severity}"
        )
    else:
        siemplify.LOGGER.info(
            f"Fetching alerts from {last_success_time_datetime.isoformat()} to {now.isoformat()}"
        )

    fetched_alerts = manager.get_alerts(
        start_time=last_success_time_datetime.isoformat(),
        end_time=now.isoformat(),
        min_severity=min_severity,
        workflows=["OPEN"],
        limit=max(max_alerts_per_cycle, 100),
        sort_by="backend_timestamp",
    )

    filtered_ids = filter_old_ids([alert.id for alert in fetched_alerts], existing_ids)
    filtered_alerts = [alert for alert in fetched_alerts if alert.id in filtered_ids]

    siemplify.LOGGER.info(
        f"Found {len(filtered_alerts)} new alert in since {last_success_time_datetime.isoformat()}."
    )

    if is_test_run:
        siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
        filtered_alerts = filtered_alerts[:1]

    filtered_alerts = sorted(filtered_alerts, key=lambda alert: alert.create_time_ms)

    if len(filtered_alerts) > max_alerts_per_cycle:
        filtered_alerts = filtered_alerts[:max_alerts_per_cycle]
        siemplify.LOGGER.info(f"Slicing to {max_alerts_per_cycle} alerts")

    for alert in filtered_alerts:
        try:

            is_overflowed = False
            siemplify.LOGGER.info(f"Processing alert {alert.id}")
            alert_info = create_alert_info(
                environment_common,
                alert,
                alert_name_field_name,
                rule_generator_field_name,
            )
            existing_ids.update({alert.id: alert.create_time})
            all_alerts.append(alert_info)

            try:
                is_overflowed = siemplify.is_overflowed_alert(
                    environment=alert_info.environment,
                    alert_identifier=alert_info.ticket_id,
                    alert_name=alert_info.rule_generator,
                    product=alert_info.device_product,
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error validation connector overflow, ERROR: {e}"
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            if is_overflowed:
                siemplify.LOGGER.info(
                    f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                )
                continue
            else:
                alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

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

    siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


def validate_alert_name_field_name(alert_name_field_name):
    """
    Validate the value passed to the Name Field of Siemplify Alert configuration
    :return: {bool} True if valid, exception otherwise
    """
    if alert_name_field_name not in VALIDATOR_FIELDS:
        raise CBCloudConnectorValidationException(
            'Valid values to use for the "What Alert Field to use for Name field" are type, category or policy_name'
        )

    return True


def validate_rule_generator_field_name(rule_generator_field_name):
    """
    Validate the value passed to the Rule Generator Field of Siemplify Alert configuration
    :return: {bool} True if valid, exception otherwise
    """
    if rule_generator_field_name not in VALIDATOR_FIELDS:
        raise CBCloudConnectorValidationException(
            'Valid values to use for the "What Alert Field to use for Rule Generator" are type, category or policy_name'
        )

    return True


def create_alert_info(
    environment_common, alert, alert_name_field_name, rule_generator_field_name
):
    """
    Create an AlertInfo object from a single alert
    :param environment_common: {EnvironmentHandle}
    :param alert: {Alert} An alert instance
    :param alert_name_field_name: {unicode} The field name to take the alert name from
    :param rule_generator_field_name: {unicode} The field name to take the rule generator value from
    :return: {AlertInfo} The created alert info object
    """
    alert_info = AlertInfo()
    alert_info.start_time = alert.create_time_ms
    alert_info.end_time = alert.last_update_time_ms
    alert_info.ticket_id = alert.id
    alert_info.display_id = alert.id
    alert_info.name = f"CBCLOUD_Alert_{getattr(alert, alert_name_field_name)}"
    alert_info.rule_generator = f"CBCLOUD_{getattr(alert, rule_generator_field_name)}"
    alert_info.priority = alert.priority
    alert_info.description = alert.reason
    alert_info.device_product = PROVIDER_NAME
    alert_info.device_vendor = DEFAULT_VENDOR
    alert_info.environment = environment_common.get_environment(alert.as_json())
    alert_info.source_grouping_identifier = alert.threat_id
    alert_info.events = [alert.as_event()]
    alert_info.extensions = {"id": alert.id, "legacy_alert_id": alert.legacy_alert_id}

    return alert_info


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main(is_test_run=False)
    else:
        print("Test execution started")
        main(is_test_run=True)
