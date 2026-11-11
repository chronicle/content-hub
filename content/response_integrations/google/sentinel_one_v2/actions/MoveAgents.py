from __future__ import annotations
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from sentinel_one_v2.core.exceptions import SentinelOneV2NotFoundError, SentinelOneV2ValidationError
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from sentinel_one_v2.core.constants import INTEGRATION_NAME, PRODUCT_NAME, MOVE_AGENTS_SCRIPT_NAME
from sentinel_one_v2.core.utils import get_entity_original_identifier
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = MOVE_AGENTS_SCRIPT_NAME

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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    group_id = extract_action_param(siemplify, param_name="Group ID", print_value=True)
    group_name = extract_action_param(
        siemplify, param_name="Group Name", print_value=True
    )

    group_identifier_type, group_identifier = (
        ("ID", group_id) if group_id else ("Name", group_name)
    )

    found_agents, success_entities, ignored_entities, failed_entities = (
        [],
        [],
        [],
        set(),
    )
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    request_group_id = group_id
    output_message = ""

    try:
        if not (group_id or group_name):
            raise SentinelOneV2ValidationError(
                "either 'Group Name' or 'Group ID' should be provided."
            )

        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        if not request_group_id:
            group = manager.get_group_or_raise(group_name)
            request_group_id = group.id

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            try:
                siemplify.LOGGER.info(f"Processing entity {entity_identifier}")
                found_agent = None

                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for hostname {entity_identifier}"
                        )
                        found_agent = manager.get_agent_by_hostname(entity_identifier)
                    except SentinelOneV2NotFoundError as e:
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")

                elif entity.entity_type == EntityTypes.ADDRESS:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for address {entity_identifier}"
                        )
                        found_agent = manager.get_agent_by_ip(entity_identifier)
                    except SentinelOneV2NotFoundError as e:
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")

                if found_agent:
                    found_agents.append((found_agent, entity_identifier))
                    siemplify.LOGGER.info(
                        f"Found agent {found_agent.id} for entity {entity_identifier}"
                    )
                else:
                    failed_entities.add(entity_identifier)
            except Exception as e:
                failed_entities.add(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if found_agents:
            siemplify.LOGGER.info(
                f"Moving {len(found_agents)} agents to group {group_identifier}."
            )
            for agent, entity_identifier in found_agents:
                try:
                    moved_agents_count = manager.move_agents(
                        agent_ids=[agent.id], group_id=request_group_id
                    )
                    (
                        success_entities if moved_agents_count > 0 else ignored_entities
                    ).append(entity_identifier)
                except Exception as e:
                    siemplify.LOGGER.exception(e)
                    siemplify.LOGGER.error(
                        f"Unable to move agent {agent.id} to group {group_identifier}"
                    )
                    if isinstance(e, SentinelOneV2NotFoundError):
                        raise
                    failed_entities.add(entity_identifier)

        if success_entities:
            output_message += (
                "Successfully moved the following endpoints to the group with"
                f"{group_identifier_type} {group_identifier} in {PRODUCT_NAME}:\n"
                f"{', '.join(success_entities)}\n"
            )

        if failed_entities:
            output_message += (
                "Action wasn't able to move the following endpoints to the group with"
                f"{group_identifier_type} {group_identifier} in {PRODUCT_NAME}:\n"
                f"{', '.join(failed_entities)}\n"
            )
        if ignored_entities:
            output_message += (
                "The following endpoints are already a part of the group with"
                f"{group_identifier_type} {group_identifier} in {PRODUCT_NAME}:\n"
                f"{', '.join(ignored_entities)}\n"
            )
        elif not success_entities:
            result_value = False
            output_message = (
                f"No endpoints were moved to the group {group_identifier_type}"
                f"{group_identifier} in {PRODUCT_NAME}"
            )
    except Exception as e:
        output_message = (
            "Action wasn't able to move endpoints to the group with"
            f"{group_identifier_type} {group_identifier} in {PRODUCT_NAME}."
            "Reason: Group was not found."
            if isinstance(e, SentinelOneV2NotFoundError)
            else f"Error executing action '{MOVE_AGENTS_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n"
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
