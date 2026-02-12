from __future__ import annotations

# ==============================================================================
# title           :SymantecICDXQueryConnector.py
# description     :This Module contain SymantecICDXQueryConnector query Connector logic.
# author          : zivh@siemplify.co
# date            : 07-04-19
# python_version  :2.7
# libraries       : -
# requirements    : -
# Product Version: 1.0
# ==============================================================================
import json
import os
import sys

import arrow
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_string_to_unix_time,
    dict_to_flat,
    output_handler,
)

from ..core.SymantecICDXManager import SymantecICDXManager

# ============================== CONSTS ===================================== #
DEVICE_VENDOR = DEVICE_PRODUCT = "SymantecICDX"
UTC_TIMEZONE_STRING = "UTC"
TIMESTAMP_FILE_NAME = "timestamp.stmp"
RULE_GENERATOR = "Vulnerabilities"
EVENTS_LIMIT = 10
DEFAULT_DAYS_BACKWARDS = 1
DEFAULT_ALERT_NAME = "Symantec ICDX Default Alert Name"
ALERT_NAME_KEY = "message"
ALERT_ID_KEY = "uuid"
SCRIPT_NAME = "SymantecICDX Connector"
IDS_HOURS_LIMIT = 72
IDS_FILE = "ids.json"
# ============================== CLASSES ==================================== #


class SymantecICDXConnectorException(Exception):
    """
    SymantecICDX Cases Connector Exception
    """

    pass


class SymantecICDXConnector:
    """
    SymantecICDX Connector
    """

    def __init__(self, symantec_icdx_manager, connector_scope, environment_field_name=None):
        self.icdx_manager = symantec_icdx_manager
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.environment_field_name = environment_field_name

    @staticmethod
    def validate_timestamp(timestamp, max_days_backwards=DEFAULT_DAYS_BACKWARDS):
        """
        Validate timestamp in range
        :param timestamp: {unixtime} last run timestamp.
        :param max_days_backwards: {int} days backwards to check timestamp.
        :return: {long} if first run, return current time minus offset time, else return timestamp from file
        """
        # Calculate- Days backwards to milliseconds.
        offset_datetime = arrow.utcnow().shift(days=-max_days_backwards).datetime
        offset_timestamp = convert_datetime_to_unix_time(offset_datetime)

        # Calculate max time with offset.
        if timestamp < offset_timestamp:
            return offset_timestamp

        return timestamp

    def create_case_info(self, alert):
        """
        Create CaseInfo object from SymantecICDX alert
        :param alert: {dict} An SymantecICDX Case
        :return: {CaseInfo} The newly created case
        """
        self.logger.info(
            f"Creating Case for Alert {str(alert.get('message')).encode('utf-8')}, UUID: {str(alert.get('uuid')).encode('utf-8')}"
        )

        try:
            # Create the CaseInfo
            case_info = CaseInfo()

            case_info.name = alert.get(ALERT_NAME_KEY, DEFAULT_ALERT_NAME)
            case_info.ticket_id = alert[ALERT_ID_KEY]

            case_info.rule_generator = alert.get(ALERT_NAME_KEY, DEFAULT_ALERT_NAME)
            case_info.display_id = alert[ALERT_ID_KEY]
            case_info.identifier = alert[ALERT_ID_KEY]
            case_info.device_vendor = DEVICE_VENDOR
            case_info.priority = 40  # Defaulting to Low.
            case_info.device_product = alert.get("product_name", DEVICE_PRODUCT)
            case_info.environment = (
                alert.get(self.environment_field_name)
                or self.connector_scope.context.connector_info.environment
            )

            try:
                alert_time = convert_string_to_unix_time(alert.get("log_time", 1))
            except Exception as e:
                self.logger.error(f"Unable to get alert time: {str(e)}")
                self.logger.exception(e)
                alert_time = 1

            case_info.start_time = alert_time

            try:
                case_info.end_time = (
                    convert_string_to_unix_time(alert.get("end_time", 1))
                    if alert.get("end_time")
                    else alert_time
                )

            except Exception as e:
                self.logger.error(f"Unable to get alert end time: {str(e)}")
                self.logger.exception(e)
                case_info.end_time = alert_time

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {str(e)}")

        case_info.events = [dict_to_flat(alert)]

        return case_info

    def read_ids(self, ids_file_path):
        """
        Read existing alerts IDs from ids file (from last 24h only)
        :param ids_file_path: {str} The path of the ids file.
        :return: {list} List of the uds
        """
        if not os.path.exists(ids_file_path):
            return {}

        try:
            with open(ids_file_path, "r") as f:
                existing_ids = json.loads(f.read())

                filtered_ids = {}
                for alert_id, timestamp in list(existing_ids.items()):
                    if timestamp > arrow.utcnow().shift(hours=-IDS_HOURS_LIMIT).timestamp:
                        filtered_ids[alert_id] = timestamp

                return filtered_ids

        except Exception as e:
            self.connector_scope.LOGGER.error(f"Unable to read ids file: {str(e)}")
            self.connector_scope.LOGGER.exception(e)
            return {}

    def write_ids(self, ids_file_path, ids):
        """
        Write ids to the ids file
        :param ids_file_path: {str} The path of the ids file.
        :param ids: {dict} The ids to write to the file
        """
        if not os.path.exists(os.path.dirname(ids_file_path)):
            os.makedirs(os.path.dirname(ids_file_path))

        with open(ids_file_path, "w") as f:
            f.write(json.dumps(ids))

    @staticmethod
    def filter_old_alerts(alerts, existing_ids):
        """
        Filter alerts that were already processed
        :param alerts: {list} The alerts to filter
        :param existing_ids: {list} The ids to filter
        :return: {list} The filtered alerts
        """
        filtered_alerts = []

        for alert in alerts:
            if alert.get("uuid") not in list(existing_ids.keys()):
                filtered_alerts.append(alert)

        return filtered_alerts


@output_handler
def main(test_handler=False):
    """
    Main execution - SymantecICDX Cases Connector
    """
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = SCRIPT_NAME
    output_variables = {}
    log_items = []

    if test_handler:
        connector_scope.LOGGER.info("========== Starting Connector Test ==========.")
    else:
        connector_scope.LOGGER.info("========== Starting Connector ==========.")

    try:
        connector_scope.LOGGER.info("Connecting to SymantecICDX")

        api_root = connector_scope.parameters.get("Api Root")
        api_token = connector_scope.parameters.get("Api Token")
        verify_ssl = connector_scope.parameters.get("Verify SSL", "False").lower() == "true"
        environment_field_name = connector_scope.parameters.get("Environment Field Name")
        events_limit = int(connector_scope.parameters.get("Events Limit", EVENTS_LIMIT))
        events_query = connector_scope.parameters.get("Search Query")
        max_days_backwards = (
            int(connector_scope.parameters.get("Max Days Backwards"))
            if connector_scope.parameters.get("Max Days Backwards")
            else DEFAULT_DAYS_BACKWARDS
        )

        symantec_icdx_manager = SymantecICDXManager(api_root, api_token, verify_ssl)
        symantec_icdx_connector = SymantecICDXConnector(
            symantec_icdx_manager, connector_scope, environment_field_name
        )

        # last run time its the query start time param
        last_run_time_ms = symantec_icdx_connector.validate_timestamp(
            connector_scope.fetch_timestamp(), max_days_backwards
        )

        # Get alerts from SymantecICDX
        connector_scope.LOGGER.info(
            f"Collecting alerts from SymantecICDX since {last_run_time_ms}."
        )
        alerts = symantec_icdx_manager.find_events(
            query=events_query, start_time=last_run_time_ms, limit=events_limit
        )

        # Read already existing alerts ids
        existing_ids = symantec_icdx_connector.read_ids(
            os.path.join(connector_scope.run_folder, IDS_FILE)
        )

        filtered_alerts = symantec_icdx_connector.filter_old_alerts(alerts, existing_ids)

        sorted_alerts = sorted(
            filtered_alerts, key=lambda alert: arrow.get(alert.get("log_time", 1))
        )

        # Construct CaseInfo from alerts
        cases = []

        if test_handler:
            sorted_alerts = sorted_alerts[:1]

        connector_scope.LOGGER.info(f"Found {len(sorted_alerts)} alerts.")

        for alert in sorted_alerts:
            try:
                connector_scope.LOGGER.info(
                    f"Processing Alert {str(alert.get(ALERT_NAME_KEY)).encode('utf-8')}, UUID: {str(alert.get(ALERT_ID_KEY)).encode('utf-8')}"
                )

                case = symantec_icdx_connector.create_case_info(alert)

                is_overflow = False

                try:
                    is_overflow = connector_scope.is_overflowed_alert(
                        environment=case.environment,
                        alert_identifier=str(case.ticket_id),
                        alert_name=str(case.rule_generator),
                        product=str(case.device_product),
                    )

                except Exception as e:
                    connector_scope.LOGGER.error(
                        f"Failed to detect overflow for Alert {str(alert.get(ALERT_NAME_KEY)).encode('utf-8')}, UUID: {str(alert.get(ALERT_ID_KEY)).encode('utf-8')}. Error:"
                    )
                    connector_scope.LOGGER.exception(e)

                if not is_overflow:
                    cases.append(case)
                    existing_ids.update({alert["uuid"]: case.start_time})

                else:
                    connector_scope.LOGGER.warn(
                        f"Overflowed on Alert {str(alert.get(ALERT_NAME_KEY)).encode('utf-8')}, UUID: {str(alert.get(ALERT_ID_KEY)).encode('utf-8')}"
                    )

            except Exception as e:
                # Failed to build CaseInfo for alert
                connector_scope.LOGGER.error(
                    f"Failed to create CaseInfo for Alert {str(alert.get(ALERT_NAME_KEY)).encode('utf-8')}, UUID: {str(alert.get(ALERT_ID_KEY)).encode('utf-8')}"
                )

                connector_scope.LOGGER.error(f"Error Message: {str(e)}")
                connector_scope.LOGGER.exception(e)

                if test_handler:
                    raise e

        connector_scope.LOGGER.info(f"Completed. Found {len(cases)} cases.")

        if test_handler:
            connector_scope.LOGGER.info("--------- Test completed. ------------")

        if not test_handler and cases:
            try:
                # Last execution time is set to the newest event
                new_last_run_time = sorted(sorted_alerts, key=lambda alert: alert.get("log_time"))[
                    -1
                ].get("log_time")
                connector_scope.save_timestamp(
                    new_timestamp=convert_string_to_unix_time(new_last_run_time)
                )

                symantec_icdx_connector.write_ids(
                    os.path.join(connector_scope.run_folder, IDS_FILE), existing_ids
                )

            except Exception as e:
                connector_scope.LOGGER.error("Unable to save timestamp.")
                connector_scope.LOGGER.exception(e)

        # Return data
        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as e:
        connector_scope.LOGGER.error(str(e))
        connector_scope.LOGGER.exception(e)
        if test_handler:
            raise e


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main(test_handler=False)
    else:
        print("Test execution started")
        main(test_handler=True)
