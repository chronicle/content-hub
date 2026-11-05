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

# ============================================================================#
# title           :EndgameConnector.py
# description     :This Module contain all Endgame connector functionality
# author          :zivh@siemplify.co
# date            :12-06-19
# python_version  :2.7
# ============================================================================#

# ============================= IMPORTS ===================================== #
import sys
import re
import arrow
from urllib.parse import urlparse, parse_qs
from soar_sdk.SiemplifyUtils import dict_to_flat, unix_now, convert_string_to_unix_time
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from ..core.EndgameManager import EndgameManager
from ..core.EndgameCommon import EndgameCommon
import os
import json

# ============================== CONSTS ===================================== #
DEFAULT_PRODUCT = DEFAULT_VENDOR = "Endgame"
ALERTS_LIMIT = 20
TIMEZONE = "UTC"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # ISO-8601 datetime
TIMESTAMP_FILE = "timestamp.stmp"
MAP_FILE = "map.json"
IDS_FILE = "ids.json"
NEXT_ALERTS_QUERY_FILE = "alerts.json"

DEFAULT_MAX_ALERTS_PER_CYCLE = 10
HIGH_RISK = "high"
LOW_RISK = "low"
UPPERCASE_REGEX = "[A-Z][^A-Z]*"

# ============================== PAYLOAD ===================================== #


# ============================= CLASSES ===================================== #


class EndgameConnectorException(Exception):
    """
    Endgame Exception
    """

    pass


class EndgameConnector:
    """
    Endgame Connector
    """

    def __init__(
        self,
        connector_scope,
        endgame_manager,
        environment_field_name,
        endgame_common,
        environment_regex,
    ):
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.endgame_manager = endgame_manager
        self.environment_field_name = environment_field_name
        self.endgame_common = endgame_common
        self.environment_regex = environment_regex
        self.map_file = os.path.join(self.connector_scope.run_folder, MAP_FILE)
        self.alerts_file = os.path.join(
            self.connector_scope.run_folder, NEXT_ALERTS_QUERY_FILE
        )

        try:
            if not os.path.exists(self.map_file):
                with open(self.map_file, "w+") as map_file:
                    map_file.write(
                        json.dumps(
                            {
                                "Original environment name": "Desired environment name",
                                "Env1": "MyEnv1",
                            }
                        )
                    )
                    self.connector_scope.LOGGER.info(
                        f"Mapping file was created at {str(self.map_file).encode('utf-8')}"
                    )
        except Exception as e:
            self.logger.error(f"Unable to create mapping file: {str(e)}")
            self.logger.exception(e)

    def read_ids(self, cast_keys_to_int=False, max_hours_backwards=24):
        """
        Read existing (arleady seen) alert ids from the ids.json file
        :param cast_keys_to_int: {bool} Whether to case the ids to int or not
        :param max_hours_backwards: {int} Max amount of hours to keep ids in the file (to prevent it from getting too big)
        :return:{dict} A dict describing the already seen ids {id: the unixtime when it was first seen}
        """
        ids_file_path = os.path.join(self.connector_scope.run_folder, IDS_FILE)
        self.logger.info(f"Fetching existing IDs from: {ids_file_path}")

        try:
            if not os.path.exists(ids_file_path):
                self.logger.info(f"Ids file doesn't exist at path {ids_file_path}")
                return {}

            with open(ids_file_path, "r") as f:
                self.logger.info("Reading existing ids from ids file")
                existing_ids = json.loads(f.read())

                filtered_ids = {}
                # Insert IDs that did not passed time retention time limit.
                for alert_id, timestamp in list(existing_ids.items()):
                    if (
                        timestamp
                        > arrow.utcnow().shift(hours=-max_hours_backwards).timestamp
                        * 1000
                    ):
                        filtered_ids[alert_id] = timestamp

                if cast_keys_to_int:
                    return {int(k): v for k, v in list(filtered_ids.items())}

                return filtered_ids

        except Exception as e:
            self.logger.error(f"Unable to read ids file: {e}")
            self.logger.exception(e)
            return {}

    def write_ids(self, ids_file_path, ids):
        """
        Write ids to the ids file
        :param ids_file_path: {str} The path of the ids file.
        :param ids: {dict} The ids to write to the file
        """
        try:
            self.logger.info(f"Writing ids to file: {ids_file_path}")

            if not os.path.exists(os.path.dirname(ids_file_path)):
                self.logger.info(
                    f"Ids file doesn't exist at {ids_file_path}. Creating new file."
                )
                os.makedirs(os.path.dirname(ids_file_path))

            with open(ids_file_path, "w") as f:
                try:
                    for chunk in json.JSONEncoder().iterencode(ids):
                        f.write(chunk)
                except:
                    # Move seeker to start of the file
                    f.seek(0)
                    # Empty the content of the file (the partially written content that was written before the exception)
                    f.truncate()
                    # Write an empty dict to the events data file
                    f.write("{}")
                    raise

        except Exception as e:
            self.logger.error(f"Failed writing IDs to IDs file, ERROR: {e}")
            self.logger.exception(e)

    def filter_old_ids(self, alert_ids, existing_ids):
        """
        Filter ids that were already processed
        :param alert_ids: {list} The ids to filter
        :param existing_ids: {list} The ids to filter
        :return: {list} The filtered ids
        """
        new_alert_ids = []

        for correlated_event_id in alert_ids:
            if correlated_event_id not in list(existing_ids.keys()):
                new_alert_ids.append(correlated_event_id)

        return new_alert_ids

    @staticmethod
    def get_priority(alert):
        """
        Translate the priority of Endgame to Siemplify priority
        :param alert: {dict} An Endgame alert
        :return: {int} The matching priority
        """
        alert_risk = alert.get("severity")
        if HIGH_RISK == alert_risk:
            return 100
        elif LOW_RISK == alert_risk:
            return 40

        return 40

    @staticmethod
    def split_by_upper_case(text):
        """
        When endgame type is more than one word - the display is combined string (e.g. SiemplifyTest instead of Siemplify Test)
        :param text: {string} text to split by uppercase
        :return: {string} Text with spaces between words (e.g. Siemplify Test)
        """
        return " ".join(re.findall(UPPERCASE_REGEX, text))

    def get_alerts_manager(
        self, last_run, max_alerts_per_cycle=DEFAULT_MAX_ALERTS_PER_CYCLE
    ):
        """
        Fetch alerts from Endgame from last run
        :param last_run: {str} The time to fetch the alerts from (%Y-%m-%dT%H:%M:%SZ)
        :param max_alerts_per_cycle: {int} Max num of alerts to fetch in one time.
        :return: {list} List of found alerts
        """
        # alerts_file content is the next query params
        # for paginate the results
        query = None

        if os.path.exists(self.alerts_file):
            with open(self.alerts_file, "r") as f:
                try:
                    query = json.loads(f.read())
                except Exception as e:
                    self.connector_scope.LOGGER.error(
                        "Unable to load query from alerts file"
                    )
                    self.connector_scope.LOGGER.exception(e)

        if query:
            self.connector_scope.LOGGER.info(f"Query exists: {query}")
            results, payload = self.endgame_manager.get_alerts_by_query(query)

        else:
            # Limit param will cut the alerts to max_alerts_per_cycle
            # Alerts are sorted by alert creation time - Ascending
            self.connector_scope.LOGGER.info("Query doesn't exist. Starting new query.")
            results, payload = self.endgame_manager.get_alerts(
                end_timestamp=last_run, limit_per_page=max_alerts_per_cycle
            )
        all_alerts = results.get("data")
        self.paginate_results(results, payload, self.alerts_file)

        # Validate the number of alerts is according to the limit
        if len(all_alerts) > max_alerts_per_cycle:
            self.connector_scope.LOGGER.info(
                f"Slicing to {max_alerts_per_cycle} alerts."
            )
            all_alerts = all_alerts[:max_alerts_per_cycle]

        return all_alerts

    def create_event(self, alert):
        """
        Create event from Endgame alert
        :param alert: {dict} An Endgame alert
        :return: {dict} event details
        """
        self.logger.info("Creating security event")
        event_details = {
            "Alert Type": self.split_by_upper_case(alert.get("type")),
            "Status": alert.get("archived") or "Open",
            "Assigned To": alert.get("assigned_to").get("full_name") or "Unassigned",
            "Severity": alert.get("severity"),
            "Date Created": alert.get("created_at"),
            "Endpoint Name": alert.get("endpoint").get("name"),
            "Endpoint IP Address": alert.get("endpoint").get("ip_address"),
            "Endpoint Status": alert.get("endpoint").get("status"),
            "Endpoint OS": alert.get("endpoint").get("display_operating_system"),
        }
        event_details.update(dict_to_flat(alert.get("data")))

        # remove none items
        event_details = {k: v for k, v in list(event_details.items()) if v is not None}
        return event_details

    def create_case_info(self, alert):
        """
        Create CaseInfo object from Endgame alert
        :param alert: {dict} An Endgame alert
        :return: {CaseInfo} The newly created case
        """
        self.logger.info(f"Creating Case for Alert {alert['id']}")
        self.logger.info(f"Alert Time: {alert.get('created_at')}")

        try:
            # Create the CaseInfo
            case_info = CaseInfo()

            # split by uppercase
            case_info.name = self.split_by_upper_case(alert.get("type"))

            case_info.ticket_id = alert["id"]
            case_info.display_id = alert["id"]
            case_info.rule_generator = case_info.name
            case_info.device_vendor = DEFAULT_VENDOR
            case_info.device_product = DEFAULT_PRODUCT
            case_info.priority = self.get_priority(alert)

            try:
                # Verify timezone (MS) --> this is UTC TIME
                alert_time = convert_string_to_unix_time(alert.get("created_at"))
            except Exception as e:
                self.logger.error(f"Unable to get alert time: {str(e)}")
                self.logger.exception(e)
                alert_time = 0

            case_info.start_time = alert_time
            case_info.end_time = alert_time

            if self.environment_field_name and alert.get(self.environment_field_name):
                # Get the environment from the given field
                environment = alert.get(self.environment_field_name, "")

                if self.environment_regex:
                    # If regex pattern given - extract environment
                    match = re.search(self.environment_regex, environment)

                    if match:
                        # Get the first matching value to match the pattern
                        environment = match.group()

                # Try to resolve the found environment to its mapped alias.
                # If the found environment / extracted environment is empty
                # use the default environment
                case_info.environment = (
                    self.endgame_common.get_mapped_environment(
                        environment, self.map_file
                    )
                    if environment
                    else self.connector_scope.context.connector_info.environment
                )

            else:
                # Default env
                case_info.environment = (
                    self.connector_scope.context.connector_info.environment
                )

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {str(e)}")

        # Split the alert to events and flatten them
        try:
            event = self.create_event(alert)
        except Exception as e:
            self.logger.error(
                f"Unable to create an event from Endgame alert: {alert['id']}. Error: {str(e)}"
            )
            event = {}

        case_info.events = [event]

        return case_info

    def paginate_results(self, results, original_payload, alerts_file):
        """
        Paginate the results
        :param results: {dict} original response object
        :param original_payload: {dict} original payload
        :param alerts_file: {string} alerts file path
        :return: {list} alerts updated list
        """
        with open(alerts_file, "w") as f:
            if results.get("metadata").get("next_url"):
                o = urlparse(results.get("metadata").get("next_url"))
                query = parse_qs(o.query)
                if query.get("to"):
                    del query["to"]
                # Update with previous payload
                original_payload.update(query)
                self.connector_scope.LOGGER.info(f"Updated query: {original_payload}")
                f.write(json.dumps(original_payload))
            else:
                self.connector_scope.LOGGER.info("No next_url. Query has finished.")
                # Delete file content
                f.seek(0)
                f.truncate()
                f.write("{}")


@output_handler
def main(test_handler=False):
    """
    Main execution - Endgame Connector
    """
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = "Endgame Connector"
    output_variables = {}
    log_items = []

    if test_handler:
        connector_scope.LOGGER.info("========== Starting Connector Test ==========.")
    else:
        connector_scope.LOGGER.info("========== Starting Connector ==========.")

    try:
        connector_scope.LOGGER.info("Connecting to Endgame")
        api_root = connector_scope.parameters["API Root"]
        username = connector_scope.parameters["Username"]
        password = connector_scope.parameters["Password"]
        use_ssl = (
            str(connector_scope.parameters.get("Verify SSL", "False")).lower() == "true"
        )
        offset = (
            int(connector_scope.parameters.get("Max Days Backwards", 3))
            if connector_scope.parameters.get("Max Days Backwards")
            else 3
        )
        environment_field_name = connector_scope.parameters.get(
            "Environment Field Name"
        )
        environment_regex = connector_scope.parameters.get("Environment Regex Pattern")
        alerts_limit = (
            int(connector_scope.parameters.get("Alerts Count Limit"))
            if connector_scope.parameters.get("Alerts Count Limit")
            else ALERTS_LIMIT
        )

        endgame_manager = EndgameManager(
            api_root, username=username, password=password, use_ssl=use_ssl
        )
        endgame_common = EndgameCommon(connector_scope, connector_scope.LOGGER)
        endgame_connector = EndgameConnector(
            connector_scope,
            endgame_manager,
            environment_field_name,
            endgame_common,
            environment_regex,
        )

        # Validate timezone
        last_run = endgame_common.validate_timestamp(
            connector_scope.fetch_timestamp(datetime_format=True), offset
        )
        last_run = last_run.strftime(TIME_FORMAT)

        existing_ids = endgame_connector.read_ids(max_hours_backwards=24 * offset * 2)
        # Set current time for next run
        current_time = unix_now()

        # Get alerts from Endgame
        connector_scope.LOGGER.info(f"Collecting alerts from Endgame since {last_run}.")
        alerts = endgame_connector.get_alerts_manager(last_run, alerts_limit)
        connector_scope.LOGGER.info(f"Found {len(alerts)} alerts")

        connector_scope.LOGGER.info("Filtering already existing alerts")
        filtered_alert_ids = endgame_connector.filter_old_ids(
            [alert["id"] for alert in alerts], existing_ids
        )
        alerts = [alert for alert in alerts if alert["id"] in filtered_alert_ids]
        connector_scope.LOGGER.info(f"Filtered to {len(alerts)} new alerts.")

        # Construct CaseInfo from alerts
        cases = []

        if test_handler:
            alerts = alerts[-1:]

        for alert in alerts:
            try:
                connector_scope.LOGGER.info(f"Processing alert {alert['id']}")

                case = endgame_connector.create_case_info(alert)
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
                        f"Failed to detect overflow for Alert {alert['id']}"
                    )
                    connector_scope.LOGGER.exception(e)

                if not is_overflow:
                    cases.append(case)

                else:
                    connector_scope.LOGGER.warn(f"Overflowed on Alert {alert['id']}")

                existing_ids.update({case.ticket_id: case.start_time})

            except Exception as e:
                # Failed to build CaseInfo for alert
                connector_scope.LOGGER.error(
                    f"Failed to create CaseInfo for alert {alert['id']}: {str(e)}"
                )
                connector_scope.LOGGER.error(f"Error Message: {str(e)}")

                if test_handler:
                    raise e

        connector_scope.LOGGER.info(f"Completed. Found {len(cases)} cases.")

        if test_handler:
            connector_scope.LOGGER.info("--------- Test completed. ------------")

        # Alerts and NOT cases in case that everything s overflow = loop forever
        if alerts:
            new_last_run_time = convert_string_to_unix_time(alerts[-1]["created_at"])
        else:
            new_last_run_time = current_time

        if not test_handler and alerts:
            endgame_connector.write_ids(
                os.path.join(connector_scope.run_folder, IDS_FILE), existing_ids
            )
            connector_scope.save_timestamp(new_timestamp=new_last_run_time)

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
