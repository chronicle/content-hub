from __future__ import annotations
import json
import sys
from collections import defaultdict
from typing import Optional, List, Union

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.LogPointManager import LogPointManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.consts import (
    INTEGRATION_NAME,
    EXECUTE_ENTITY_QUERY_SCRIPT_NAME,
    DEFAULT_QUERY_TIME_FRAME,
    DEFAULT_CROSS_ENTITY_OPERATOR,
    DEFAULT_MAX_QUERY_RESULTS,
    CUSTOM_QUERY_TIME_FRAME,
    TIME_FRAME_MAPPING,
    ENTITY_TYPE_EMAIL,
    MAPPED_OPERATOR,
    OR,
    SEARCH_ID,
    RESULTS,
)
from ..core.exceptions import (
    LogPointNotFoundException,
    LogPointInvalidParametersException,
    LogPoIntInsufficientEntityTypesException,
    LogPointUnsuccessfulQueryResultsException,
)
from ..core.utils import (
    load_csv_to_list,
    get_missing_repos,
    unix_now_seconds,
    validate_date_parameter,
    validate_time_range,
    is_valid_email,
    join_queries,
    build_sub_query,
)


def start_operation(
    siemplify: SiemplifyAction,
    manager: LogPointManager,
    time_range: Union[List[int], str],
    query: str,
    repos: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> (str, str, int):
    """
    Main part of the action that executes query job in LogPoint
    :param siemplify: SiemplifyAction object.
    :param manager: LogPointManager manager object.
    :param repos: {[str]} List of IP addresses of the repos for which to perform the search query
    :param time_range: {[int,int] or str} Time range of the query. Can be list of 2 timestamps (unix time in seconds) [1609496280,
    1610274480] or custom range represented as string for example: "Last 24 hours"
    :param query: {str} Valid search query to execute in Logpoint
    :param limit: {int} Max records of search results to return
    :return: {output message, json result, execution_state} Output message, results value and execution state
    """

    status = EXECUTION_STATE_INPROGRESS

    try:
        siemplify.LOGGER.info(f"Creating query job with query:\n {query}")
        query_job = manager.create_query_job(
            time_range=time_range, query=query, limit=limit, repos=repos
        )
        siemplify.LOGGER.info(
            f"Successfully created query job with search id {query_job.search_id}"
        )

        output_message = (
            f"Waiting for query to finish processing in {INTEGRATION_NAME}."
        )
        result_value = json.dumps({SEARCH_ID: query_job.search_id})

    except LogPointUnsuccessfulQueryResultsException as error:
        output_message = (
            "Action wasn't able to successfully execute query and retrieve results "
            f"from {INTEGRATION_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_COMPLETED
        result_value = False

    except Exception as error:
        output_message = (
            f"Error executing action '{EXECUTE_ENTITY_QUERY_SCRIPT_NAME}'. "
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


def query_operation_status(siemplify, manager: LogPointManager, search_id: str):
    """
    Part of the action that periodically fetches the created query job results
    :param siemplify: SiemplifyAction object.
    :param manager: LogPointManager manager object.
    :param search_id: {str} Unique search id to retrieve results for
    :return: {output message, json result, execution_state} Output message, results value and execution state
    """

    try:
        siemplify.LOGGER.info(f"Checking results for query with search id: {search_id}")
        query_result = manager.get_query_results(search_id=search_id)

        if query_result.finished:
            status = EXECUTION_STATE_COMPLETED

            if query_result.query_rows:
                output_message = (
                    "Successfully executed query and retrieved results from "
                    f"{INTEGRATION_NAME}"
                )
                result_value = True
                siemplify.result.add_data_table(
                    title=RESULTS,
                    data_table=construct_csv(
                        [query_row.as_csv() for query_row in query_result.query_rows]
                    ),
                )
                siemplify.result.add_result_json(
                    [query_row.as_json() for query_row in query_result.query_rows]
                )
            else:
                output_message = f"No data was found for the provided query."
                result_value = False
        else:
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps({SEARCH_ID: search_id})
            output_message = (
                f"Waiting for query to finish processing in {INTEGRATION_NAME}"
            )

    except LogPointUnsuccessfulQueryResultsException as error:
        output_message = (
            "Action wasn't able to successfully execute query and retrieve results "
            f"from {INTEGRATION_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_COMPLETED
        result_value = False

    except Exception as error:
        output_message = (
            f"Error executing action '{EXECUTE_ENTITY_QUERY_SCRIPT_NAME}'. "
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {EXECUTE_ENTITY_QUERY_SCRIPT_NAME}"
    mode = "Main" if is_first_run else "Check Query Job Status"

    supported_entities = [
        EntityTypes.URL,
        EntityTypes.ADDRESS,
        EntityTypes.USER,
        EntityTypes.HOSTNAME,
        EntityTypes.FILEHASH,
    ]
    suitable_entities = []
    mapped_suitable_entities = defaultdict(
        list
    )  # Map suitable entity types to their entity identifiers
    custom_entity_query = ""

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    ip_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IP Address",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret",
        is_mandatory=True,
    )

    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=True,
        print_value=True,
    )

    # Action Parameters
    query = extract_action_param(
        siemplify,
        param_name="Query",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=True,
        input_type=str,
        default_value=DEFAULT_QUERY_TIME_FRAME,
        print_value=True,
    )
    start_time = extract_action_param(
        siemplify,
        param_name="Start Time",
        is_mandatory=False,
        default_value=None,
        input_type=str,
        print_value=True,
    )
    end_time = extract_action_param(
        siemplify,
        param_name="End Time",
        is_mandatory=False,
        default_value=None,
        input_type=str,
        print_value=True,
    )
    repos = extract_action_param(
        siemplify,
        param_name="Repos",
        is_mandatory=False,
        default_value=None,
        input_type=str,
        print_value=True,
    )
    ip_entity_key = extract_action_param(
        siemplify,
        param_name="IP Entity Key",
        is_mandatory=False,
        input_type=str,
        default_value=None,
        print_value=True,
    )
    hostname_entity_key = extract_action_param(
        siemplify,
        param_name="Hostname Entity Key",
        is_mandatory=False,
        input_type=str,
        default_value=None,
        print_value=True,
    )
    file_hash_entity_key = extract_action_param(
        siemplify,
        param_name="File Hash Entity Key",
        is_mandatory=False,
        input_type=str,
        default_value=None,
        print_value=True,
    )
    user_entity_key = extract_action_param(
        siemplify,
        param_name="User Entity Key",
        is_mandatory=False,
        input_type=str,
        default_value=None,
        print_value=True,
    )
    url_entity_key = extract_action_param(
        siemplify,
        param_name="URL Entity Key",
        is_mandatory=False,
        input_type=str,
        default_value=None,
        print_value=True,
    )
    email_address_entity_key = extract_action_param(
        siemplify,
        param_name="Email Address Entity Key",
        is_mandatory=False,
        input_type=str,
        default_value=None,
        print_value=True,
    )
    stop_if_not_enough_entities = extract_action_param(
        siemplify,
        param_name="Stop if Not Enough Entities",
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )
    cross_entity_operator = extract_action_param(
        siemplify,
        param_name="Cross Entity Operator",
        is_mandatory=True,
        input_type=str,
        default_value=DEFAULT_CROSS_ENTITY_OPERATOR,
        print_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        max_results_to_return = extract_action_param(
            siemplify,
            param_name="Max Results To Return",
            is_mandatory=False,
            input_type=int,
            default_value=DEFAULT_MAX_QUERY_RESULTS,
            print_value=True,
        )
        manager = LogPointManager(
            ip_address=ip_address,
            username=username,
            secret=secret,
            ca_certificate_file=ca_certificate_file,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )
        manager.test_connectivity()

        if max_results_to_return <= 0:
            siemplify.LOGGER.info('"Max Results To Return" must be positive.')
            raise LogPointInvalidParametersException(
                '"Max Results To Return" must be positive.'
            )

        if not (
            ip_entity_key
            or hostname_entity_key
            or file_hash_entity_key
            or user_entity_key
            or url_entity_key
            or email_address_entity_key
        ):
            raise LogPointInvalidParametersException(
                'Please specify at least one ".. Entity Key" parameter.'
            )

        if is_first_run:

            # Check that provided repos exist in LogPoint
            repos_addresses = []
            if repos:
                repos = load_csv_to_list(repos, "Repos")
                siemplify.LOGGER.info("Searching for available repos")
                found_repos = manager.list_repos()
                siemplify.LOGGER.info(f"Found {len(found_repos)} available repos")

                missing_repos = get_missing_repos(repos, found_repos)
                if missing_repos:
                    raise LogPointNotFoundException(
                        "The following repos were not found in {}: {}\n Please make "
                        "sure that all of the repos are available.".format(
                            INTEGRATION_NAME, "\n   ".join(missing_repos)
                        )
                    )

                repos_addresses = [
                    found_repo.address
                    for found_repo in found_repos
                    if found_repo.repo in repos
                ]
                siemplify.LOGGER.info(
                    f"All provided repos available in {INTEGRATION_NAME}"
                )

            # Validate custom time frames
            if time_frame == CUSTOM_QUERY_TIME_FRAME:
                if not start_time:
                    raise LogPointInvalidParametersException(
                        "you need to provide 'Start Time', if 'Custom' is selected "
                        "for time frame."
                    )

                try:
                    # Check if start time is of format "YYYY-MM-DDThh:mm:ssZ" or timestamp "1611938799"
                    siemplify.LOGGER.info(
                        f"Validating provided start time {start_time}"
                    )
                    start_time_timestamp = validate_date_parameter(
                        start_time, "Start Time"
                    )
                    siemplify.LOGGER.info(
                        "Successfully validated date parameter as "
                        f"{start_time_timestamp}"
                    )

                    if end_time:
                        siemplify.LOGGER.info(
                            f"Validating provided start time {start_time}"
                        )
                        end_time_timestamp = validate_date_parameter(
                            end_time, "End Time"
                        )
                        siemplify.LOGGER.info(
                            "Successfully validated date parameter as "
                            f"{end_time_timestamp}"
                        )
                    else:
                        end_time_timestamp = unix_now_seconds()
                        siemplify.LOGGER.info(
                            "Custom time frame is selected without end time. Using "
                            f"timestamp of current time: {end_time_timestamp}"
                        )

                except Exception as error:
                    raise LogPointInvalidParametersException(f"{error}")

                siemplify.LOGGER.info(f"Successfully validated custom time frames.")
                time_range = validate_time_range(
                    [start_time_timestamp, end_time_timestamp]
                )
            else:
                siemplify.LOGGER.info(f'Using provided time frame of "{time_frame}"')
                time_range = TIME_FRAME_MAPPING.get(time_frame)

            for entity in siemplify.target_entities:
                if entity.entity_type not in supported_entities:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                if entity.entity_type == EntityTypes.USER:
                    if is_valid_email(entity.identifier):
                        siemplify.LOGGER.info(
                            f"Entity {entity.identifier} is of type {ENTITY_TYPE_EMAIL}"
                        )
                        mapped_suitable_entities[ENTITY_TYPE_EMAIL].append(
                            entity.identifier
                        )
                    else:
                        siemplify.LOGGER.info(
                            f"Entity {entity.identifier} is of type USER"
                        )
                        mapped_suitable_entities[EntityTypes.USER].append(
                            entity.identifier
                        )
                else:
                    mapped_suitable_entities[entity.entity_type].append(
                        entity.identifier
                    )

                suitable_entities.append(entity)

            mapped_entity_keys = {
                EntityTypes.USER: user_entity_key,
                EntityTypes.FILEHASH: file_hash_entity_key,
                EntityTypes.HOSTNAME: hostname_entity_key,
                EntityTypes.ADDRESS: ip_entity_key,
                EntityTypes.URL: url_entity_key,
                ENTITY_TYPE_EMAIL: email_address_entity_key,
            }

            # Check that enough entities were provided
            if stop_if_not_enough_entities:
                siemplify.LOGGER.info(
                    "Checking if enough entity types were supplied in scope"
                )
                for entity_type, entity_key_is_provided in mapped_entity_keys.items():
                    if (
                        bool(entity_key_is_provided)
                        and not mapped_suitable_entities[entity_type]
                    ):
                        raise LogPoIntInsufficientEntityTypesException(
                            "Action wasn\'t able to build the query, because not "
                            "enough entity types were supplied for the specified '.. "
                            "Entity Keys'. Please disable 'Stop If Not Enough "
                            "Entities' parameter or provide at least one entity for "
                            "each specified '.. Entity Key'"
                        )
                siemplify.LOGGER.info(f"All entity types were supplied")

            if suitable_entities:
                siemplify.LOGGER.info(
                    "Building entity query for supported entities:: "
                    f"{', '.join([entity.identifier for entity in suitable_entities])}"
                )

                sub_queries = []
                for (
                    entity_type,
                    suitable_entity_types,
                ) in mapped_suitable_entities.items():
                    entity_key = mapped_entity_keys[entity_type]
                    if suitable_entity_types and entity_key:
                        sub_queries.append(
                            build_sub_query(
                                operator=OR,
                                key=entity_key,
                                values=mapped_suitable_entities[entity_type],
                            )
                        )
                    else:
                        siemplify.LOGGER.info(
                            f"No entity keys or entities were found of {entity_type}"
                        )

                custom_entity_query = join_queries(
                    queries=sub_queries,
                    join_operand=MAPPED_OPERATOR[cross_entity_operator],
                )

            else:
                siemplify.LOGGER.info("No supported entities found.")

            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                manager=manager,
                time_range=time_range,
                repos=repos_addresses,
                query=f"{custom_entity_query} {query}",
                limit=max_results_to_return,
            )

        elif unix_now() >= siemplify.execution_deadline_unix_time_ms:
            siemplify.LOGGER.error(
                "Action reached a timeout. Please narrow down the time frame or"
                " lower the amount of results to return."
            )
            status = EXECUTION_STATE_TIMEDOUT
            result_value = False
            output_message = (
                "Action reached a timeout. Please narrow down the time frame or lower "
                "the amount of results to return."
            )

        else:
            search_id = json.loads(
                siemplify.extract_action_param("additional_data")
            ).get(SEARCH_ID)
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify, manager=manager, search_id=search_id
            )

    except LogPoIntInsufficientEntityTypesException as error:
        output_message = f"{error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_COMPLETED
        result_value = False

    except Exception as error:
        output_message = (
            f"Error executing action '{EXECUTE_ENTITY_QUERY_SCRIPT_NAME}'. "
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
