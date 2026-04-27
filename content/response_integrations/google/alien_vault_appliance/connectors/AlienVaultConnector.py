from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ============================================================================#
# title           :AlienVaultConnector.py
# description     :This Module contain all AlienVault connector functionality
# author          :avital@siemplify.co
# date            :17-05-2018
# python_version  :2.7
# ============================================================================#

# ============================= IMPORTS ===================================== #

import sys
import os
import json
import dateparser
import datetime
import pytz
import arrow
import urllib.parse
from soar_sdk.SiemplifyUtils import dict_to_flat
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from ..core.AlienVaultManager import AlienVaultManager

# ============================== CONSTS ===================================== #
DEFAULT_PRODUCT = DEFAULT_VENDOR = "AlienVault USM"
DEFAULT_NAME = "Alient Vault Default Alert Name"
ALERTS_LIMIT = 20
TIME_FORMAT = "%Y-%m-%d"
TIMESTAMP_FILE = "timestamp.stmp"
IDS_FILE = "ids.json"
IDS_HOURS_LIMIT = 24
UTC = "UTC"
UNKNOWN_ENV = "unknown"
HUMAN_TIMES = ["min", "day", "hour", "second", "min", "hour", "minute", "year"]
ALERT_LINK_URL = "ossim/#analysis/alarms/alarms-{0}"  # {0} - Alert ID


# ============================= CLASSES ===================================== #


class AlienVaultConnector:
    """
    AlienVault Connector
    """

    def __init__(
        self, connector_scope, alienvault_manager, environment_field_name, timezone=UTC
    ):
        self.timezone = timezone
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.alienvault_manager = alienvault_manager
        self.environment_field_name = environment_field_name

    def read_ids(self, ids_file_path):
        """
        Read existing alerts IDs from ids file.
        :param ids_file_path: {str} The path of the ids file.
        :return: {dict} Dict of the ids ({id: id's entrance timestamp})
        """
        if not os.path.exists(ids_file_path):
            return {}

        try:
            with open(ids_file_path, "r") as f:
                return json.loads(f.read())
        except Exception as e:
            self.logger.error(f"Unable to read ids file: {str(e)}")
            self.logger._log.exception(e)
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

    def filter_old_ids(self, ids):
        """
        Filter ids that are older than IDS_HOURS_LIMIT hours
        :param ids: {dict} The ids to filter
        :return: {dict} The filtered ids
        """
        filtered_ids = {}
        for alert_id, timestamp in list(ids.items()):
            if timestamp > arrow.utcnow().shift(hours=-IDS_HOURS_LIMIT).timestamp:
                filtered_ids[alert_id] = timestamp

        return filtered_ids

    @staticmethod
    def validate_timestamp(last_run_timestamp, offset):
        """
        Validate timestamp in range
        :param last_run_timestamp: {arrow datetime} last run timestamp
        :param offset: {datetime} max dyas backward to fetch from
        :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
        """
        # Check if first run
        if last_run_timestamp.shift(days=offset) < arrow.utcnow():
            return arrow.utcnow().shift(days=-offset)
        else:
            return last_run_timestamp

    def get_alerts(self, last_run, max_alerts_per_cycle):
        """
        Fetch alerts from AlienVault from last run
        :param last_run: {arrow object} The time to fetch the alerts from
        :param max_alerts_per_cycle: {int} Max num of alerts to detch in one time.
        :return: {list} List of found alerts
        """
        last_run_timestamp = last_run.strftime(TIME_FORMAT)

        current_timestamp = arrow.utcnow()
        self.logger.info(f"Fetching alerts from {last_run}")

        all_alerts = self.alienvault_manager.get_alarms(
            last_run_timestamp, current_timestamp.strftime(TIME_FORMAT)
        )

        alerts = []

        # Read already existing alerts ids
        old_ids = self.read_ids(os.path.join(self.connector_scope.run_folder, IDS_FILE))

        # Filter out old ids (older than 24 hours)
        old_ids = self.filter_old_ids(old_ids)

        # Filter out old alerts by last run time and by ids vault
        for alert in all_alerts:
            if (
                self.parse_date(alert.get("Date", 0)) > last_run.timestamp
                and alert["Id"] not in old_ids
            ):
                alerts.append(alert)

        # Cut the alerts to max_alerts_per_cycle
        alerts = sorted(
            alerts, key=lambda alert: self.parse_date(alert.get("Date", 0))
        )[:max_alerts_per_cycle]

        # Add the added alerts to ids vault
        for alert in alerts:
            old_ids.update({alert["Id"]: current_timestamp.timestamp})

        self.write_ids(os.path.join(self.connector_scope.run_folder, IDS_FILE), old_ids)

        return alerts

    @staticmethod
    def get_gmt_timezone(timezone):
        """
        Convert Timezone name to utc offset ,i.e: US/eastern => -4000,
        in consideration of dst.
        :param timezone: {str} Timezone name
        :return: {str} The utc offset.
        """
        return datetime.datetime.now(pytz.timezone(timezone)).strftime("%z")

    def parse_date(self, timestamp):
        """
        Prase AlienVault times to unixtime.
        :param timestamp:
        :return: {int} The unix timestamp
        """
        try:
            # Check if date is in human format
            for human_time in HUMAN_TIMES:
                if human_time in timestamp:
                    return arrow.get(
                        dateparser.parse(
                            f"{timestamp} ago {self.get_gmt_timezone(self.timezone)}"
                        )
                    ).timestamp

            # Date is not in human form - try to parse as a regular date
            return arrow.get(dateparser.parse(timestamp)).timestamp

        except Exception as e:
            # Parsing failed!
            self.logger.error(f"Unable to parse date: {timestamp}")
            self.logger.exception(e)
            return 0

    @staticmethod
    def get_priority(alert):
        """
        Translate the priority of AlienVault to Siemplify priority
        :param alert: {dict} An alienvault alert
        :return: {int} The matching priority
        """
        alert_risk = int(alert.get("Risk"), 0)
        if 4 <= alert_risk:
            return 100
        elif 3 <= alert_risk:
            return 80
        elif 2 <= alert_risk:
            return 60
        elif 1 <= alert_risk:
            return 40

        return 0

    def get_events(self, alert, max_events_per_alert):
        """
        Fetch the events of an alert
        :param alert: {dict} AlienVault alert dict
        :param max_events_per_alert: {int} Max num of events to fetch per alert
        :return: {(list, total_event_count)} LIst of found events and the total count of all existing events in the siem
        """
        events = []
        all_events = []
        self.logger.info(
            f"Fetching first {max_events_per_alert} events of {alert['Id']}"
        )
        try:
            all_events = self.alienvault_manager.get_events_ids(alert["Id"])

            for event_id in all_events[:max_events_per_alert]:
                try:
                    self.logger.info(f"Fetching event {event_id}")

                    event = self.alienvault_manager.get_event_info(event_id)

                    event["Id"] = event_id
                    events.append(event)

                except Exception as e:
                    self.logger.error(
                        f"Couldn't get event info for event {event_id}: {str(e)}"
                    )
                    self.logger._log.exception(e)

        except Exception as e:
            self.logger.error(
                f"Unable to get events for alert {alert['Id']}: {str(e)}"
            )
            self.logger._log.exception(e)

        return events, len(all_events)

    def create_case_info(self, alert, max_events_per_alert):
        """
        Create CaseInfo object from AlienVault alert
        :param alert: {dict} An alienvault alert
        :param max_events_per_alert: {int} Max num of events to fetch per alert
        :return: {CaseInfo} The newly created case
        """
        self.logger.info(f"Creating Case for Alert {alert['Id']}")

        try:
            # Create the CaseInfo
            case_info = CaseInfo()

            try:
                if alert.get("Destination") and alert["Destination"].get("Hostname"):
                    name = f"{alert['Intent']} - {alert['Method']} - {alert['Destination']['Hostname']}"
                else:
                    name = f"{alert['Intent']} - {alert['Method']}"

            except Exception as e:
                self.logger.error(f"Unable to construct alert name: {str(e)}")
                self.logger._log.exception(e)
                name = DEFAULT_NAME

            case_info.name = name
            case_info.ticket_id = alert["Id"]

            case_info.rule_generator = name
            case_info.display_id = alert["Id"]
            case_info.device_vendor = DEFAULT_VENDOR
            case_info.device_product = DEFAULT_PRODUCT
            case_info.priority = self.get_priority(alert)
            case_info.extensions.update({"alert_link": alert.get("alert_link")})

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {str(e)}")

        events, total_events_count = self.get_events(alert, max_events_per_alert)

        alert_time = 1
        flat_events = []

        self.logger.info(f"Processing events of {alert['Id']}")
        for event in events:
            try:
                self.logger.info(
                    f"Processing event {event['Id']} - {event.get('Name')}"
                )
                event["device_product"] = event.get("Data Source Name", DEFAULT_PRODUCT)
                event["device_vendor"] = DEFAULT_VENDOR
                event["Timestamp"] = (
                    self.parse_date(event.get("Date", 1)) * 1000
                )  # Convert to millisecnods

                if event.get("Category").lower() == "alarm":
                    # The event is the alarm itself
                    try:
                        alert_time = (
                            self.parse_date(event.get("Date", 1)) * 1000
                        )  # Convert to millisecnods

                    except Exception as e:
                        self.logger.error(
                            f"Unable to get alarm time of alert {alert['Id']}: {str(e)}"
                        )
                        self.logger.exception(e)

                    case_info.environment = event.get(
                        self.environment_field_name,
                        self.connector_scope.context.connector_info.environment,
                    )

                flat_events.append(dict_to_flat(event))

            except Exception as e:
                self.logger.error(
                    f"Unable to get event data and flatten event {event['Id']}: {str(e)}"
                )
                self.logger.exception(e)

        if not case_info.environment or case_info.environment.lower() == UNKNOWN_ENV:
            # If the environment from AlienVault is set to Unknown
            # then take other event environment (find the first event that is not alarm)
            event_env = None
            for event in flat_events:
                if (
                    event.get("Category").lower() != "alarm"
                    and event.get(self.environment_field_name) != UNKNOWN_ENV
                ):
                    event_env = event.get(self.environment_field_name)
                    break
            case_info.environment = (
                event_env or self.connector_scope.context.connector_info.environment
            )

        case_info.events = flat_events
        case_info.start_time = alert_time
        case_info.end_time = alert_time
        case_info.extensions.update({"Total Events": total_events_count})

        return case_info


@output_handler
def test():
    """
    Test execution - AlienVault Connector
    """
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = "AlienVault Connector"
    result_params = {}
    result_value = True

    connector_scope.LOGGER.info("========== Starting Connector Test ==========.")

    connector_scope.LOGGER.info("Testing connection to AlienVault")
    api_root = connector_scope.parameters.get("Api Root")
    username = connector_scope.parameters.get("Username")
    password = connector_scope.parameters.get("Password")
    max_events_per_alert = int(connector_scope.parameters["Max Events Per Alert"])
    max_alert_per_cycle = int(connector_scope.parameters["Max Alerts Per Cycle"])
    offset = int(connector_scope.parameters["Max Days Backwards"])
    timezone = connector_scope.parameters.get("Server Timezone")
    environment_field_name = connector_scope.parameters["Environment Field Name"]

    alienvault_manager = AlienVaultManager(api_root, username, password)

    connector_scope.LOGGER.info("Connection is successful.")
    result_params["Connection"] = "Successful"

    alienvault_connector = AlienVaultConnector(
        connector_scope, alienvault_manager, environment_field_name, timezone
    )

    last_run = alienvault_connector.validate_timestamp(
        arrow.get(connector_scope.fetch_timestamp()), offset
    )

    # Get alerts
    connector_scope.LOGGER.info("Trying to fetch alerts.")
    alerts = alienvault_connector.get_alerts(last_run, max_alert_per_cycle)[:1]

    connector_scope.LOGGER.info(f"Successfully found {len(alerts)} alerts.")

    result_params["Fetching Alerts"] = "Successful"

    # Construct CaseInfos from alerts
    connector_scope.LOGGER.info("Testing CaseInfo construction.")

    cases = []
    for alert in alerts:
        try:
            connector_scope.LOGGER.info(
                f"Processing alert {alert['Id']}"
            )

            case = alienvault_connector.create_case_info(alert, max_events_per_alert)

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
                    f"Failed to detect overflow for Alert {case.name}"
                )
                connector_scope.LOGGER.exception(e)

            if not is_overflow:
                cases.append(case)

            else:
                connector_scope.LOGGER.warn(
                    f"{case.name}-{case.ticket_id}-{case.environment}-{case.device_product} found as overflow alert, skipping this alert."
                )

        except Exception as e:
            # Failed to build CaseInfo for alert
            connector_scope.LOGGER.error(
                f"Failed to create CaseInfo for alert {alert['Id']}"
            )
            connector_scope.LOGGER.error(f"Error Message: {str(e)}")

            connector_scope.LOGGER.exception(e)
            raise

    result_params["Building Case Info"] = "Successful"
    connector_scope.LOGGER.info("Successfully constructed CaseInfo for all alerts.")

    connector_scope.LOGGER.info("Test completed.")

    # Return data
    output_variables = {}
    log_items = []
    connector_scope.return_package(cases, output_variables, log_items)


@output_handler
def main():
    """
    Main execution - AlienVault Connector
    """
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = "AlienVault Connector"
    output_variables = {}
    log_items = []

    connector_scope.LOGGER.info("========== Starting Connector ==========.")

    try:
        connector_scope.LOGGER.info("Connecting to AlienVault")
        api_root = connector_scope.parameters.get("Api Root")
        username = connector_scope.parameters.get("Username")
        password = connector_scope.parameters.get("Password")
        max_events_per_alert = int(connector_scope.parameters["Max Events Per Alert"])
        max_alert_per_cycle = int(connector_scope.parameters["Max Alerts Per Cycle"])
        offset = int(connector_scope.parameters["Max Days Backwards"])
        timezone = connector_scope.parameters.get("Server Timezone")
        environment_field_name = connector_scope.parameters.get(
            "Environment Field Name"
        )

        alienvault_manager = AlienVaultManager(api_root, username, password)
        alienvault_connector = AlienVaultConnector(
            connector_scope, alienvault_manager, environment_field_name, timezone
        )

        # NOTICE!!! Fetching timestamp in seconds and not in milliseconds.
        last_run = alienvault_connector.validate_timestamp(
            arrow.get(connector_scope.fetch_timestamp()), offset
        )

        # Get alerts from AlienVault
        connector_scope.LOGGER.info("Collecting alerts from AlienVault.")
        alerts = alienvault_connector.get_alerts(last_run, max_alert_per_cycle)

        # Construct CaseInfo from alerts
        cases = []

        for alert in alerts:
            try:
                connector_scope.LOGGER.info(
                    f"Processing alert {alert['Id']}"
                )

                # Build alert link.
                alert["alert_link"] = urllib.parse.urljoin(
                    alienvault_manager.server_address,
                    ALERT_LINK_URL.format(alert.get("Id")),
                )

                case = alienvault_connector.create_case_info(
                    alert, max_events_per_alert
                )

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
                        f"Failed to detect overflow for Alert {case.name}"
                    )
                    connector_scope.LOGGER.exception(e)

                if not is_overflow:
                    cases.append(case)

                else:
                    connector_scope.LOGGER.warn(
                        f"{case.name}-{case.ticket_id}-{case.environment}-{case.device_product} found as overflow alert, skipping this alert."
                    )

            except Exception as e:
                # Failed to build CaseInfo for alert
                connector_scope.LOGGER.error(
                    f"Failed to create CaseInfo for alert {alert['Id']}: {str(e)}"
                )
                connector_scope.LOGGER.error(f"Error Message: {str(e)}")

        if alerts:
            # Sort the alerts by timestamp
            alerts = sorted(
                alerts,
                key=lambda alert: alienvault_connector.parse_date(alert.get("Date", 0)),
            )

            # Save last index's timestamp - in seconds (not in milliseconds)
            connector_scope.save_timestamp(
                new_timestamp=alienvault_connector.parse_date(alerts[-1]["Date"])
            )

        connector_scope.LOGGER.info(f"Completed. Found {len(cases)} cases.")

        # Return data
        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as e:
        connector_scope.LOGGER.error(str(e))
        connector_scope.LOGGER.exception(e)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main()
    else:
        print("Test execution started")
        test()
