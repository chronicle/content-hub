from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ==============================================================================
# title           :TenableSecurityCenterConnection.py
# description     :This Module contain Tenabl eSecurity Center Connection Connector logic.
# author          : -
# date            : -
# python_version  :2.7
# libraries       : -
# requirements    : -
# Product Version: -

# ==============================================================================
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from ..core.TenableManager import TenableSecurityCenterManager
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict_keys,
    convert_datetime_to_unix_time,
    utc_now,
)
import uuid
import re
import sys
from ..core.UtilsManager import get_last_success_time, get_days_back, read_offset, write_offset
from ..core.constants import UNIX_FORMAT, DAY_IN_MILLISECONDS


# ============================== CONSTS ===================================== #
IGNORED_LIST_OF_SEVERITIES = ["Low", "Info"]
DEVICE_VENDOR = "Tenable"
DEVICE_PRODUCT = "Security Center"
RULE_GENERATOR = "Vulnerabilities"
CVE_REGEX = "(?<=CVE:)[^,]*"


# ============================== CLASSES ==================================== #
class TenableConnector:
    def __init__(self, connector_scope, tenable_manager):
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.tenable_manager = tenable_manager

    def get_alerts(self, test=False, days_back=1, start_offset=0, limit=10):
        """
        Get alerts from tenable and generate CaseInfos
        :param test: {bool} Specifies if connector running in test mode or no
        :param days_back: Specifies the amount of days back for fetching data.
        :param start_offset: Specifies the start offset for fetching data.
        :param limit: The limit for results
        :return: {tuple} The new cases (CaseInfo), Number of results
        """
        self.logger.info("Collecting alerts")
        vulnerabilities = self.tenable_manager.get_vulnerabilities(
            days_ago=days_back, start_offset=start_offset, limit=limit
        )
        self.logger.info(f"Found {len(vulnerabilities)} vulnerabilities.")

        cases = []

        for vulnerability in vulnerabilities:
            try:
                self.logger.info(f"Processing vulnerability: {vulnerability['name']}")
                if vulnerability["severity"] in IGNORED_LIST_OF_SEVERITIES:
                    # Vulnerability not relevant - skip vulnerability
                    self.logger.info(
                        f"Vulnerability's severity is ignored ({vulnerability['severity']}). Skipping vulnerability."
                    )
                    continue

                plugin_info = self.tenable_manager.get_plugin_info(
                    vulnerability["pluginID"]
                )
                plugin_info = add_prefix_to_dict_keys(plugin_info, "plugin")
                vulnerability.update(plugin_info)

                case_info = self.build_case_info(vulnerability)
                cases.append(case_info)

            except Exception as e:
                # The correlation has failed
                self.logger.error(
                    f"Failed to process  vulnerability{vulnerability['name']}"
                )

                self.logger.exception(e)

                if test:
                    raise

        return cases, len(vulnerabilities)

    def build_case_info(self, vulnerability):
        """
        Build a CaseInfo from a vulnerability
        :param vulnerability: {dict} The vulnerability
        :return: {CaseInfo} The new CaseInfo
        """
        self.logger.info(f"Building CaseInfo for {vulnerability['name']}")
        try:
            case_info = CaseInfo()
            case_info.name = vulnerability["name"]
            case_info.identifier = str(uuid.uuid4())
            case_info.ticket_id = case_info.identifier
            case_info.device_vendor = DEVICE_VENDOR
            case_info.device_product = DEVICE_PRODUCT
            case_info.display_id = case_info.identifier
            case_info.rule_generator = RULE_GENERATOR
            case_info.environment = (
                self.connector_scope.context.connector_info.environment
            )
            case_info.start_time = convert_datetime_to_unix_time(utc_now())
            case_info.end_time = case_info.start_time

            pattern = re.compile(CVE_REGEX)
            cves = pattern.findall(vulnerability["plugin_xrefs"])

            for index, cve in enumerate(cves):
                vulnerability[f"CVE_{index}"] = cve

            # Inject device vendor & product to event
            vulnerability["device_vendor"] = DEVICE_VENDOR
            vulnerability["device_product"] = DEVICE_PRODUCT

            case_info.events = [dict_to_flat(vulnerability)]

            return case_info

        except KeyError as e:
            raise KeyError(f"Missing mandatory key: {str(e)}")


@output_handler
def main(test_handler=False):
    connector_scope = SiemplifyConnectorExecution()
    output_variables = {}
    log_items = []

    connector_scope.script_name = "Tenable Connector"
    if test_handler:
        connector_scope.LOGGER.info("Starting Connector Test")
    else:
        connector_scope.LOGGER.info("Starting Connector")

    try:
        connector_scope.LOGGER.info("Connecting to Tenable")
        server_address = connector_scope.parameters.get("Server Address")
        username = connector_scope.parameters.get("Username")
        password = connector_scope.parameters.get("Password")
        access_key = connector_scope.parameters.get("Access Key")
        secret_key = connector_scope.parameters.get("Secret Key")
        use_ssl = connector_scope.parameters["Use SSL"].lower() == "true"
        days_back = int(connector_scope.parameters.get("Max Days Backwards") or 1)
        limit = int(connector_scope.parameters.get("Limit Per Cycle") or 10)

        tenable_manager = TenableSecurityCenterManager(
            server_address,
            username,
            password,
            access_key,
            secret_key,
            use_ssl,
        )

        tenable_connector = TenableConnector(connector_scope, tenable_manager)
        last_run_timestamp = get_last_success_time(
            siemplify=connector_scope,
            offset_with_metric={"days": days_back},
            time_format=UNIX_FORMAT,
        )
        start_offset = read_offset(connector_scope)
        days_ago = get_days_back(last_run_timestamp)

        connector_scope.LOGGER.info(
            f"Querying {days_ago - 1 if days_ago >= 1 else 0}-{days_ago if days_ago >= 0 else 0} days ago, offsets {start_offset}-{start_offset + limit}"
        )
        cases, number_of_results = tenable_connector.get_alerts(
            test=test_handler,
            days_back=days_ago,
            start_offset=start_offset,
            limit=limit,
        )
        connector_scope.LOGGER.info(f"Completed. Found {len(cases)} cases.")

        if number_of_results < limit:
            updated_offset = 0 if days_ago >= 2 else start_offset + number_of_results
            updated_days_back = (
                last_run_timestamp + DAY_IN_MILLISECONDS
                if days_ago >= 2
                else last_run_timestamp
            )
        else:
            updated_offset = start_offset + limit
            updated_days_back = last_run_timestamp

        if not test_handler:
            write_offset(connector_scope, updated_offset)
            connector_scope.save_timestamp(new_timestamp=updated_days_back)

        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as e:
        connector_scope.LOGGER.error(e)
        connector_scope.LOGGER.exception(e)
        if test_handler:
            raise


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main()
    else:
        print("Test execution started")
        main(test_handler=True)
