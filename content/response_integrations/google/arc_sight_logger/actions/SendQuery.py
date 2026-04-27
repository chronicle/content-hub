from __future__ import annotations
import datetime
import sys
import re
import json
from random import randint
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ArcSightLoggerManager import ArcSightLoggerManager
from soar_sdk.SiemplifyUtils import output_handler, utc_now
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    dict_to_flat,
    construct_csv,
)

from ..core.constants import (
    INTEGRATION_NAME,
    SEND_QUERY_SCRIPT_NAME,
    DEFAULT_TIME_FRAME,
    QUERY_STATUS_COMPLETED,
    QUERY_STATUS_RUNNING,
    QUERY_STATUS_STARTING,
    QUERY_STATUS_ERROR,
    DEFAULT_TIME_FRAME,
    TIME_UNIT_MAPPER,
    PAGE_LIMIT,
)


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_QUERY_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"
    siemplify.LOGGER.info(f"-------------- {mode} - Param Init --------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        input_type=str
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        input_type=str
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Parameters
    query = extract_action_param(
        siemplify,
        param_name="Query",
        is_mandatory=True
    )
    events_limit = extract_action_param(
        siemplify,
        param_name="Max Events to Return",
        default_value=PAGE_LIMIT,
        input_type=int,
    )
    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", default_value=DEFAULT_TIME_FRAME
    )
    fields_to_fetch = extract_action_param(
        siemplify,
        param_name="Fields to Fetch"
    )
    include_raw_event_data = extract_action_param(
        siemplify,
        param_name="Include Raw Event Data",
        default_value=True,
        input_type=bool,
    )
    local_search_only = extract_action_param(
        siemplify,
        param_name="Local Search Only",
        default_value=False,
        input_type=bool
    )
    discover_fields = extract_action_param(
        siemplify,
        param_name="Discover Fields",
        default_value=True,
        input_type=bool
    )
    sort_string = extract_action_param(
        siemplify, param_name="Sort", default_value="ascending"
    )

    siemplify.LOGGER.info(f"---------------- {mode} - Started ----------------")

    try:
        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                api_root,
                username,
                password,
                verify_ssl,
                query,
                time_frame,
                local_search_only,
                discover_fields,
            )
        else:
            session_id, encrypted_token = json.loads(
                siemplify.parameters["additional_data"]
            )
            fields = (
                [f.strip() for f in fields_to_fetch.split(",") if f.strip()]
                if fields_to_fetch
                else []
            )
            output_message, result_value, status = query_operation_status(
                siemplify,
                api_root,
                username,
                password,
                encrypted_token,
                verify_ssl,
                session_id,
                query,
                include_raw_event_data,
                sort_string,
                fields,
                events_limit,
            )

    except Exception as e:
        output_message = f'Error executing action "Send Query". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        result_value = "False"
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"--------------- {mode} - Finished ---------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def start_operation(
    siemplify,
    api_root,
    username,
    password,
    verify_ssl,
    query,
    time_frame,
    local_search_only,
    discover_fields,
):
    """
    Main SendQuery action
    :param siemplify: SiemplifyAction object
    :param api_root: Server address of the ArcSight Logger instance
    :param username: Username of ArcSight Logger account
    :param password: Password of the ArcSight Logger account
    :param verify_ssl: Sets session verification
    :param query: The query to send to ArcSight Logger event search
    :param time_frame: The time frame to fetch events
    :param local_search_only: If True, ArcSight Logger event search is local only
    :param discover_fields: If True, discover fields in the found events
    :return: {output_message, json result, execution state}
    """
    search_session_id = randint(1, 99999999999999999)
    time_delta = datetime.timedelta(
        **extract_unit_and_value_from_time_frame(
            logger=siemplify.LOGGER, time_frame=time_frame
        )
    )
    current_time = utc_now()
    time_offset = current_time - time_delta
    current_time_string = current_time.isoformat()[:-9] + current_time.isoformat()[26:]
    time_offset_string = time_offset.isoformat()[:-9] + time_offset.isoformat()[26:]
    arcsight_logger_manager = ArcSightLoggerManager(
        api_root,
        username,
        password,
        verify_ssl,
        siemplify_logger=siemplify.LOGGER
    )
    try:
        arcsight_logger_manager.login()
        auth_token = arcsight_logger_manager.send_query(
            search_session_id,
            query,
            time_offset_string,
            current_time_string,
            local_search_only,
            discover_fields,
        )
        encrypted_token = ArcSightLoggerManager.encrypt_token_json(
            json.dumps({"auth_token": auth_token}), password
        )
        output_message = (
            'Successfully initialized query. '
            'Continuing executing action "Send Query".'
        )
    except Exception as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        arcsight_logger_manager.logout()
        return output_message, "false", EXECUTION_STATE_COMPLETED

    return (
        output_message,
        json.dumps((search_session_id, encrypted_token)),
        EXECUTION_STATE_INPROGRESS,
    )


def query_operation_status(
    siemplify,
    api_root,
    username,
    password,
    encrypted_token,
    verify_ssl,
    session_id,
    query,
    include_raw_event_data,
    sort_string,
    fields_to_fetch,
    events_limit,
):
    """
    Main SendQuery action
    :param siemplify: SiemplifyAction object
    :param api_root: Server address of the ArcSight Logger instance
    :param username: Username of ArcSight Logger account
    :param password: Password of the ArcSight Logger account
    :param encrypted_token: Encrypted Auth Token for current session
    :param verify_ssl: Sets session verification
    :param session_id: Search session ID
    :param query: The query to send to ArcSight Logger event search
    :param include_raw_event_data: If True, raw event data is included in the response
    :param sort_string: Sort method to use
    :param fields_to_fetch: Fields to fetch from ArcSight Logger
    :param events_limit: The amount of events to return
    :return: {output message, json result, execution state}
    """
    result_value = "false"
    output_message = ""
    token_json = json.loads(
        ArcSightLoggerManager.decrypt_token_json(encrypted_token, password)
    )
    auth_token = token_json.get("auth_token")
    arcsight_logger_manager = ArcSightLoggerManager(
        api_root,
        username,
        password,
        auth_token,
        verify_ssl,
        siemplify_logger=siemplify.LOGGER,
    )
    arcsight_logger_manager.login()
    query_status = arcsight_logger_manager.get_query_status(session_id)
    if query_status.status == QUERY_STATUS_COMPLETED:
        results = arcsight_logger_manager.get_events_from_query(
            session_id,
            include_raw_event_data,
            fields_to_fetch,
            sort_string,
            events_limit,
        )
        if results and query_status.hit > 0:
            if fields_to_fetch:
                results = [
                    {k: v for k, v in d.items() if k in fields_to_fetch}
                    for d in results
                ]

            flat_results = list(map(dict_to_flat, results))
            csv_output = construct_csv(flat_results)
            siemplify.result.add_data_table("Results", csv_output)
            siemplify.result.add_result_json(results)
            result_value = "true"
            output_message = (
                'Successfully returned events for query '
                f'"{query}" from the ArcSight Logger'
            )
        else:
            output_message = (
                f'Events were not found for query "{query}" in ArcSight Logger'
            )

    elif (
        query_status.status == QUERY_STATUS_STARTING
        or query_status.status == QUERY_STATUS_RUNNING
    ):
        output_message = (
            'Starting processing query '
            f'"{query}" in ArcSight Logger'
        )
        return (
            output_message,
            json.dumps((session_id, encrypted_token)),
            EXECUTION_STATE_INPROGRESS,
        )
    elif query_status.status == QUERY_STATUS_ERROR:
        output_message = f'Unable to execute query "{query}" in ArcSight Logger'

    arcsight_logger_manager.logout()
    return output_message, result_value, EXECUTION_STATE_COMPLETED


def extract_unit_and_value_from_time_frame(logger, time_frame):
    try:
        value, unit = re.findall(r"(\d*)(\w)", time_frame)[0]
        value = int(value)
        return {TIME_UNIT_MAPPER[unit]: int(value)}
    except Exception as e:
        logger.warn(
            'Unable to extract provided time frame '
            f'"{time_frame}". Using default time '
            f'frame instead "{DEFAULT_TIME_FRAME}"'
        )
        value, unit = re.findall(r"(\d*)(\w)", DEFAULT_TIME_FRAME)[0]
        return {TIME_UNIT_MAPPER[unit]: int(value)}


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
