from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ============================================================================#
# title           :CylanceConnector.py
# description     :This Module contain all Cylance connector functionality.
# author          :danield@siemplify.co
# date            :03-29-2018
# python_version  :2.7
# ============================================================================#

# ============================= IMPORTS ===================================== #

import sys
import pytz
import time
import logging
import uuid
import datetime
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, unix_now
from ..core.CylanceManager import CylanceManager
from soar_sdk.SiemplifyUtils import dict_to_flat

# ============================== CONSTS ===================================== #
VENDOR = PRODUCT = "CyLance"
DEFAULT_ALERT_NAME = "Risky Hash"
DEFAULT_PRIORITY = 20
CYLANCE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
CYLANCE_EVENT_DEFAULT_NAME = "Cylance Event"

# ============================= CLASSES ===================================== #


class CylanceConnectorException(Exception):
    pass


class CylanceConnector:

    def __init__(self, connector_scope, cylance_manager):  # , connector_scope)
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.cylance_manager = cylance_manager

    def retrieve_updated_threats(self, last_run_time):
        """
        Gets a list of threats that were created since the last time the connector ran
        :params last_run_time: {string} Timestamp to retrieve offenses from the timestamp to now (unix time).
        :return: {list} List of new threats
        """
        all_threats = self.cylance_manager.get_threats()
        self.logger.info(f"Found total {len(all_threats)} threats")

        new_threats = []
        for threat in all_threats:
            threat_unix_time = self.convert_to_unix_time(threat["last_found"])
            if threat_unix_time > last_run_time:
                # Threat is new - set its start and end time and add to
                # new threats list
                threat["start_time"] = threat_unix_time
                threat["end_time"] = threat_unix_time
                new_threats.append(threat)

        self.logger.info(f"Found {len(new_threats)} new threats.")
        return new_threats

    @staticmethod
    def convert_to_unix_time(timestamp):
        dt = datetime.datetime.strptime(timestamp, CYLANCE_TIME_FORMAT)
        dt = pytz.utc.localize(dt)
        return convert_datetime_to_unix_time(dt)

    def build_case_info(self, threat):
        """
        Builds CaseInfo
        :params threat: {string} threat information from Cylance
        :return: {CaseInfo} The newly created case
        """
        case_info = CaseInfo()

        self.logger.info(
            f"Build CaseInfo for threat {str(threat['name']).encode('utf-8')} - {threat['sha256']}."
        )

        self.logger.info("Fetching events.")

        events = self.cylance_manager.get_threat_devices(threat["sha256"])

        self.logger.info(f"Found {len(events)} events.")

        if not events:
            return case_info

        events.sort(
            key=lambda event: time.mktime(
                time.strptime(event["date_found"], "%Y-%m-%dT%H:%M:%S")
            )
        )

        for event in events:
            event["threat"] = threat
            event["cylance_event"] = CYLANCE_EVENT_DEFAULT_NAME

        case_info.start_time = self.convert_to_unix_time(events[0]["date_found"])
        case_info.end_time = self.convert_to_unix_time(events[-1]["date_found"])
        case_info.ticket_id = str(uuid.uuid4())
        case_info.display_id = case_info.ticket_id
        case_info.name = DEFAULT_ALERT_NAME
        case_info.rule_generator = DEFAULT_ALERT_NAME
        case_info.device_vendor = VENDOR
        case_info.device_product = PRODUCT
        case_info.priority = DEFAULT_PRIORITY

        case_info.events = [dict_to_flat(event) for event in events]
        case_info.environment = None

        return case_info

    def get_threats(self):
        """
        Get Alerts from Cylance
        :return: {list}List of new cases (CaseInfo objects)
        """
        # Get Alerts
        logging.info("Getting threats from Cylance Protect")

        last_run_time = self.connector_scope.fetch_timestamp()
        threats = self.retrieve_updated_threats(last_run_time)

        cases = []

        for threat in threats:
            try:
                self.logger.info(
                    f"Processing threat {str(threat['name']).encode('utf-8')} - {threat['sha256']}."
                )
                cases.append(self.build_case_info(threat))
            except Exception as e:
                self.logger.error(
                    f"Couldn't process threat {str(threat['name']).encode('utf-8')} - {threat['sha256']}."
                )
                self.logger.exception(e)

        self.logger.info(f"Found {len(cases)} cases.")

        return cases


@output_handler
def main():
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = "Cylance Connector"
    output_variables = {}
    log_items = []

    try:
        connector_scope.LOGGER.info("Starting Cylance Connector")

        server_address = connector_scope.parameters.get("Api Root")
        application_secret = connector_scope.parameters.get("Application Secret")
        application_id = connector_scope.parameters.get("Application ID")
        tenant_identifier = connector_scope.parameters.get("Tenant Identifier")

        # Get the current time
        now = unix_now()

        logging.info("Connecting to Cylance Protect")
        cylance_manager = CylanceManager(
            server_address, application_id, application_secret, tenant_identifier
        )

        cylance_connector = CylanceConnector(
            connector_scope, cylance_manager
        )  # connector_scope)
        connector_scope.LOGGER.info("Creating cases.")
        cases = cylance_connector.get_threats()

        connector_scope.LOGGER.info(f"Created {len(cases)} cases")
        connector_scope.LOGGER.info("Completed.")

        connector_scope.save_timestamp(new_timestamp=now)
        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as err:
        connector_scope.LOGGER.error(f"Failed to run cCylance Connector. Error: {err}")
        connector_scope.LOGGER.exception(err)


def Test():
    connector_scope = SiemplifyConnectorExecution()
    output_variables = {}
    log_items = []
    connector_scope.script_name = "Cylance Connector"

    connector_scope.LOGGER.info("Starting Cylance Connector")

    server_address = connector_scope.parameters.get("Api Root")
    application_secret = connector_scope.parameters.get("Application Secret")
    application_id = connector_scope.parameters.get("Application ID")
    tenant_identifier = connector_scope.parameters.get("Tenant Identifier")

    connector_scope.LOGGER.info("Connecting to Cylance Protect")
    cylance_manager = CylanceManager(
        server_address, application_id, application_secret, tenant_identifier
    )

    cylance_connector = CylanceConnector(
        connector_scope, cylance_manager
    )  # connector_scope)
    connector_scope.LOGGER.info("Creating cases.")
    cases = cylance_connector.get_threats()

    connector_scope.LOGGER.info(f"Created {len(cases)} cases.")
    connector_scope.LOGGER.info("Completed.")

    connector_scope.return_package(cases, output_variables, log_items)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main()
    else:
        print("Test execution started")
        Test()
