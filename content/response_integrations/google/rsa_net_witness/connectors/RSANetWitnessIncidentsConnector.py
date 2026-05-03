from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ==============================================================================
# title           :RSA Incidents Connector.py
# description     :This Module contain RSA Connector logic.
# author          :victor@siemplify.co
# date            :06-08-18
# python_version  :2.7
# libraries       : -
# requirements    :
# product_version : 11.1.0.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from ..core.RSAManager import RSA
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    convert_unixtime_to_datetime,
    convert_string_to_unix_time,
)
import arrow
import uuid
import sys

# =====================================
#             CONSTANTS               #
# =====================================

DEFAULT_TIME_FIELD = "time"
DEFAULT_PRODUCT = "RSA NetWitness"
TIME_UNIXTIME_FIELD = "time_unixtime"
DEFAULT_ALERT_NAME_FIELD = "title"
DEFAULT_MAX_DAYS_BACKWARDS = 1
DEFAULT_INCIDENTS_COUNT = 10


# =====================================
#              CLASSES                #
# =====================================
class RSAIncidentsConnectorException(Exception):
    """
    RSA Incidents Connector Exception
    """

    pass


class RSAIncidentsConnector:
    """
    RSA Incidents Connector
    """

    @staticmethod
    def validate_timestamp(unixtime_timestamp, max_days_backwards=1):
        """
        Adjust timestamp to the max days backwards value.
        :param unixtime_timestamp: {long} unix time timestamp.
        :param max_days_backwards: {int} days backwards to check timestamp.
        :return: {long} unixtime timestamp
        """
        # Calculate max time with offset.
        offset_unixtime_milliseconds = (
            arrow.utcnow().shift(days=-max_days_backwards).timestamp * 1000
        )

        if unixtime_timestamp <= offset_unixtime_milliseconds:
            return offset_unixtime_milliseconds
        return unixtime_timestamp

    @staticmethod
    def create_case(
        alert,
        alert_events,
        device_product_field,
        rule_generator_field,
        event_time_field,
        environment,
    ):
        """
        Create case object.
        :param alert: {dict} RSA NetWitness alert object.
        :param alert_events: {list} List of alert events objects.
        :param device_product_field: {string} The field at the event that holds the device product value.
        :param rule_generator_field: {string} The field at the event that holds the rule generator value.
        :param event_time_field: {string} The field at the event that holds the event time value.
        :param environment: {string} The field at the event that holds the environment value.
        :return: {CaseInfo} Case object.
        """

        # Sort Events.
        alert_events.sort(key=lambda x: x.get(event_time_field))

        # Add unixtime milliseconds field to each event for mapping reasons.
        for event in alert_events:
            event[TIME_UNIXTIME_FIELD] = (
                event.get(event_time_field) * 1000 if event.get(event_time_field) else 1
            )
        case_info = CaseInfo()
        if alert_events:
            case_info.start_time = (
                alert_events[0].get(event_time_field) * 1000
                if alert_events[0].get(event_time_field)
                else 1
            )
            case_info.end_time = (
                alert_events[-1:][0].get(event_time_field) * 1000
                if alert_events[-1:][0].get(event_time_field)
                else 1
            )
            case_info.rule_generator = alert_events[0].get(
                rule_generator_field, "No rule generator field found."
            )
            case_info.device_product = alert_events[0].get(
                device_product_field, DEFAULT_PRODUCT
            )

        case_info.device_vendor = case_info.device_product
        case_info.environment = environment

        case_info.name = alert.get(DEFAULT_ALERT_NAME_FIELD, "Alert has no name.")
        # If no Session ID, replace with timestamp + uuid because timestamp can be not unique in some cases.
        case_info.ticket_id = alert.get(
            "id", f"{case_info.start_time}_{str(uuid.uuid4())}"
        )
        case_info.display_id = case_info.identifier = case_info.ticket_id

        case_info.events = list(map(dict_to_flat, alert_events))

        return case_info


@output_handler
def main_handler(test_handler=False):
    """
    :param test_handler: run test flow of real flow (timestamp updating is the differencee)
    :return:
    """
    connector_scope = SiemplifyConnectorExecution()
    output_variables = {}
    log_items = []
    cases = []
    is_overflowed = False

    try:

        if test_handler:
            connector_scope.LOGGER.info(
                " ------------ Starting RSA  Connector test. ------------ "
            )
        else:
            connector_scope.LOGGER.info(
                " ------------ Starting Connector. ------------ "
            )
        ui_uri = connector_scope.parameters.get("UI URI")
        concentrator_uri = connector_scope.parameters.get("Concentrator URI")
        decoder_uri = connector_scope.parameters.get("Decoder URI")
        username = connector_scope.parameters.get("Username")
        password = connector_scope.parameters.get("Password")
        device_product_field = connector_scope.parameters.get("DeviceProductField")
        rule_generator_field = connector_scope.parameters.get("Rule Generator Field")
        incidents_count_limit = int(
            connector_scope.parameters.get(
                "Incidents Count Limit", DEFAULT_INCIDENTS_COUNT
            )
        )
        max_days_backwards = int(
            connector_scope.parameters.get(
                "Max Days Backwards", DEFAULT_MAX_DAYS_BACKWARDS
            )
        )
        event_time_field = connector_scope.parameters.get(
            "Event Time Field", DEFAULT_TIME_FIELD
        )
        verify_ssl = (
            connector_scope.parameters.get("Verify SSL", "false").lower() == "true"
        )

        rsa_manager = RSA(
            ui_uri=ui_uri,
            concentrator_uri=concentrator_uri,
            decoder_uri=decoder_uri,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        rsa_connector = RSAIncidentsConnector()

        alerts = []

        # Fetch last event time from the timestamp file.
        last_event_time = rsa_connector.validate_timestamp(
            connector_scope.fetch_timestamp(), max_days_backwards
        )

        incidents = rsa_manager.get_incident_in_time_range(
            from_time=convert_unixtime_to_datetime(last_event_time)
        )
        connector_scope.LOGGER.info(
            f'Fetched {len(incidents)} incidents since {last_event_time}, incidents IDs: {", ".join([incident.get("id") for incident in incidents])}'
        )

        # Incidents are received sorted.
        limited_incidents = (
            incidents[-1:] if test_handler else incidents[-incidents_count_limit:]
        )

        connector_scope.LOGGER.info(
            f'After slicing left incidents with IDs: {", ".join([incident.get("id") for incident in limited_incidents])}'
        )

        for incident in limited_incidents:
            try:
                alerts.extend(
                    rsa_manager.fetch_alerts_for_incident_by_id(incident.get("id"))
                )
            except Exception as err:
                error_message = f"Error occurred fetching alerts for incident with ID '{incident.get('id')}', Error: {err}"
                connector_scope.LOGGER.error(error_message)
                connector_scope.LOGGER.exception(err)
                if test_handler:
                    raise RSAIncidentsConnectorException(error_message)

        for alert in alerts:
            events_session_ids = [
                event.get("eventSourceId")
                for event in alert.get("events", [])
                if event.get("eventSourceId")
            ]
            alert_events = []
            for session_id in events_session_ids:
                try:
                    connector_scope.LOGGER.info(
                        f'Fetching event for session ID "{session_id}"'
                    )
                    alert_events.append(
                        rsa_manager.get_metadata_from_session_id(session_id)
                    )
                except Exception as err:
                    error_message = f"Error occurred fetching event for session ID '{session_id}', Error: {err}"
                    connector_scope.LOGGER.error(error_message)
                    connector_scope.LOGGER.exception(err)
                    if test_handler:
                        raise RSAIncidentsConnectorException(error_message)
            try:
                case = rsa_connector.create_case(
                    alert,
                    alert_events,
                    device_product_field,
                    rule_generator_field,
                    event_time_field,
                    connector_scope.context.connector_info.environment,
                )

                # Check if overflowed.
                try:
                    is_overflowed = connector_scope.is_overflowed_alert(
                        environment=case.environment,
                        alert_identifier=str(case.ticket_id),
                        alert_name=str(case.rule_generator),
                        product=str(case.device_product),
                    )

                except Exception as err:
                    connector_scope.LOGGER.err(
                        f"Error validation connector overflow, ERROR: {str(err)}"
                    )
                    connector_scope.LOGGER.exeption(err)

                if is_overflowed:
                    connector_scope.LOGGER.info(
                        f"{str(case.rule_generator)}-{str(case.ticket_id)}-{str(case.environment)}-{str(case.device_product)} found as overflow alert. Skipping."
                    )
                else:
                    cases.append(case)
                    connector_scope.LOGGER.info(
                        f'Case with display id "{case.display_id}" was created.'
                    )

            except Exception as err:
                error_message = f"Error occurred creating case for alert with ID '{alert.get('id')}' amd title '{alert.get('title')}', Error: {err}"
                connector_scope.LOGGER.error(error_message)
                connector_scope.LOGGER.exception(err)
                if test_handler:
                    raise RSAIncidentsConnectorException(error_message)

        if not test_handler:
            if limited_incidents:
                # Sort incidents by time.
                limited_incidents.sort(
                    key=lambda x: convert_string_to_unix_time(x.get("created"))
                )
                # Take the last incident and save it's creation time.
                # Add additional second to the final time in order to not fetch the incident that was fetched earlier.
                connector_scope.save_timestamp(
                    new_timestamp=convert_string_to_unix_time(
                        limited_incidents[-1:][0].get("created")
                    )
                    + 1000
                )

        connector_scope.LOGGER.info(
            " ------------ Connector Finished Iteration ------------ "
        )

        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as err:
        error_message = f"Got exception on main handler. Error: {err}"
        if test_handler:
            raise RSAIncidentsConnectorException(error_message)
        connector_scope.LOGGER.error(error_message)
        connector_scope.LOGGER.exception(err)


@output_handler
def test():
    """
    Test execution -
    """
    main_handler(test_handler=True)


@output_handler
def main():
    """
    Main execution -
    """
    main_handler()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main()
    else:
        print("Test execution started")
        test()
