from __future__ import annotations

import sys
import time
import uuid

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import output_handler

from ..core.FlashpointManager import FlashpointManager, dict_to_flat

DEFAULT_PRODUCT = "Flashpoint"
EVENT_TIME_FIELD = "_source_header__indexed_at"
ALERT_DESCRIPTION_FIELD = "_source_basetypes_1"
ALERT_NAME_FIELD = "_source_basetypes_1"
ALERT_ID_FIELD = "_source_id"
ALERT_WITHOUT_A_RULE_DEFAULT = "Alert has no rule."
ALERT_WITHOUT_A_NAME_DEFAULT = "Alert has no name."
ALERT_NAME_IS_EMPTY_DEFAULT = "Alert name is empty."
DAYS_IN_SECONDS = 86400


class FlashpointConnectorError(Exception):
    pass


class FlashpointConnector:
    def __init__(self, logger):
        self.logger = logger

    def create_case(self, threat, device_product_field, environment):
        """Create a case object.
        :return: {CaseInfo} Case object.
        """
        case_info = CaseInfo()
        event = {}
        event = threat
        case_info.start_time = threat.get(EVENT_TIME_FIELD)
        case_info.end_time = threat.get(EVENT_TIME_FIELD)
        case_info.rule_generator = (
            threat.get(ALERT_DESCRIPTION_FIELD) if not None else "Flashpoint"
        )
        case_info.device_product = threat.get(device_product_field, DEFAULT_PRODUCT)
        case_info.device_vendor = case_info.device_product
        case_info.priority = 60
        case_info.environment = environment
        case_info.name = (
            threat.get(ALERT_NAME_FIELD, ALERT_WITHOUT_A_NAME_DEFAULT)
            if threat.get(ALERT_NAME_FIELD)
            else ALERT_NAME_IS_EMPTY_DEFAULT
        )
        # If no Session ID, replace with timestamp + uuid because timestamp can be not unique in some cases.
        case_info.ticket_id = threat.get("_id") if not None else str(uuid.uuid4())
        case_info.display_id = case_info.identifier = case_info.ticket_id
        event["event_name"] = "Credential Sighting"
        event["start_time"] = case_info.start_time
        event["end_time"] = case_info.end_time
        event = dict((k.lower(), v) for k, v in event.items())
        case_info.events.append(event)
        return case_info


def fetch_last_saved_timestamp(connector_scope, time_now, max_days_backwards):
    last_fetched_timestamp = connector_scope.fetch_timestamp()
    last_fetched_timestamp = int(last_fetched_timestamp / 1000)
    connector_scope.LOGGER.info(
        f"****The last timestamp that was fetched is {last_fetched_timestamp}****",
    )
    if not is_test_run and last_fetched_timestamp > 0:
        if last_fetched_timestamp >= (
            time_now - (max_days_backwards * DAYS_IN_SECONDS)
        ):
            connector_scope.LOGGER.info(
                f"The last timestamp that was saved is: {last_fetched_timestamp}",
            )
        else:
            last_fetched_timestamp = time_now - (max_days_backwards * DAYS_IN_SECONDS)
            connector_scope.LOGGER.info(
                f"The last timestamp that was fetched is:{last_fetched_timestamp}",
            )
    else:
        last_fetched_timestamp = time_now - (max_days_backwards * DAYS_IN_SECONDS)
        if is_test_run:
            connector_scope.LOGGER.info(
                f"This is a test run.The timestamp is:{last_fetched_timestamp}",
            )
        else:
            connector_scope.LOGGER.info(
                f"This is a real run, there is no timestamp to fetch. The timestamp is {last_fetched_timestamp}",
            )
    return last_fetched_timestamp


@output_handler
def main(is_test_run=False):
    connector_scope = SiemplifyConnectorExecution()
    cases = []
    try:
        if is_test_run:
            connector_scope.LOGGER.info(
                " ------------ Starting Flashpoint Connector test. ------------ ",
            )
        else:
            connector_scope.LOGGER.info(
                " ------------ Starting Flashpoint Connector. ------------ ",
            )
        api_key = connector_scope.extract_connector_param(param_name="API Key")
        max_days_backwards = connector_scope.extract_connector_param(
            param_name="Max Days Back",
            input_type=int,
        )
        device_product_field = connector_scope.extract_connector_param(
            param_name="DeviceProductField",
        )
        limit = connector_scope.extract_connector_param(param_name="Limit")
        proxy_server_address = connector_scope.extract_connector_param(
            param_name="Proxy Server Address",
        )
        proxy_username = connector_scope.extract_connector_param(
            param_name="Proxy Username",
        )
        proxy_password = connector_scope.extract_connector_param(
            param_name="Proxy Password",
        )
        flashpoint_manager = FlashpointManager(
            api_key,
            proxy_server_address,
            proxy_username,
            proxy_password,
        )
        flashpoint_connector = FlashpointConnector(connector_scope.LOGGER)
        time_now = int(time.time())

        last_timestamp = fetch_last_saved_timestamp(
            connector_scope,
            time_now,
            max_days_backwards,
        )

        alert_list = flashpoint_manager.search_CCM(last_timestamp, time_now, limit)
        alert_list = alert_list["hits"]["hits"]
        if is_test_run:
            alert_list = alert_list[-10:]
        for alert in alert_list:
            try:
                case = flashpoint_connector.create_case(
                    dict_to_flat(alert),
                    device_product_field=device_product_field,
                    environment=connector_scope.context.connector_info.environment,
                )
                is_overflowed = False
                try:
                    is_overflowed = connector_scope.is_overflowed_alert(
                        environment=case.environment,
                        alert_identifier=str(case.ticket_id),
                        alert_name=str(case.rule_generator),
                        product=str(case.device_product),
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error validation connector overflow, ERROR: {err}",
                    )
                    connector_scope.LOGGER.exception(err)
                    if is_test_run:
                        raise
                if is_overflowed:
                    connector_scope.LOGGER.info(
                        f"{case.rule_generator!s}-{case.ticket_id!s}-{case.environment!s}-{case.device_product!s} found as overflow alert. Skipping.",
                    )
                else:
                    cases.append(case)
                    connector_scope.LOGGER.info(
                        f'Case with display id "{case.display_id}" was created.',
                    )
            except Exception as err:
                error_message = f"Failed creating case for alert with ID: {alert.get(ALERT_ID_FIELD)}, ERROR: {err}"
                connector_scope.LOGGER.error(error_message)
                connector_scope.LOGGER.exception(err)

        cases.sort(key=lambda x: x.start_time)
        if cases and not is_test_run:
            connector_scope.save_timestamp(cases[-1].start_time)
        if is_test_run:
            connector_scope.LOGGER.info(
                " ------------ Complete Flashpoint Compromised Credential Connector test. ------------ ",
            )
        else:
            connector_scope.LOGGER.info(
                " ------------ Complete Connector Iteration. ------------ ",
            )
        connector_scope.return_package(cases)
    except Exception as err:
        connector_scope.LOGGER.error(f"Got exception on main handler. Error: {err}")
        connector_scope.LOGGER.exception(err)
        if is_test_run:
            raise
        # This is a test


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
