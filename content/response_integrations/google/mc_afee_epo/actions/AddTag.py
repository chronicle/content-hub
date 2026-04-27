from __future__ import annotations
from ..core.McAfeeCommon import McAfeeCommon
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, PRODUCT_NAME, ADD_TAG_SCRIPT_NAME
from ..core.exceptions import McAfeeEpoNotFoundException
from ..core.utils import (
    get_entity_original_identifier,
    is_different_items,
    fix_status_for_duplicated_items,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_TAG_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ServerAddress",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    group_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="GroupName"
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )

    tag_name = extract_action_param(siemplify, param_name="Tag Name", is_mandatory=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    (
        success_entities,
        failed_entities,
        ignored_entities,
        systems_data,
        handled_entities,
    ) = ([], [], [], [], [])
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = McafeeEpoManager(
            api_root=api_root,
            username=username,
            password=password,
            group_name=group_name,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        if manager.group and suitable_entities:
            systems_data = manager.get_systems(manager.group.group_id)

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity}")
            entity_original_identifier = get_entity_original_identifier(entity)
            try:
                manager.get_system_info_or_raise(entity_original_identifier)

                if manager.group:
                    system = McAfeeCommon.filter_systems_by_entity(systems_data, entity)
                    affected = manager.apply_tag_to_endpoint_by_host_id(
                        tag_name, host_id=system.parent_id
                    )
                else:
                    affected = manager.apply_tag_to_endpoint_by_host_name(
                        tag_name, host_name=entity_original_identifier
                    )

                (success_entities if affected > 0 else ignored_entities).append(
                    entity_original_identifier
                )
                handled_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity}")
            except Exception as e:
                if isinstance(e, McAfeeEpoNotFoundException):
                    raise
                failed_entities.append(entity_original_identifier)
                siemplify.LOGGER.error(
                    f"Failed to add tag for entity {entity_original_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if success_entities and is_different_items(
            entity.entity_type for entity in handled_entities
        ):
            success_entities, ignored_entities = fix_status_for_duplicated_items(
                manager, success_entities, ignored_entities
            )

        if success_entities:
            output_message = (
                f'Successfully added tag "{tag_name}" to the following endpoints in '
                f'{PRODUCT_NAME}: {", ".join(success_entities)}\n'
            )
        if failed_entities:
            output_message += (
                f'Action wasn\'t able to add tag "{tag_name}" to the following endpoints in '
                f'{PRODUCT_NAME}: {", ".join(failed_entities)}\n'
            )
        if ignored_entities:
            output_message += (
                f'Tag "{tag_name}" was already a part of the following endpoints in '
                f'{PRODUCT_NAME}: {", ".join(ignored_entities)}\n'
            )
        elif not success_entities:
            result_value = False
            output_message = (
                f'Tag "{tag_name}" wasn\'t added to the provided endpoints.'
            )
    except Exception as e:
        output_message = f"Error executing action '{ADD_TAG_SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
