from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_connector_param

# ============================================================================#
# title           :ArcsightESMConnector.py
# description     :This Module contain all Arcsight ESM connector functionality
# author          :avital@siemplify.co
# date            :26-03-2018
# python_version  :3.7
# ============================================================================#

# ============================= IMPORTS ===================================== #

import csv
import sys
import json
import os
import uuid
from soar_sdk.SiemplifyUtils import dict_to_flat
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from ..core.ArcsightManager import ArcsightManager
from ..core.exceptions import ArcsightLoginError, UnableToParseException
from soar_sdk.FileRetentionManager import FileRetentionManager
import re

# ============================== CONSTS ===================================== #
EVENT_ID_FIELD_NAME = "eventId"
CORRELATION_ID_FIELD_NAME = "event.eventId"
CORRELATION_MANAGER_RECEIPT_TIME = "event.managerReceiptTime"
ARCSIGHT_SOURCE_ENUM = "1"
RULE_GENERATOR_SEPARATOR = r"/"
CSV_EXTENTION = ".done.csv"
CORRELATION_NAME_FIELD_NAME = "#event.name"
ARCSIGHT = "arcsight"
SLICED_PATTERN = "_sliced_"
DEFAULT_DONE_FILES_RETENTION_DAYS = 3
DEFAULT_ERROR_FILES_RETENTION_DAYS = 14

DEFAULT_BLACKLIST = [
    "^Connector Raw Event Statistics$",
    "Device Receipt Time is smaller than Agent Receipt Time",
]

# ============================= CLASSES ===================================== #


class ArcsightESMConnectorException(Exception):
    """
    Arcsight ESM Connector Exception
    """

    pass


class ArcsightESMConnector:
    """
    Arcsight ESM Connector
    """

    def __init__(
        self,
        connector_scope,
        arcsight_manager,
        event_limit,
        alerts_limit,
        siemshare_path,
        device_product_field_name,
        secondary_device_product_field_name,
        environment_field_name,
        alert_custom_fields_names,
        done_retention_days=DEFAULT_DONE_FILES_RETENTION_DAYS,
        error_retention_days=DEFAULT_ERROR_FILES_RETENTION_DAYS,
    ):
        # Document what is this connector_scope and its type
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.arcsight_manager = arcsight_manager
        self.event_limit = event_limit
        self.alerts_limit = alerts_limit
        self.siemshare_path = siemshare_path
        self.error_folder = os.path.join(self.siemshare_path, "Error")
        self.done_folder = os.path.join(self.siemshare_path, "Done")
        self.sliced_folder = os.path.join(self.siemshare_path, "Slice Original")
        self.device_product_field_name = device_product_field_name
        self.secondary_device_product_field_name = secondary_device_product_field_name
        self.environment_field_name = environment_field_name
        self.map_file = os.path.join(self.connector_scope.run_folder, "map.json")
        self.blacklist_file = os.path.join(
            self.connector_scope.run_folder, "blacklist.json"
        )
        self.alert_custom_fields_names = alert_custom_fields_names
        self.done_retention_hours = (
            int(done_retention_days) * 24
        )  # Convert days into hours
        self.error_retention_hours = (
            int(error_retention_days) * 24
        )  # Convert days into hours

        self.retention_manager = FileRetentionManager(self.logger)

        try:
            # Make Done folder if doesn't exist
            if not os.path.exists(self.done_folder):
                os.makedirs(self.done_folder)
        except Exception as e:
            self.logger.error(f"Unable to create Done folder: {str(e)}")
            self.logger.exception(e)

        try:
            # Make Error folder if doesn't exist
            if not os.path.exists(self.error_folder):
                os.makedirs(self.error_folder)
        except Exception as e:
            self.logger.error(f"Unable to create Error folder: {str(e)}")
            self.logger.exception(e)

        try:
            # Make Sliced Original folder if doesn't exist
            if not os.path.exists(self.sliced_folder):
                os.makedirs(self.sliced_folder)
        except Exception as e:
            self.logger.error(f"Unable to create Sliced Original folder: {str(e)}")
            self.logger.exception(e)

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
                        f"Mapping file was created at {self.map_file}"
                    )
        except Exception as e:
            self.logger.error(f"Unable to create mapping file: {str(e)}")
            self.logger.exception(e)

        try:
            if not os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, "w+") as blacklist_file:
                    blacklist_file.write(json.dumps(DEFAULT_BLACKLIST))
                    self.connector_scope.LOGGER.info(
                        f"Blacklist file was created at {self.blacklist_file}"
                    )
        except Exception as e:
            self.logger.error(f"Unable to create blacklist file: {str(e)}")
            self.logger.exception(e)

        try:
            with open(self.blacklist_file, "r+") as blacklist_file:
                self.blacklist = json.loads(blacklist_file.read())
        except Exception as e:
            self.logger.error(
                "Unable to read blacklist. Default blacklist will be used."
            )
            self.logger.exception(e)
            self.blacklist = DEFAULT_BLACKLIST

    def is_blacklisted(self, correlation_name):
        """
        Check if a correlation name is blacklisted
        :param correlation_name: {str} The name of the correlation
        :return:
        """
        for blacklist_pattern in self.blacklist:
            pattern = re.compile(blacklist_pattern)
            if pattern.search(correlation_name):
                return blacklist_pattern

    def parse_csv(self, csv_file):
        """
        Parse a csv
        :param csv_file: {str} The path to the csv
        :return: {[dict]} List of found correlations (dicts)
        """
        self.logger.info(f"Parsing {csv_file}")

        correlations_list = []
        correlations = []

        # Read csv line by line
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                correlations_list.append(row)

        # Check if there are any correlations (first row is headers row)
        if len(correlations_list) <= 1:
            # No correlations were found in csv
            return []

        # Construct human readable correlation objects (using headers and info)
        for correlation in correlations_list[1:]:
            correlation_info = {}
            for i, item in enumerate(correlation):
                # Construct Arcsight alert info dict
                correlation_info[correlations_list[0][i]] = item
            # Append alert info dict to alerts list
            correlation_info["raw"] = ",".join(correlation)
            correlations.append(correlation_info)

        return correlations

    @staticmethod
    def create_csv(save_path, correlations):
        """
        Create a new csv with given correlations at given path
        :param save_path: {str} The path to save the csv at
        :param correlations: {list} The list of correlations to save
        :return:
        """
        # Remove the raw field from the correlations
        for correlation in correlations:
            if "raw" in correlation:
                del correlation["raw"]

        # Write the csv
        with open(save_path, "w") as output_file:
            dict_writer = csv.DictWriter(output_file, correlations[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(correlations)

    def get_first_correlation(self, correlation_id, events):
        """
        Find the event that has matching Id to the given correlation_id
        :param correlation_id: {int} The id to search for
        :param events: {[dict]} List of event info dicts.
        :return: {dict} The found event
        """
        for event in events:
            if event.get(EVENT_ID_FIELD_NAME) == correlation_id:
                return event

    def split_large_csv_file(self, csv_file):
        """
        Split a large csv to multiple smaller csvs files, save the original csv in the sliced_file_name
        :param csv_file: {str} The path of the csv file
        """
        arcsight_correlations = self.parse_csv(
            os.path.join(self.siemshare_path, csv_file)
        )
        # Split correlations list into sub lists under the limit restrictions
        correlations_chunks = [
            arcsight_correlations[i : i + self.alerts_limit]
            for i in range(0, len(arcsight_correlations), self.alerts_limit)
        ]

        self.logger.info(
            f"Creating {len(correlations_chunks)} sliced file from {csv_file}"
        )
        for correlations_chunk in correlations_chunks:
            sliced_file_name = f"{csv_file.split(CSV_EXTENTION)[0]}{SLICED_PATTERN}{uuid.uuid4().hex}{CSV_EXTENTION}"

            self.logger.info(f"Creating sliced file - {sliced_file_name}")
            self.create_csv(
                os.path.join(self.siemshare_path, sliced_file_name), correlations_chunk
            )

        try:
            # Backup the original file to Sliced Originals folder
            self.retention_manager.retensify_file(
                os.path.join(self.siemshare_path, csv_file),
                self.sliced_folder,
                self.error_retention_hours,
            )
        except Exception as e:
            self.logger.error(f"Could not move {csv_file} to sliced folder")
            raise

    def get_arcsight_alerts(self, test_run):
        """
        Get Arcsight alerts
        :return: {[CaseInfo]} List of CaseInfos.
        """
        alerts = []
        count = 0
        logged_in = False

        # Iterate files in SiemShare folder
        for csv_file in os.listdir(self.siemshare_path):
            try:
                if csv_file.endswith(CSV_EXTENTION):
                    # Process only files with .done.csv extension.
                    self.logger.info(f"Parsing {csv_file}")

                    try:
                        # Parse the csv file
                        arcsight_correlations = self.parse_csv(
                            os.path.join(self.siemshare_path, csv_file)
                        )

                        # Validate file size limit
                        if len(arcsight_correlations) > self.alerts_limit:
                            self.logger.info(
                                f"Current csv file contains {len(arcsight_correlations)}"
                            )
                            self.logger.info(f"Splitting {csv_file}")
                            self.split_large_csv_file(csv_file)

                    except Exception:
                        done_folder = FileRetentionManager.create_retention_folder_name(
                            self.done_folder
                        )
                        # Check if the file was already moved to the Done folder
                        if os.path.exists(
                            os.path.join(
                                done_folder,
                                os.path.basename(
                                    os.path.join(self.siemshare_path, csv_file)
                                ),
                            )
                        ):
                            self.logger.info(
                                'File "{}" wasn\'t found in the Cases folder: "{}" but was found in the Done folder: "{}" '
                                "continuing...".format(
                                    os.path.join(self.siemshare_path, csv_file),
                                    self.siemshare_path,
                                    done_folder,
                                )
                            )
                            continue
                        self.logger.error(f"Unable to parse csv {csv_file}.")
                        raise

                    if count + len(arcsight_correlations) > self.alerts_limit:
                        # Alerts limit reached - slice
                        self.logger.info("Reached alerts limit. stopping iteration")
                        break

                    # Start processing the csv file
                    else:
                        count += len(arcsight_correlations)
                        self.logger.info(f"Processing {csv_file}")
                        # Initiate inner failure flag - to mark if one of the
                        # cases in the current csv has failed (to move the entire
                        # csv to errors folder)
                        inner_failure = False

                        self.logger.info(
                            f"Found {len(arcsight_correlations)} correlations."
                        )
                        # Iterate the found correlations from the csv
                        for correlation in arcsight_correlations:
                            try:
                                blacklist_pattern = self.is_blacklisted(
                                    correlation.get(CORRELATION_NAME_FIELD_NAME)
                                )

                                if blacklist_pattern:
                                    self.logger.info(
                                        f"Correlation {correlation.get(CORRELATION_ID_FIELD_NAME)} is blacklisted by rule :{blacklist_pattern}"
                                    )
                                    self.logger.info(
                                        f"Blacklisted correlation name: {correlation.get(CORRELATION_NAME_FIELD_NAME)}"
                                    )
                                    self.logger.info(
                                        f"Skipping correlation {correlation.get(CORRELATION_ID_FIELD_NAME)}"
                                    )

                                else:
                                    if not logged_in:
                                        self.arcsight_manager.login()
                                        logged_in = True

                                    is_overflow = False

                                    try:
                                        is_overflow = self.connector_scope.is_overflowed_alert(
                                            environment=self.get_mapped_environment(
                                                correlation.get(
                                                    self.environment_field_name,
                                                    self.connector_scope.context.connector_info.environment,
                                                )
                                            ),
                                            alert_identifier=str(
                                                correlation[CORRELATION_ID_FIELD_NAME]
                                            ),
                                            alert_name=str(
                                                correlation[CORRELATION_NAME_FIELD_NAME]
                                            ),
                                        )

                                    except Exception as e:
                                        self.logger.error(
                                            f"Failed to detect overflow for Alert {str(correlation[CORRELATION_NAME_FIELD_NAME])}"
                                        )
                                        self.logger.exception(e)

                                    if not is_overflow:
                                        # Generate case info for the correlation
                                        case = self.create_case_info(correlation)
                                        alerts.append(case)

                                        # In case of test run return one alert
                                        if test_run:
                                            return alerts

                                    else:
                                        self.logger.warn(
                                            f"{str( correlation[CORRELATION_NAME_FIELD_NAME] )}-{str( correlation[CORRELATION_ID_FIELD_NAME] )}-{self.get_mapped_environment( correlation.get( self.environment_field_name, self.connector_scope.context.connector_info.environment ) )} found as overflow alert, skipping this alert."
                                        )

                            except ArcsightLoginError as e:
                                raise ArcsightLoginError(
                                    f"Failed login error for given creds.\n{str(e)}. \nCheck Logs for more details."
                                )

                            except Exception as e:
                                # The correlation has failed
                                self.logger.error(
                                    f"Failed to create CaseInfo for Correlation {correlation.get(CORRELATION_ID_FIELD_NAME)}"
                                )
                                self.logger.error(f"Error Message: {str(e)}")
                                self.logger.exception(e)

                                inner_failure = True

                        if inner_failure:
                            # At least one of the inner correlations have failed -
                            # raise an exception
                            raise ArcsightESMConnectorException(
                                f"Failure occured when processing {csv_file}. Check Logs for details."
                            )

                        # Completed processing - move to Done folder
                        self.logger.info(f"Completed - {csv_file}")

                        if not test_run:
                            try:
                                # Check if the file was already moved to the Done folder
                                done_folder = (
                                    FileRetentionManager.create_retention_folder_name(
                                        self.done_folder
                                    )
                                )
                                if os.path.exists(
                                    os.path.join(
                                        done_folder,
                                        os.path.basename(
                                            os.path.join(self.siemshare_path, csv_file)
                                        ),
                                    )
                                ):
                                    self.logger.info(
                                        'File "{}" wasn\'t found in the Cases folder: "{}" but was found in the Done folder: "{}" '
                                        "continuing...".format(
                                            os.path.join(self.siemshare_path, csv_file),
                                            self.siemshare_path,
                                            done_folder,
                                        )
                                    )
                                    continue
                                self.retention_manager.retensify_file(
                                    os.path.join(self.siemshare_path, csv_file),
                                    self.done_folder,
                                    self.done_retention_hours,
                                )

                            except Exception as e:
                                self.logger.error(
                                    f"Unable to move {csv_file} to Done folder."
                                )
                                self.logger.error(str(e))
                                self.logger.exception(e)

            except ArcsightLoginError as e:
                raise

            except Exception as e:
                # Execution failed - move to error folder
                self.logger.error("Error occurred in creating alerts loop")
                self.logger.exception(e)

                if not test_run:
                    try:
                        self.retention_manager.retensify_file(
                            os.path.join(self.siemshare_path, csv_file),
                            self.error_folder,
                            self.error_retention_hours,
                        )

                    except Exception as e:
                        self.logger.error(f"Unable to move {csv_file} to Error folder.")
                        self.logger.exception(e)

        return alerts

    def get_priority_value(self, correlation):
        """
        Get priority from correlation
        :param correlation: {dict} The correlation info
        :return: {int} The maching priority (Siemplify matching)
        """
        try:
            priority = float(correlation.get("priority", -1))

            if priority in [9, 10]:
                return 100  # Critical
            elif priority in [7, 8]:
                return 80  # High
            elif priority in [5, 6]:
                return 60  # Medium
            elif priority in [3, 4]:
                return 40  # Low

        except Exception as e:
            # Exception in conversion - return Informative priority level
            self.logger.warn(
                f"Couldn't calculate priority of correlation {correlation.get(EVENT_ID_FIELD_NAME)}"
            )
            self.logger.warn(str(e))

        return -1  # Informative

    def get_rule_generator(self, value):
        """
        Get rule generator from given generator uri
        :param value: {str} generator uri field in an Arcsight event
        :return: {str} the rule generator
        """
        return value.split(RULE_GENERATOR_SEPARATOR)[-1]

    def create_case_info(self, correlation):
        """
        Get alerts from Arcsight ESM
        :param correlation: {dict} An arcsight correlation info
        :return: {list} List of the newly created alerts
        """
        correlation_id = int(correlation[CORRELATION_ID_FIELD_NAME])

        self.logger.info(f"Processing correlation {correlation_id}")

        events, error_message = self.arcsight_manager.get_security_events(
            [correlation_id], self.event_limit
        )

        if error_message:
            self.logger.error(
                f"An error occurred while fetching events: {error_message}"
            )
            self.logger.warn("Case will be created anyway with found events.")

        # Get the base correlation info from events (an event that matches
        # the given correlation_id)
        first_correlation = self.get_first_correlation(correlation_id, events)

        # Remove first correlation from events (first correlation is
        # an alert in Siemplify)
        if first_correlation in events:
            events.remove(first_correlation)

        if not first_correlation:
            # Base event was not found - case cannot be created
            self.logger.error(f"Found events: {str(events).encode().decode()}")
            raise ArcsightESMConnectorException(
                "Correlation was not found in events. Cannot create case."
            )

        self.logger.info(f"Creating Case for Arcsight Correlation {correlation_id}")

        try:
            # Create the CaseInfo
            case_info = CaseInfo()
            case_info.name = first_correlation.get("name")
            case_info.ticket_id = first_correlation[EVENT_ID_FIELD_NAME]

            try:
                rule_generator = first_correlation.get("generator", {}).get("uri", "")
            except Exception as e:
                self.logger.error(f"Unable to get rule generator: {str(e)}")
                self.logger.exception(e)
                rule_generator = ""

            case_info.rule_generator = self.get_rule_generator(rule_generator)
            case_info.display_id = first_correlation.get(EVENT_ID_FIELD_NAME)

            try:
                device_product = first_correlation.get("device", {}).get("product")
            except Exception as e:
                self.logger.error(f"Unable to get device product: {str(e)}")
                self.logger.exception(e)
                device_product = ""

            case_info.device_product = device_product

            try:
                device_vendor = first_correlation.get("device", {}).get("vendor")
            except Exception as e:
                self.logger.error(f"Unable to get device vendor: {str(e)}")
                self.logger.exception(e)
                device_vendor = ""

            case_info.device_vendor = device_vendor

            case_info.start_time = first_correlation.get("startTime", 1)
            case_info.end_time = first_correlation.get("endTime", 1)
            case_info.source_system_name = ARCSIGHT_SOURCE_ENUM
            case_info.priority = self.get_priority_value(first_correlation)
            # Take env name from given field in settings or if it is not in csv
            # take the default environment name. Then try to replace that
            # with the mappings.
            # If replacement fails stay with current env.
            case_info.environment = self.get_mapped_environment(
                correlation.get(
                    self.environment_field_name,
                    self.connector_scope.context.connector_info.environment,
                )
            )

            # Pull custom field values from ArcSight into the alert section on context details
            flat_first_correlation = dict_to_flat(first_correlation)

            if self.alert_custom_fields_names:
                for alert_custom_field_name in self.alert_custom_fields_names:
                    if flat_first_correlation.get(alert_custom_field_name):
                        case_info.extensions.update(
                            {
                                alert_custom_field_name: flat_first_correlation.get(
                                    alert_custom_field_name
                                )
                            }
                        )
                    else:
                        self.logger.error(f"{alert_custom_field_name} doesn't exist")
                if case_info.extensions:
                    try:
                        self.arcsight_manager.remove_invalid_values(
                            [case_info.extensions]
                        )
                        self.arcsight_manager.parse_ip_addresses([case_info.extensions])
                    except Exception as e:
                        self.logger.error(
                            "Unable to remove invalid values from extensions"
                        )
                        self.logger.exception(e)
        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {e}")

        # Flatten events
        flat_events = []

        for event in events:
            flat_events.append(dict_to_flat(event))

        try:
            self.arcsight_manager.remove_invalid_values(flat_events)
        except Exception as e:
            self.logger.error("Unable to remove invalid values from events")
            self.logger.exception(e)

        try:
            self.arcsight_manager.parse_ip_addresses(flat_events)
        except UnableToParseException as e:
            key = str(e.key)
            value = str(e.value)
            self.logger.info(
                f"Value - '{value}' in key '{key}' wasn't converted to the IP address"
            )

        for flat_event in flat_events:
            if (
                flat_event.get(self.device_product_field_name, "").lower() == ARCSIGHT
                and flat_event.get("device_vendor", "").lower() == ARCSIGHT
                and flat_event.get("type", "").upper() == "BASE"
            ):
                # Event is a base event - try to fetch real product
                # from secondary product field
                if flat_event.get(self.secondary_device_product_field_name):
                    # Replace the original product field (from connector's
                    # DeviceProductField settings) with the value from
                    # secondary product field
                    flat_event[self.device_product_field_name] = flat_event[
                        self.secondary_device_product_field_name
                    ]
                    self.logger.info(
                        f'Product Field was replaced in event {flat_event.get("eventId")}'
                    )

        case_info.events = flat_events

        return case_info

    def get_mapped_environment(self, original_env):
        try:
            with open(self.map_file, "r+") as map_file:
                mappings = json.loads(map_file.read())
        except Exception as e:
            self.connector_scope.LOGGER.error(
                f"Unable to read environment mappings: {str(e)}"
            )
            mappings = {}

        if not isinstance(mappings, dict):
            self.connector_scope.LOGGER.error(
                "Mappings are not in valid format. Environment will not be mapped."
            )
            return original_env

        return mappings.get(original_env, original_env)


@output_handler
def main(test_run=False):
    """
    Main execution - Arcsight ESM Connector
    """
    connector_scope = SiemplifyConnectorExecution()
    output_variables = {}
    log_items = []
    result_params = {}

    connector_scope.script_name = "Arcsight ESM Connector"
    connector_scope.LOGGER.info(
        "====================Starting Connector===================="
    )
    if test_run:
        connector_scope.LOGGER.info("====================Test====================")

    try:
        connector_scope.LOGGER.info("Connecting to Arcsight ESM")
        server_address = connector_scope.parameters.get("Server Address")
        username = connector_scope.parameters.get("Username")
        password = connector_scope.parameters.get("Password")
        verify_ssl = extract_connector_param(
            connector_scope, param_name="Verify SSL", input_type=bool
        )
        ca_certificate_file = extract_connector_param(
            connector_scope, param_name="CA Certificate File"
        )
        event_limit = int(connector_scope.parameters["Events Count Limit"])
        alerts_limit = int(connector_scope.parameters["Alerts Count Limit"])
        siemshare_path = connector_scope.parameters.get("Cases Folder Path")
        done_retention_days = int(
            connector_scope.parameters.get(
                "Done files retention days", DEFAULT_DONE_FILES_RETENTION_DAYS
            )
        )
        error_retention_days = int(
            connector_scope.parameters.get(
                "Error files retention days", DEFAULT_ERROR_FILES_RETENTION_DAYS
            )
        )

        device_product_field_name = connector_scope.parameters.get("DeviceProductField")
        secondary_device_product_field_name = connector_scope.parameters.get(
            "Secondary Device Product Field", ""
        )
        environment_field_name = connector_scope.parameters.get(
            "Environment Field Name"
        )
        alert_custom_fields_names = connector_scope.parameters.get(
            "Alert Custom Fields Names", []
        )
        alert_custom_fields_names = (
            alert_custom_fields_names.split(",") if alert_custom_fields_names else []
        )

        # Connect to Arcsight
        arcsight_manager = ArcsightManager(
            server_address,
            username,
            password,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
            logger=connector_scope.LOGGER,
        )

        arcsight_connector = ArcsightESMConnector(
            connector_scope,
            arcsight_manager,
            event_limit,
            alerts_limit,
            siemshare_path,
            device_product_field_name,
            secondary_device_product_field_name,
            environment_field_name,
            alert_custom_fields_names,
            done_retention_days=done_retention_days,
            error_retention_days=error_retention_days,
        )

        # Get alerts
        connector_scope.LOGGER.info("Collecting correlations from Arcsight ESM.")
        cases = arcsight_connector.get_arcsight_alerts(test_run=test_run)

        connector_scope.LOGGER.info(f"Completed. Found {len(cases)} cases.")

        try:
            # Logout from arcsight
            arcsight_manager.logout()
            connector_scope.LOGGER.info("Logout from Arcsight successfully")

        except Exception as e:
            connector_scope.LOGGER.error(f"Unable to logout from Arcsight: {str(e)}")
            connector_scope.LOGGER.exception(e)
            if test_run:
                raise

        connector_scope.LOGGER.info(
            "====================Connector Finished===================="
        )

        # Return data
        connector_scope.return_package(cases, output_variables, log_items)

    except ArcsightLoginError as e:
        connector_scope.LOGGER.error("Failed login error for given creds.")
        connector_scope.LOGGER.exception(e)
        raise

    except Exception as e:
        connector_scope.LOGGER.error("Error in main handler")
        connector_scope.LOGGER.exception(e)
        if test_run:
            raise


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main(test_run=False)
    else:
        print("Test execution started")
        main(test_run=True)
