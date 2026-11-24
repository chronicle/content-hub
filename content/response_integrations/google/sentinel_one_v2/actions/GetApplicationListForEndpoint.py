from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    flat_dict_to_csv,
)
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    GET_APPLICATION_LIST_FOR_ENDPOINT_SCRIPT_NAME,
    UNSUCCESSFUL_ATTEMPTS_TABLE_NAME,
)
from sentinel_one_v2.core.exceptions import SentinelOneV2NotFoundError
from sentinel_one_v2.core.utils import get_entity_original_identifier
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


SUITABLE_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_APPLICATION_LIST_FOR_ENDPOINT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
    max_items_to_return = extract_action_param(
        siemplify,
        param_name="Max Applications To Return",
        input_type=int,
        print_value=True,
    )
    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUITABLE_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_entities, failed_entities = [], []
    json_results, errors_dict = {}, {}

    try:
        sentinel_one_manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for entity in scope_entities:
            entity_identifier = get_entity_original_identifier(entity)

            try:
                siemplify.LOGGER.info(f"Processing entity {entity_identifier}")
                agent = None

                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for hostname {entity_identifier}"
                        )
                        agent = sentinel_one_manager.get_agent_by_hostname(
                            hostname=entity_identifier
                        )
                    except SentinelOneV2NotFoundError as e:
                        failed_entities.append(entity_identifier)
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")
                        continue

                if entity.entity_type == EntityTypes.ADDRESS:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for address {entity_identifier}"
                        )
                        agent = sentinel_one_manager.get_agent_by_ip(
                            ip_address=entity_identifier
                        )
                    except SentinelOneV2NotFoundError as e:
                        failed_entities.append(entity_identifier)
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")
                        continue

                if agent and agent.id:
                    siemplify.LOGGER.info(
                        f"Found agent {agent.id} for entity {entity_identifier}"
                    )
                    siemplify.LOGGER.info(f"Fetching applications for agent {agent.id}")
                    applications_list = (
                        sentinel_one_manager.get_applications_from_endpoint(
                            agent_id=agent.id, limit=max_items_to_return
                        )
                    )

                    if applications_list:
                        siemplify.LOGGER.info(
                            f"Found {len(applications_list)} applications"
                        )
                        successful_entities.append(entity_identifier)
                        siemplify.result.add_entity_table(
                            entity_identifier,
                            construct_csv([app.to_csv() for app in applications_list]),
                        )
                        json_results[entity_identifier] = [
                            app.to_json() for app in applications_list
                        ]
                    else:
                        failed_entities.append(entity_identifier)
                else:
                    siemplify.LOGGER.error(
                        f'Error: Not found agent id for entity "{entity_identifier}"'
                    )
            except Exception as err:
                failed_entities.append(entity_identifier)
                errors_dict[entity_identifier] = str(err)
                siemplify.LOGGER.error(
                    f"An error occurred on the {entity_identifier} entity: {err}"
                )
                siemplify.LOGGER.exception(err)

        if successful_entities:
            output_message = (
                "Successfully retrieved available applications for the"
                f"following endpoints:\n{', '.join(successful_entities)}\n"
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

        if failed_entities:
            output_message += (
                "Action wasn't able to retrieve available applications for the"
                f"following endpoints:\n{', '.join(failed_entities)}\n"
            )

        if not successful_entities:
            output_message = (
                "No applications were retrieved for the provided endpoints."
            )
            result_value = False

        if errors_dict:
            siemplify.result.add_data_table(
                UNSUCCESSFUL_ATTEMPTS_TABLE_NAME, flat_dict_to_csv(errors_dict)
            )

    except Exception as err:
        output_message = (
            "Error executing action"
            f"'{GET_APPLICATION_LIST_FOR_ENDPOINT_SCRIPT_NAME}'. Reason: {err}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
