from __future__ import annotations
import arrow
import json
import sys
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict, unix_now
from soar_sdk.SiemplifyAction import SiemplifyAction
from sentinel_one_v2.core.exceptions import SentinelOneV2NotFoundError, SentinelOneV2TooManyRequestsError
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from sentinel_one_v2.core.utils import get_entity_original_identifier
from setuptools.namespaces import flatten
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    GET_EVENTS_FOR_ENDPOINT_HOURS_BACK_SCRIPT_NAME,
    FOUND_EVENTS_TABLE_NAME,
    DEEP_VISIBILITY_QUERY_EVENTS_DEFAULT_LIMIT,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_EVENTS_FOR_ENDPOINT_HOURS_BACK_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    delta_in_hours = extract_action_param(
        siemplify,
        param_name="Hours Back",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    additional_data = extract_action_param(
        siemplify=siemplify,
        param_name="additional_data",
        default_value='{"failed_entities": [], "in_progress_entities": {}}',
    )
    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    failed_entities, query_ids_with_entity_identifiers = json.loads(
        additional_data
    ).values()
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )
        if is_first_run:
            from_date_unix_time = (
                arrow.utcnow().shift(hours=-delta_in_hours).int_timestamp * 1000
            )

            for entity in (
                entity
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
            ):
                entity_identifier = get_entity_original_identifier(entity)
                try:
                    siemplify.LOGGER.info(
                        f"Started processing entity: {entity_identifier}"
                    )
                    agent = None

                    if entity.entity_type == EntityTypes.HOSTNAME:
                        try:
                            siemplify.LOGGER.info(
                                f"Fetching agent for hostname {entity_identifier}"
                            )
                            agent = manager.get_agent_by_hostname(
                                hostname=entity_identifier
                            )
                        except SentinelOneV2NotFoundError as e:
                            siemplify.LOGGER.info(e)
                            siemplify.LOGGER.info(
                                f"Skipping entity {entity_identifier}"
                            )

                    elif entity.entity_type == EntityTypes.ADDRESS:
                        try:
                            siemplify.LOGGER.info(
                                f"Fetching agent for address {entity_identifier}"
                            )
                            agent = manager.get_agent_by_ip(
                                ip_address=entity_identifier
                            )
                        except SentinelOneV2NotFoundError as e:
                            siemplify.LOGGER.info(e)
                            siemplify.LOGGER.info(
                                f"Skipping entity {entity_identifier}"
                            )

                    if agent:
                        query_id = manager.initialize_get_events_for_agent_query(
                            agent_uuid=agent.uuid,
                            from_date=from_date_unix_time,
                            to_date=unix_now(),
                        )
                        siemplify.LOGGER.info(
                            f"Successfully initialized events fetching query {query_id} for {entity_identifier}"
                        )

                        query_ids_with_entity_identifiers[entity_identifier] = query_id
                    else:
                        failed_entities.append(entity_identifier)

                except Exception as e:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

        if query_ids_with_entity_identifiers:
            (
                success_entity_events,
                failed_entity_events,
                in_progress_entities,
                json_results,
            ) = handle_query_ids(siemplify, manager, query_ids_with_entity_identifiers)

            all_failed_entities = list(set(failed_entities + failed_entity_events))

            if in_progress_entities:
                status = EXECUTION_STATE_INPROGRESS
                result_value = json.dumps(
                    {
                        "failed_entities": all_failed_entities,
                        "in_progress_entities": in_progress_entities,
                    }
                )
                output_message = "Queries have not completed yet. Waiting"

            elif success_entity_events:
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
                output_message = (
                    "Successfully retrieved information about the events for the following endpoints:"
                    "\n   {}\n".format("\n   ".join(success_entity_events))
                )
                result_value = True

                if all_failed_entities:
                    output_message += (
                        "Action wasn't able to find any events for the following endpoints:"
                        "\n   {}\n".format("\n   ".join(all_failed_entities))
                    )
            else:
                output_message = "No information events for the provided endpoints."
        else:
            output_message = "No suitable endpoints were found."

    except Exception as e:
        output_message = f"Error executing action '{GET_EVENTS_FOR_ENDPOINT_HOURS_BACK_SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def validate_api_limit_exception(exception):
    if isinstance(exception, SentinelOneV2TooManyRequestsError):
        raise


def handle_query_ids(siemplify, manager, query_ids_with_entity_identifiers):
    """
    Wait for completing all of the query ids, get results depends on specified parameters
    :param siemplify: {SiemplifyAction}
    :param manager: {SentinelOneV2Manager}
    :param query_ids_with_entity_identifiers: {dict}
    :return: {tpl} Of success_entity_events, failed_entity_events, in_progress_entities, json_results
    """
    limit = extract_action_param(
        siemplify,
        param_name="Events Amount Limit",
        input_type=int,
        default_value=DEEP_VISIBILITY_QUERY_EVENTS_DEFAULT_LIMIT,
        print_value=True,
    )
    include_file_events_info = extract_action_param(
        siemplify,
        param_name="Include File Events Information",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    include_indicator_events_info = extract_action_param(
        siemplify,
        param_name="Include Indicator Events Information",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    include_dns_events_info = extract_action_param(
        siemplify,
        param_name="Include DNS Events Information",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    include_network_actions_events_info = extract_action_param(
        siemplify,
        default_value=False,
        input_type=bool,
        param_name="Include Network Actions Events Information",
        print_value=True,
    )
    include_url_events_info = extract_action_param(
        siemplify,
        param_name="Include URL Events Information",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    include_registry_events_info = extract_action_param(
        siemplify,
        param_name="Include Registry Events Information",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    include_scheduled_task_events_info = extract_action_param(
        siemplify,
        default_value=False,
        input_type=bool,
        param_name="Include Scheduled Task Events Information",
        print_value=True,
    )

    success_entity_events, failed_entity_events, json_results = [], [], {}

    for entity_identifier, query_id in query_ids_with_entity_identifiers.items():
        try:
            if not manager.is_query_completed(query_id):
                break
        except Exception as e:
            siemplify.LOGGER.exception(e)
            siemplify.LOGGER.info(
                f"Failed to check status of query {query_id}, entity {entity_identifier}"
            )
            validate_api_limit_exception(e)
            break
    else:
        siemplify.LOGGER.info("All queries have completed. Fetching events.")
        for (
            entity_identifier,
            query_id,
        ) in query_ids_with_entity_identifiers.copy().items():
            try:
                query_status = manager.get_query_status(query_id)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Unable to get query {query_id} status for entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)
                # break the loop and return in_progress_entities to the
                # next action iteration for getting query statuses again
                validate_api_limit_exception(e)
                break

            if manager.is_failed_query_status(query_status):
                # remove from in-progress queue adn add to failed list
                query_ids_with_entity_identifiers.pop(entity_identifier)
                failed_entity_events.append(entity_identifier)

                siemplify.LOGGER.error(
                    f"Failed to get failure status of query {query_id} of entity {entity_identifier}"
                )
                continue
            else:
                # remove handled query
                query_ids_with_entity_identifiers.pop(entity_identifier)

            siemplify.LOGGER.info(
                f"Collecting results for query {query_id}, entity {entity_identifier}"
            )
            json_results[entity_identifier] = {}

            try:
                process_events = manager.get_process_events_by_query_id(
                    query_id, limit=limit
                )
                siemplify.LOGGER.info(
                    f"Found {len(process_events)} process events for query {query_id}, entity {entity_identifier}"
                )

                json_results[entity_identifier]["process_events"] = [
                    process_event.to_json() for process_event in process_events
                ]
                if process_events:
                    siemplify.result.add_data_table(
                        FOUND_EVENTS_TABLE_NAME.format("Processes", entity_identifier),
                        construct_csv([event.to_csv() for event in process_events]),
                    )

            except Exception as e:
                siemplify.LOGGER.exception(e)
                siemplify.LOGGER.error(
                    f"Failed to get process events for query {query_id} and entity {entity_identifier}"
                )
                validate_api_limit_exception(e)

            if include_file_events_info:
                try:
                    file_events = manager.get_file_events_by_query_id(
                        query_id, limit=limit
                    )
                    siemplify.LOGGER.info(
                        f"Found {len(file_events)} file events for query {query_id}, entity {entity_identifier}"
                    )

                    json_results[entity_identifier]["file_events"] = [
                        file_event.to_json() for file_event in file_events
                    ]
                    if file_events:
                        siemplify.result.add_data_table(
                            FOUND_EVENTS_TABLE_NAME.format("File", entity_identifier),
                            construct_csv([event.to_csv() for event in file_events]),
                        )

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get file events for query {query_id} and entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

            if include_indicator_events_info:
                try:
                    indicator_events = manager.get_indicator_events_by_query_id(
                        query_id, limit=limit
                    )
                    siemplify.LOGGER.info(
                        f"Found {len(indicator_events)} indicator events for query {query_id}, entity {entity_identifier}"
                    )
                    json_results[entity_identifier]["indicator_events"] = [
                        indicator_event.to_json()
                        for indicator_event in indicator_events
                    ]
                    if indicator_events:
                        siemplify.result.add_data_table(
                            FOUND_EVENTS_TABLE_NAME.format(
                                "Indicator", entity_identifier
                            ),
                            construct_csv(
                                [event.to_csv() for event in indicator_events]
                            ),
                        )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get indicator events for query {query_id} and entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

            if include_dns_events_info:
                try:
                    dns_events = manager.get_dns_events_by_query_id(
                        query_id, limit=limit
                    )
                    siemplify.LOGGER.info(
                        f"Found {len(dns_events)} dns events for query {query_id}, entity {entity_identifier}"
                    )
                    json_results[entity_identifier]["dns_events"] = [
                        dns_event.to_json() for dns_event in dns_events
                    ]
                    if dns_events:
                        siemplify.result.add_data_table(
                            FOUND_EVENTS_TABLE_NAME.format("DNS", entity_identifier),
                            construct_csv([event.to_csv() for event in dns_events]),
                        )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get dns events for query {query_id} and entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

            if include_network_actions_events_info:
                try:
                    network_actions_events = (
                        manager.get_network_actions_events_by_query_id(
                            query_id, limit=limit
                        )
                    )
                    siemplify.LOGGER.info(
                        f"Found {len(network_actions_events)} network actions events for query {query_id}, entity {entity_identifier}"
                    )

                    json_results[entity_identifier]["network_actions_events"] = [
                        network_actions_event.to_json()
                        for network_actions_event in network_actions_events
                    ]
                    if network_actions_events:
                        siemplify.result.add_data_table(
                            FOUND_EVENTS_TABLE_NAME.format(
                                "Network", entity_identifier
                            ),
                            construct_csv(
                                [event.to_csv() for event in network_actions_events]
                            ),
                        )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get network actions events for query {query_id} and entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

            if include_url_events_info:
                try:
                    url_events = manager.get_url_events_by_query_id(
                        query_id, limit=limit
                    )
                    siemplify.LOGGER.info(
                        f"Found {len(url_events)} url events for query {query_id}, entity {entity_identifier}"
                    )
                    json_results[entity_identifier]["url_events"] = [
                        url_event.to_json() for url_event in url_events
                    ]

                    if url_events:
                        siemplify.result.add_data_table(
                            FOUND_EVENTS_TABLE_NAME.format("URL", entity_identifier),
                            construct_csv([event.to_csv() for event in url_events]),
                        )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get url events for query {query_id} and entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

            if include_registry_events_info:
                try:
                    registry_events = manager.get_registry_events_by_query_id(
                        query_id, limit=limit
                    )
                    siemplify.LOGGER.info(
                        f"Found {len(registry_events)} registry events for query {query_id}, entity {entity_identifier}"
                    )

                    json_results[entity_identifier]["registry_events"] = [
                        registry_event.to_json() for registry_event in registry_events
                    ]
                    if registry_events:
                        siemplify.result.add_data_table(
                            FOUND_EVENTS_TABLE_NAME.format(
                                "Registry", entity_identifier
                            ),
                            construct_csv(
                                [event.to_csv() for event in registry_events]
                            ),
                        )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get registry events for query {query_id} and entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

            if include_scheduled_task_events_info:
                try:
                    scheduled_task_events = (
                        manager.get_scheduled_task_events_by_query_id(
                            query_id, limit=limit
                        )
                    )
                    siemplify.LOGGER.info(
                        f"Found {len(scheduled_task_events)} scheduled task events for query {query_id}, entity {entity_identifier}"
                    )

                    json_results[entity_identifier]["scheduled_task_events"] = [
                        scheduled_task_event.to_json()
                        for scheduled_task_event in scheduled_task_events
                    ]
                    if scheduled_task_events:
                        siemplify.result.add_data_table(
                            FOUND_EVENTS_TABLE_NAME.format(
                                "Scheduled", entity_identifier
                            ),
                            construct_csv(
                                [event.to_csv() for event in scheduled_task_events]
                            ),
                        )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get scheduled task events for query {query_id} and entity {entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    validate_api_limit_exception(e)

            if not query_ids_with_entity_identifiers:
                json_result_values = (value.values() for value in json_results.values())
                events_exist = bool(list(flatten(flatten(json_result_values))))
                (
                    success_entity_events if events_exist else failed_entity_events
                ).append(entity_identifier)

    return (
        success_entity_events,
        failed_entity_events,
        query_ids_with_entity_identifiers,
        json_results,
    )


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
