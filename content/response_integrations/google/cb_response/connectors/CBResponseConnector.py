from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ============================================================================#
# title           :CBResponseConnector.py
# description     :This Module contain all CBResponse connector functionality
# author          :avital@siemplify.co
# date            :17-05-2018
# python_version  :2.7
# ============================================================================#

# ============================= IMPORTS ===================================== #

import sys
import arrow
import urllib.parse
import os
import json
from soar_sdk.SiemplifyUtils import dict_to_flat, utc_now, convert_string_to_unix_time
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from ..core.CBResponseManagerLoader import CBResponseManagerLoader
import datetime
from TIPCommon import extract_connector_param
from EnvironmentCommon import EnvironmentHandle
from ..core.CBResponseManager import WHITELIST_STRING, EXACT_STRING

# =====================================
#             CONSTANTS               #
# =====================================
CONNECTOR_NAME = "CBResponse Connector"
DEFAULT_ALERTS_LIMIT = 100
DEFAULT_OFFSET_TIME_HOURS = 24

# ============================== CONSTS ===================================== #
DEFAULT_PRODUCT = DEFAULT_VENDOR = "Carbon Black Response"
ALERTS_LIMIT = 20
IDS_HOURS_LIMIT = 72
TIMEZONE = "UTC"
IDS_FILE = "ids.json"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
QUERY = "created_time: [{} TO *] and status:Unresolved"
BINARY_ALERT_LINK_URL = "/#/binary/{0}"  # {0} - File Hash.
PROCESS_ALERT_LINK_URL = "/#/analyze/{0}/{1}"  # {0} - Process ID, Segment ID.
MAP_FILE = "map.json"


# ============================= CLASSES ===================================== #
class CBResponseConnectorException(Exception):
    """
    CBResponse Exception
    """

    pass


class CBResponseConnector:
    """
    CBResponse Connector
    """

    def __init__(self, connector_scope, cbresponse_manager, environment_common):
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.cbresponse_manager = cbresponse_manager
        self.environment_common = environment_common

        self.map_file = self.initialize_map_file()

    def initialize_map_file(self):
        """
        Validate map file exists and returns it's path.
        :return:
        """
        try:
            map_file_path = os.path.join(self.connector_scope.run_folder, MAP_FILE)
            if not os.path.exists(map_file_path):
                with open(map_file_path, "w") as map_file:
                    map_file.write(
                        json.dumps(
                            {
                                "Original environment name": "Desired environment name",
                                "Example-Env1": "Example-MyEnv1",
                            }
                        )
                    )
                    self.connector_scope.LOGGER.info(
                        f"Mapping file was created at {map_file_path}"
                    )

            return map_file_path

        except Exception as e:
            error_message = f"Unable to create mapping file: {e}"
            self.logger.error(error_message)
            self.logger.exception(e)
            raise Exception(error_message)

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
                    if (
                        timestamp
                        > arrow.utcnow().shift(hours=-IDS_HOURS_LIMIT).timestamp
                    ):
                        filtered_ids[alert_id] = timestamp

                return filtered_ids

        except Exception as e:
            self.connector_scope.LOGGER.error(f"Unable to read ids file: {e}")
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
            if alert.unique_id not in list(existing_ids.keys()):
                filtered_alerts.append(alert)

        return filtered_alerts

    @staticmethod
    def validate_timestamp(last_run_timestamp, offset_in_days):
        """
        Validate timestamp in range
        :param last_run_timestamp: {datetime} last run timestamp
        :param offset_in_days: {datetime} last run timestamp
        :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
        """
        current_time = utc_now()
        # Check if first run
        if current_time - last_run_timestamp > datetime.timedelta(days=offset_in_days):
            return current_time - datetime.timedelta(days=offset_in_days)
        else:
            return last_run_timestamp

    def create_case_info(self, alert):
        """
        Create CaseInfo object from CBResponse alert
        :param alert: {Alert} An ES alert
        :return: {CaseInfo} The newly created case
        """
        self.logger.info(f"Creating Case for Alert {alert.unique_id}")

        try:
            # Create the CaseInfo
            case_info = CaseInfo()

            case_info.name = alert.watchlist_name
            case_info.ticket_id = alert.unique_id

            case_info.rule_generator = alert.watchlist_name
            case_info.display_id = alert.unique_id
            case_info.device_vendor = DEFAULT_VENDOR
            case_info.device_product = DEFAULT_PRODUCT
            case_info.extensions = {
                "alert_link": alert.alert_link,
                "process_segment_id": alert.process_segment_id,
                "process_alert_link": alert.process_alert_link,
            }

            try:
                alert_time = convert_string_to_unix_time(alert.created_time)
            except Exception as e:
                self.logger.error(f"Unable to get alert time: {e}")
                self.logger.exception(e)
                alert_time = 1

            case_info.start_time = alert_time
            case_info.end_time = alert_time
            case_info.environment = self.environment_common.get_environment(
                alert.raw_data
            )

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {e}")

        # Split the alert to events and flatten them
        try:
            events = []

            # Add Time Unixtime to event.
            alert.start_time = alert.end_time = alert_time

            if alert.observed_filename:
                for observed_file in alert.observed_filename:
                    event = alert.as_event()
                    event["observed_filename"] = observed_file
                    events.append(event)

            else:
                events = [alert.as_event()]

            flat_events = list(map(dict_to_flat, events))

        except Exception as e:
            self.logger.error(f"Unable to split and flat events: {e}")
            self.logger.exception(e)
            flat_events = []

        case_info.events = flat_events

        return case_info


@output_handler
def main(test_handler=False):
    """
    Main execution - CBResponse Connector
    """
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    # INIT CONFIGURATION:
    api_root = extract_connector_param(siemplify, param_name="Api Root", input_type=str)
    api_key = extract_connector_param(siemplify, param_name="Api Key", input_type=str)
    version = extract_connector_param(siemplify, param_name="Version", input_type=float)
    ca_certificate_file = extract_connector_param(
        siemplify, param_name="CA Certificate File", input_type=str
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", default_value=False, input_type=bool
    )
    first_time_run_offset_in_days = extract_connector_param(
        siemplify,
        param_name="Max Days Backwards",
        default_value=DEFAULT_OFFSET_TIME_HOURS,
        input_type=int,
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", input_type=str
    )
    alerts_limit = extract_connector_param(
        siemplify,
        param_name="Alerts Count Limit",
        default_value=DEFAULT_ALERTS_LIMIT,
        input_type=int,
    )
    list_type = extract_connector_param(
        siemplify,
        param_name="List Type",
        default_value=WHITELIST_STRING,
        input_type=str,
    )
    list_operator = extract_connector_param(
        siemplify,
        param_name="List Operator",
        default_value=EXACT_STRING,
        input_type=str,
    )
    list_fields = extract_connector_param(
        siemplify, param_name="List Fields", input_type=str
    )
    list_fields = list_fields.split(",") if list_fields else []

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    try:
        map_file_path = os.path.join(siemplify.run_folder, MAP_FILE)
        manager = CBResponseManagerLoader.load_manager(
            version,
            api_root,
            api_key,
            siemplify.LOGGER,
            verify_ssl,
            ca_certificate_file,
        )
        environment_common = EnvironmentHandle(
            map_file_path,
            siemplify.LOGGER,
            environment_field_name,
            None,
            siemplify.context.connector_info.environment,
        )
        connector = CBResponseConnector(siemplify, manager, environment_common)

        last_success_time_datetime = connector.validate_timestamp(
            siemplify.fetch_timestamp(datetime_format=True),
            offset_in_days=first_time_run_offset_in_days,
        )
        alerts = manager.get_alerts(
            QUERY.format(last_success_time_datetime.strftime(TIME_FORMAT))
        )

        # Read already existing alerts ids
        existing_ids = connector.read_ids(os.path.join(siemplify.run_folder, IDS_FILE))

        alerts = connector.filter_old_alerts(alerts, existing_ids)

        alerts = sorted(alerts, key=lambda alert: alert.created_time)

        siemplify.LOGGER.info(
            f"Found {len(alerts)} alerts in since {last_success_time_datetime.isoformat()}."
        )
        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            alerts = alerts[:1]

        prepared_alerts = []
        # Construct CaseInfo from alerts
        cases = []

        if len(alerts) > alerts_limit:
            alerts = alerts[:alerts_limit]
            siemplify.LOGGER.info(f"Slicing to {len(alerts)} alerts.")

        if list_fields:
            for alert in alerts:
                try:
                    prepared_alerts.append(
                        manager.clear_alert_fields(
                            alert, list_type, list_operator, list_fields
                        )
                    )
                except Exception as err:
                    prepared_alerts.append(alert)
                    siemplify.LOGGER.error(
                        "Failed filtering alert fields for alert with"
                        " process id '{}', ERROR: {}".format(alert.process_id, err)
                    )
                    siemplify.LOGGER.exception(err)
        else:
            prepared_alerts = alerts

        for alert in prepared_alerts:
            try:
                siemplify.LOGGER.info(f"Processing alert {alert.unique_id}")

                # Build alert link.
                if alert.process_id:

                    alert.alert_link = urllib.parse.urljoin(
                        api_root,
                        PROCESS_ALERT_LINK_URL.format(
                            alert.process_id, alert.segment_id
                        ),
                    )

                    try:
                        alert.process_segment_id = manager.get_segment_id_by_process_id(
                            alert.process_id
                        )

                        alert.process_alert_link = urllib.parse.urljoin(
                            api_root,
                            PROCESS_ALERT_LINK_URL.format(
                                alert.process_id, alert.process_segment_id
                            ),
                        )
                    except Exception as e:
                        siemplify.LOGGER.error(
                            "Failed to get segment id from process id"
                        )
                        siemplify.LOGGER.exception(e)

                elif alert.md5:
                    alert.alert_link = urllib.parse.urljoin(
                        api_root, BINARY_ALERT_LINK_URL.format(alert.md5)
                    )

                case = connector.create_case_info(alert)
                existing_ids.update({alert.unique_id: case.start_time})
                is_overflow = False

                try:
                    is_overflow = siemplify.is_overflowed_alert(
                        environment=case.environment,
                        alert_identifier=str(case.ticket_id),
                        alert_name=str(case.rule_generator),
                        product=str(case.device_product),
                    )

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to detect overflow for Alert {alert.unique_id}"
                    )
                    siemplify.LOGGER.exception(e)

                if not is_overflow:
                    cases.append(case)

                else:
                    siemplify.LOGGER.warn(f"Overflowed on Alert {alert.unique_id}")

            except Exception as e:
                # Failed to build CaseInfo for alert
                siemplify.LOGGER.error(
                    f"Failed to create CaseInfo for alert {alert.unique_id}: {e}"
                )
                siemplify.LOGGER.error(f"Error Message: {e}")

                if test_handler:
                    raise e

        siemplify.LOGGER.info(f"Completed. Created {len(cases)} cases.")

        if test_handler:
            siemplify.LOGGER.info("--------- Test completed. ------------")

        elif prepared_alerts:
            siemplify.LOGGER.info(
                f"Saving new timestamp: {prepared_alerts[-1].created_time}"
            )

            siemplify.save_timestamp(
                new_timestamp=convert_string_to_unix_time(
                    prepared_alerts[-1].created_time
                )
            )

            connector.write_ids(
                os.path.join(siemplify.run_folder, IDS_FILE), existing_ids
            )

        # Return data
        siemplify.return_package(cases, {}, [])

    except Exception as e:
        siemplify.LOGGER.error(e)
        siemplify.LOGGER.exception(e)

        if test_handler:
            raise e


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
