from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.FortigateManager import FortigateManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ADD_ENTITIES_TO_POLICY_SCRIPT_NAME,
    ENTITIES_LOCATION,
)
from ..core.UtilsManager import remove_subnet_from_ip_address, get_domain_from_entity


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.URL]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ENTITIES_TO_POLICY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", is_mandatory=True, print_value=True
    )
    location = extract_action_param(siemplify, param_name="Location", print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    policy_existing_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = FortigateManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        # Check if policy exist with specified name
        policies = manager.get_policy_by_name(policy_name)

        if not policies:
            raise Exception(
                f"policy {policy_name} was not found in {INTEGRATION_DISPLAY_NAME}. Please check the "
                f"spelling."
            )

        policy = policies[0]
        policy_items = (
            policy.dst_items
            if location == ENTITIES_LOCATION.get("destination")
            else policy.src_items
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

            try:
                # Check if entity exists
                entities = manager.get_entity(entity)
                existing_entity = entities[0] if entities else None

                if not existing_entity:
                    siemplify.LOGGER.info(f"Not found entity: {entity.identifier}")

                    # Create not found entities
                    manager.create_entity(entity)
                    siemplify.LOGGER.info(
                        f"Successfully created entity: {entity.identifier}"
                    )
                else:
                    siemplify.LOGGER.info(f"Found entity: {entity.identifier}")

                # Add new entities
                entity_name = get_entity_name(entity)
                items = (
                    policy.dst_items
                    if location == ENTITIES_LOCATION.get("destination")
                    else policy.src_items
                )

                if entity_name in [item.get("name") for item in items]:
                    policy_existing_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"{entity.identifier} entity is already a part of policy {policy.name}."
                    )
                else:
                    policy_items = manager.update_policy_entities(
                        policy, policy_items, entity_name, location
                    )
                    successful_entities.append(entity)

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing entity: {entity.identifier}: Error is: {e}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if successful_entities:
            output_message += 'Successfully added the following entities to policy "{}" in {}: \n{}'.format(
                policy_name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if policy_existing_entities:
            output_message += "\nThe following entities are already a part of policy {} in {}: \n{}".format(
                policy_name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in policy_existing_entities]),
            )

        if failed_entities:
            output_message += "\nAction wasn't able to add the following entities to policy {} in {}: \n{}".format(
                policy_name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result = False
            output_message = (
                f"None of the provided entities were added to the policy {policy_name} in "
                f"{INTEGRATION_DISPLAY_NAME}."
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ADD_ENTITIES_TO_POLICY_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{ADD_ENTITIES_TO_POLICY_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


def get_entity_name(entity):
    if entity.entity_type == EntityTypes.ADDRESS:
        return remove_subnet_from_ip_address(entity.identifier)
    else:
        return get_domain_from_entity(entity.identifier)


if __name__ == "__main__":
    main()
