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
from soar_sdk.SiemplifyUtils import dict_to_flat
from ..core.RSAManager import RSA
import arrow
import uuid
import sys
import json
import os

# =====================================
#             CONSTANTS               #
# =====================================
DEFAULT_TIME_FIELD = "time"
DEFAULT_TIME_FORMAT = "%Y-%b-%d %H:%M:%S"
DEFAULT_MAX_DAYS_BACKWARDS = 1
DEFAULT_MAX_ALERTS_COUNT_LIMIT = 10
QUERY_TIME_POSTFIX = (
    " && {0}>={1} && {0}<{2}"  # {0} - Time Field ,{1} - Event Time, {2} - Current Time
)
DEFAULT_PRODUCT = "RSA NetWitness"

EVENT_TIME_FILED_MILLISECONDS = "event_time_milliseconds"

SESSION_IDS_FILE_PATH = "session_ids.json"

EMPTY_JSON_STRING = "[]"


# =====================================
#              CLASSES                #
# =====================================
class RSAIncidentsConnectorException(Exception):
    """
    RSA Incidents Connector Exception
    """

    pass


class RSAQueryConnector:
    """
    RSA Incidents Connector
    """

    def __init__(self, siemplify_logger):
        """
        :param siemplify_logger: Siemplify logger object.
        """
        self.siemplify_logger = siemplify_logger

    @staticmethod
    def validate_timestamp(unixtime_timestamp, max_days_backwards=1):
        """
        Adjust timestamp to the max days backwards value.
        :param unixtime_timestamp: {long} unix time timestamp.
        :param max_days_backwards: {int} days backwards to check timestamp.
        :return: {long} unixtime timestamp
        """
        # Calculate- Days backwards to milliseconds.
        offset_unixtime_milliseconds = (
            arrow.now().shift(days=-max_days_backwards).timestamp * 1000
        )

        # Calculate max time with offset.
        if unixtime_timestamp < offset_unixtime_milliseconds:
            return offset_unixtime_milliseconds
        return unixtime_timestamp

    @staticmethod
    def check_session_ids_json_exist_and_return_content(session_ids_file_path):
        """
        Verify session ids maintenance file exists, else create one with empty json.
        :param session_ids_file_path: {string} The path of the session ids maintenance json file.
        :return: {void}
        """
        if not os.path.exists(session_ids_file_path):
            open(session_ids_file_path, "w").write(EMPTY_JSON_STRING)
            return EMPTY_JSON_STRING
        return json.loads(open(session_ids_file_path, "r").read())

    @staticmethod
    def update_json_file_with_new_session_ids(session_ids_file_path, session_ids):
        """
        Add new event's session IDs to the file.
        :param session_ids_file_path: {string} The path of the session ids maintenance json file.
        :param session_ids: {list} list of session ids.
        :return: {void}
        """
        session_ids_list = json.loads(open(session_ids_file_path, "r").read())
        session_ids_list.extend(session_ids)
        # Always leave the last 1000 session ids.
        open(session_ids_file_path, "w").write(json.dumps(session_ids_list[-1000:]))

    def filter_out_sessions_ids_by_ids_file(
        self, session_ids_to_filter_by, session_ids_list_to_filter
    ):
        """
        Eliminate the session ids from the list according to the session ids that are at the maintenance file.
        :param session_ids_to_filter_by:
        :param session_ids_list_to_filter:
        :return: {list} complete list of session ids.
        """
        result_list = []
        for session_id in session_ids_list_to_filter:
            if str(session_id) in session_ids_to_filter_by:
                self.siemplify_logger.info(
                    f'Session ID "{session_id}" was already fetched.'
                )
            else:
                result_list.append(session_id)
        return result_list

    @staticmethod
    def form_query(default_query, event_time_field, last_event_time=0):
        """
        Form final connector query that will be sent to RSA Netwitness.
        :param default_query: {string} query recieved from the user.
        :param event_time_field: {string} the name of the field of the event time.
        :param last_event_time: {long} unixtime timestamp
        :return: {string} final query
        """
        # Get current time in unixtime.
        now_time_string = arrow.utcnow().timestamp
        last_event_time_string = str(
            last_event_time / 1000
        )  # The query uses unixtime in seconds.
        # Add to the query the time limits.
        return f"{default_query}{QUERY_TIME_POSTFIX.format(event_time_field, last_event_time_string, now_time_string)}"

    @staticmethod
    def create_case(
        event_metadata,
        device_product_field,
        rule_generator_field,
        event_time_field,
        environment,
        query,
    ):
        """
        Create a case objest.
        :param event_metadata: {dict} raw data of the event.
        :param device_product_field: {string} the name of the field which contains the device product
        :param rule_generator_field: {string} the name of the field which contain the rule generator value
        :param event_time_field: {string} the name of the field which contain the time value
        :param environment: {string} the value of the environment name
        :param query: {string} the full query that was sent to Netwitness
        :return:
        """
        case_info = CaseInfo()
        case_info.start_time = (
            event_metadata.get(event_time_field) * 1000
            if event_metadata.get(event_time_field)
            else 1
        )
        case_info.end_time = case_info.start_time
        case_info.rule_generator = event_metadata.get(
            rule_generator_field, "No rule generator field found."
        )
        case_info.device_product = event_metadata.get(
            device_product_field, DEFAULT_PRODUCT
        )
        case_info.device_vendor = case_info.device_product
        case_info.environment = environment

        case_info.name = event_metadata.get("sessionid", "Alert has no name.")
        # If no Session ID, replace with timestamp + uuid because timestamp can be not unique in some cases.
        case_info.ticket_id = event_metadata.get(
            "sessionid", f"{case_info.start_time}_{str(uuid.uuid4())}"
        )
        case_info.display_id = case_info.identifier = case_info.ticket_id

        # Add milliseconds time field to the event(For Mapping).
        event_metadata[EVENT_TIME_FILED_MILLISECONDS] = case_info.start_time

        case_info.events = [dict_to_flat(event_metadata)]

        # Add additional data to case.
        case_info.extensions.update(
            {"session_id": event_metadata.get("sessionid"), "query": query}
        )
        return case_info


@output_handler
def main_handler(test_handler=False):
    """
    :param test_handler: run test flow of real flow (timestamp updating is the differencee)
    :return: -
    """
    connector_scope = SiemplifyConnectorExecution()
    output_variables = {}
    log_items = []
    all_cases = []
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

        concentrator_uri = connector_scope.parameters.get("Concentrator URI")
        decoder_uri = connector_scope.parameters.get("Decoder URI")
        username = connector_scope.parameters.get("Username")
        password = connector_scope.parameters.get("Password")
        query = connector_scope.parameters.get("Query")
        device_product_field = connector_scope.parameters.get("DeviceProductField")
        rule_generator_field = connector_scope.parameters.get("Rule Generator Field")
        alert_count_limit = int(
            connector_scope.parameters.get(
                "Alert Count Limit", DEFAULT_MAX_ALERTS_COUNT_LIMIT
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
            concentrator_uri=concentrator_uri,
            decoder_uri=decoder_uri,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        rsa_connector = RSAQueryConnector(connector_scope.LOGGER)

        # Fetch last event time from the timestamp file.
        last_event_time = rsa_connector.validate_timestamp(
            connector_scope.fetch_timestamp(), max_days_backwards
        )
        final_query = rsa_connector.form_query(query, event_time_field, last_event_time)
        session_ids_file_path = os.path.join(
            connector_scope.run_folder, SESSION_IDS_FILE_PATH
        )

        fetched_session_ids_list = (
            rsa_connector.check_session_ids_json_exist_and_return_content(
                session_ids_file_path
            )
        )

        session_ids = rsa_manager.get_session_ids_for_query(final_query)
        connector_scope.LOGGER.info(
            f"Found {len(session_ids)} session IDs. \n session IDs: {','.join(session_ids)}"
        )

        # Remove session IDs that already were fetched.
        session_ids = rsa_connector.filter_out_sessions_ids_by_ids_file(
            fetched_session_ids_list, session_ids
        )
        connector_scope.LOGGER.info(
            "{0} Session IDs left after elimination of already fetched alerts. \n Session IDs"
            " {1}".format(len(session_ids), ",".join(session_ids))
        )

        limited_session_ids = (
            session_ids[:1] if test_handler else session_ids[:alert_count_limit]
        )

        connector_scope.LOGGER.info(
            f"{', '.join(limited_session_ids)} session were left after slicing"
        )
        for session_id in limited_session_ids:
            connector_scope.LOGGER.info(f"Running on session with ID: {session_id}.")
            try:
                event_metadata = rsa_manager.get_metadata_from_session_id(session_id)
                connector_scope.LOGGER.info(
                    f"Got event metadata for session ID: {session_id}"
                )
            except Exception as err:
                error_massage = f"Error occurred fetching metadata for session ID: {session_id}, Error: {err}"
                connector_scope.LOGGER.error(error_massage)
                connector_scope.LOGGER.exception(err)

                if test_handler:
                    raise

                continue

            # Create case package.
            try:
                case = rsa_connector.create_case(
                    event_metadata,
                    device_product_field,
                    rule_generator_field,
                    event_time_field,
                    connector_scope.context.connector_info.environment,
                    final_query,
                )
                all_cases.append(case)
                connector_scope.LOGGER.info(
                    f"Case with display id: {case.display_id}, created successfully."
                )
            except Exception as err:
                error_massage = "Error creating case package."
                connector_scope.LOGGER.error(error_massage)
                connector_scope.LOGGER.exception(err)

                if test_handler:
                    raise

                continue

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

        if test_handler:
            connector_scope.LOGGER.info(
                " ------------ Finish RSA Connector Test ------------ "
            )
        else:
            # Update last run time: Take the start time of the last case at the cases list.
            if all_cases:
                all_cases.sort(key=lambda x: x.start_time)
                connector_scope.save_timestamp(new_timestamp=all_cases[-1].start_time)

            # Update list with successful session ids, and remove Nones from sent list in case the case does not have session id.
            rsa_connector.update_json_file_with_new_session_ids(
                session_ids_file_path,
                [
                    _f
                    for _f in [case.extensions.get("session_id") for case in all_cases]
                    if _f
                ],
            )

            connector_scope.LOGGER.info(
                " ------------ Connector Finished Iteration ------------ "
            )

        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as err:
        error_message = f"Got exception on main handler. Error: {err}"
        if test_handler:
            connector_scope.return_test_result(False, {})
            raise RSAIncidentsConnectorException(error_message)
        connector_scope.LOGGER.error(error_message)
        connector_scope.LOGGER.exception(err)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main_handler()
    else:
        print("Test execution started")
        main_handler(test_handler=True)
