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
import datetime
import json
import sys
from ..core.ElasticsearchManager import ElasticsearchManager
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyUtils import utc_now, convert_string_to_unix_time
from TIPCommon import (
    extract_connector_param,
    unix_now,
    is_overflowed,
    read_ids,
    write_ids,
)
from ..core.UtilsManager import (
    load_custom_severity_configuration,
    map_severity_value,
    get_field_value,
    DEFAULT_SEVERITY_VALUE,
)

# ============================== CONSTS ===================================== #
DEFAULT_VENDOR = "ElasticSearch"
SCRIPT_NAME = "ElasticSerach DSL Connector"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
ALERTS_LIMIT = 20
DEFAULT_DAYS_BACKWARDS = 3
TIMEZONE = "UTC"
NON_SOURCE_FIELDS = ["_id", "_index", "_score", "_type"]

ALERT_LOW_SEVERITY = "LOW"
SEVERITY_MAP = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}
STORED_ALERT_IDS_LIMIT = 5000

# ============================= CLASSES ===================================== #


class ElasticSearchDSLConnectorException(Exception):
    """
    ElasticSearch Exception
    """

    pass


class ElasticSearchDSLConnector:
    """
    ElasticSearch Connector
    """

    def __init__(
        self,
        connector_scope,
        elastic_manager,
        device_product_field_name,
        event_class_id_field_name,
        alert_name_field,
        timestamp_field_name,
        alert_description_field,
        alert_severity,
        environment_common,
        environment_field_name,
    ):
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.elastic_manager = elastic_manager
        self.device_product_field_name = device_product_field_name
        self.event_class_id_field_name = event_class_id_field_name
        self.alert_name_field = alert_name_field
        self.timestamp_field_name = timestamp_field_name
        self.alert_description_field = alert_description_field
        self.alert_severity = alert_severity
        self.environment_common = environment_common
        self.environment_field_name = environment_field_name

    @staticmethod
    def validate_timestamp(last_run_timestamp, offset):
        """
        Validate timestamp in range
        :param last_run_timestamp: {datetime} last run timestamp
        :param offset: {datetime} last run timestamp
        :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
        """
        current_time = utc_now()
        # Check if first run
        if current_time - last_run_timestamp > datetime.timedelta(days=offset):
            return current_time - datetime.timedelta(days=offset)
        else:
            return last_run_timestamp

    def get_alerts(
        self,
        connector_start_time,
        python_process_timeout,
        existing_ids,
        indexes=None,
        query=None,
        alerts_count_limit=ALERTS_LIMIT,
    ):
        """
        Fetch alerts from ElasticSearch
        :return: {list} List of found alerts
        """
        all_alerts, total_hits = self.elastic_manager.dsl_search(
            indexes,
            query,
            alerts_count_limit,
            existing_ids,
            connector_start_time,
            python_process_timeout,
        )

        return sorted(
            all_alerts,
            key=lambda alert: get_field_value(
                alert.to_flat(), self.timestamp_field_name, "0"
            ),
        )

    def create_case_info(
        self, flat_alert, indexes, query, environment_regex_pattern, severity_field_name
    ):
        """
        Create CaseInfo object from ElasticSearch alert
        :param flat_alert: {dict} An ES flattened alert
        :param indexes: {str} The indexes to search by
        :param query: {str} The search query to search by
        :param environment_regex_pattern: {str} The regex pattern to extract environment from the environment field
        :param severity_field_name: {str} Name of severity field
        :return: {CaseInfo} The newly created case
        """
        self.logger.info(f"Creating Case for Alert {flat_alert['_id']}")

        try:
            # Create the CaseInfo
            case_info = CaseInfo()

            name = get_field_value(flat_alert, self.alert_name_field, "")
            case_info.name = name
            case_info.ticket_id = flat_alert["_id"]

            case_info.rule_generator = name
            case_info.display_id = flat_alert["_id"]
            case_info.device_vendor = DEFAULT_VENDOR

            case_info.device_product = get_field_value(
                flat_alert, self.device_product_field_name, ""
            )
            flat_alert[self.event_class_id_field_name] = get_field_value(
                flat_alert, self.event_class_id_field_name, ""
            )

            try:
                alert_time = convert_string_to_unix_time(
                    get_field_value(flat_alert, self.timestamp_field_name)
                )
            except Exception as e:
                self.logger.error(f"Unable to get alert time: {e}")
                self.logger.exception(e)
                alert_time = 1

            case_info.start_time = alert_time
            case_info.end_time = alert_time

            flat_alert[self.environment_field_name] = get_field_value(
                flat_alert, self.environment_field_name, ""
            )
            case_info.environment = self.environment_common.get_environment(flat_alert)

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {e}")

        case_info.events = [flat_alert]
        case_info.extensions.update({"ES Index": indexes, "ES Query": query})
        case_info.description = get_field_value(
            flat_alert, self.alert_description_field, ""
        )
        if self.alert_severity:
            case_info.priority = self.alert_severity
        else:
            case_info.priority = map_severity_value(
                severity_field_name,
                get_field_value(
                    flat_alert, severity_field_name, DEFAULT_SEVERITY_VALUE
                ),
            )
        return case_info


@output_handler
def main(test=False):
    """
    Main execution - ElasticSearch Connector
    """
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = SCRIPT_NAME
    output_variables = {}
    log_items = []
    connector_start_time = unix_now()

    if test:
        connector_scope.LOGGER.info("Starting Connector Test.")
        connector_scope.LOGGER.info("Testing connection to ElasticSearch")

    else:
        connector_scope.LOGGER.info("Starting Connector.")
        connector_scope.LOGGER.info("Connecting to ElasticSearch")

    try:
        server_address = extract_connector_param(
            connector_scope, param_name="Server Address", input_type=str
        )
        username = extract_connector_param(
            connector_scope, param_name="Username", input_type=str
        )
        password = extract_connector_param(
            connector_scope, param_name="Password", input_type=str
        )

        authenticate = extract_connector_param(
            connector_scope, param_name="Authenticate", input_type=bool
        )
        verify_ssl = extract_connector_param(
            connector_scope, param_name="Verify SSL", input_type=bool
        )
        ca_certificate_file = extract_connector_param(
            connector_scope, param_name="CA Certificate File", input_type=str
        )

        python_process_timeout = extract_connector_param(
            connector_scope,
            param_name="PythonProcessTimeout",
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )

        device_product_field_name = extract_connector_param(
            connector_scope, param_name="DeviceProductField", input_type=str
        )
        event_class_id_field_name = extract_connector_param(
            connector_scope, param_name="EventClassId", input_type=str
        )
        alert_name_field = extract_connector_param(
            connector_scope, param_name="Alert Field Name", input_type=str
        )
        alert_description_field = extract_connector_param(
            connector_scope, param_name="Alert Description Field", input_type=str
        )
        alert_severity = extract_connector_param(
            connector_scope, param_name="Alert Severity", input_type=str
        )

        if alert_severity:
            if alert_severity.upper() in SEVERITY_MAP:
                alert_severity = SEVERITY_MAP[alert_severity.upper()]
            else:
                raise ElasticSearchDSLConnectorException(
                    "Alert Severity isn't valid value"
                )

        timestamp_field_name = extract_connector_param(
            connector_scope, param_name="Timestamp Field", input_type=str
        )
        environment_field_name = extract_connector_param(
            connector_scope, param_name="Environment Field Name", input_type=str
        )
        environment_regex_pattern = extract_connector_param(
            connector_scope, param_name="Environment Regex Pattern", input_type=str
        )
        index = extract_connector_param(
            connector_scope, param_name="Index", input_type=str
        )
        query = extract_connector_param(
            connector_scope, param_name="Query", input_type=str
        )

        try:
            json.loads(query)
        except:
            raise ElasticSearchDSLConnectorException("Provide valid json for query")

        alerts_count_limit = extract_connector_param(
            connector_scope, param_name="Alerts Count Limit", input_type=int
        )

        # Connect to ElasticSearch
        if authenticate:
            elastic_manager = ElasticsearchManager(
                server_address,
                username,
                password,
                verify_ssl=verify_ssl,
                ca_certificate_file=ca_certificate_file,
                siemplify=connector_scope,
            )
        else:
            elastic_manager = ElasticsearchManager(
                server_address,
                verify_ssl=verify_ssl,
                ca_certificate_file=ca_certificate_file,
                siemplify=connector_scope,
            )

        existing_ids = read_ids(siemplify=connector_scope)

        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            connector_scope, environment_field_name, environment_regex_pattern
        )

        elastic_connector = ElasticSearchDSLConnector(
            connector_scope,
            elastic_manager,
            device_product_field_name,
            event_class_id_field_name,
            alert_name_field,
            timestamp_field_name,
            alert_description_field,
            alert_severity,
            environment_common,
            environment_field_name,
        )

        severity_field_name = extract_connector_param(
            connector_scope, param_name="Severity Field Name", input_type=str
        )

        load_custom_severity_configuration(connector_scope, severity_field_name)

        # Get alerts from ElasticSearch
        if test:
            connector_scope.LOGGER.info("Trying to fetch alerts.")
        else:
            connector_scope.LOGGER.info("Collecting alerts from ElasticSearch.")

        alerts = elastic_connector.get_alerts(
            connector_start_time=connector_start_time,
            python_process_timeout=python_process_timeout,
            existing_ids=existing_ids,
            indexes=index,
            query=query,
            alerts_count_limit=alerts_count_limit,
        )

        if test:
            alerts = alerts[:1]

        # Construct CaseInfo from alerts
        cases = []
        all_cases = []

        for alert in alerts:
            try:
                flat_alert = alert.to_flat()
                try:
                    alert_name = get_field_value(flat_alert, alert_name_field)
                except Exception as e:
                    connector_scope.LOGGER.error(f"Unable to get rule name: {e}")
                    connector_scope.LOGGER.exception(e)
                    alert_name = ""

                connector_scope.LOGGER.info(f"Processing alert {alert.alert_id}: ")

                case = elastic_connector.create_case_info(
                    flat_alert,
                    index,
                    query,
                    environment_regex_pattern,
                    severity_field_name,
                )
                all_cases.append(case)
                existing_ids.append(alert.alert_id)

                if is_overflowed(connector_scope, case, test):
                    connector_scope.LOGGER.info(
                        f"{str(case.rule_generator)}-{str(case.ticket_id)}-{str(case.environment)}-{str(case.device_product)} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                cases.append(case)
            except Exception as e:
                # Failed to build CaseInfo for alert
                connector_scope.LOGGER.error(
                    f"Failed to create CaseInfo for alert {alert.alert_id}: {e}"
                )
                connector_scope.LOGGER.error(f"Error Message: {e}")
                if test:
                    raise

        connector_scope.LOGGER.info(
            f"Found total {len(all_cases)} cases, non-overflowed cases: {len(cases)}"
        )

        if test:
            if len(all_cases) != len(alerts):
                connector_scope.LOGGER.error(
                    "Failed to create cases for some alerts. Check logs for details."
                )

            else:
                connector_scope.LOGGER.info(
                    "Successfully constructed CaseInfo for all alerts."
                )

            connector_scope.LOGGER.info("Test completed.")
            connector_scope.return_package(cases, output_variables, log_items)
            return

        # Set the new timestamp
        write_ids(
            connector_scope, ids=existing_ids, stored_ids_limit=STORED_ALERT_IDS_LIMIT
        )

        # Return data
        connector_scope.LOGGER.info(f"Completed. Total {len(cases)} cases created.")
        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as e:
        connector_scope.LOGGER.error(e)
        connector_scope.LOGGER.exception(e)
        if test:
            raise


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main(test=False)
    else:
        print("Test execution started")
        main(test=True)
