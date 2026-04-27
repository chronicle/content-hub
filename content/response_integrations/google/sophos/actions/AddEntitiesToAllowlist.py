from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.SophosManager import SophosManager
from ..core.constants import (
    SHA256_LENGTH,
    INTEGRATION_NAME,
    ADD_ENTITIES_TO_ALLOWLIST_ACTIONS_SCRIPT_NAME,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.SophosExceptions import HashAlreadyOnBlocklist

SUPPORTED_ENTITY_TYPES = [EntityTypes.FILEHASH]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ENTITIES_TO_ALLOWLIST_ACTIONS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Action parameters
    comment = extract_action_param(
        siemplify,
        param_name="Comment",
        print_value=True,
        is_mandatory=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    failed_entities = []
    already_added_hash = []

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = SophosManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            test_connectivity=True,
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            if len(entity.identifier) != SHA256_LENGTH:
                siemplify.LOGGER.error(
                    f"Hash type of hash: {entity.identifier} is not supported. "
                    "Provide SHA-256 Hash."
                )
                continue
            try:
                manager.add_hash_to_allowlist(
                    hash_entity=entity.identifier, comment=comment
                )
                successful_entities.append(entity)

            except HashAlreadyOnBlocklist as e:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} was already on the allowlist in "
                    f"{INTEGRATION_NAME}."
                )
                already_added_hash.append(entity)

            except Exception as e:
                siemplify.LOGGER.error(e)
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            output_message = "Successfully added the following entities to allowlist in {}: \n{}".format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

            if failed_entities:
                output_message += "\nAction wasn't able to add the following entities to allowlist in {}: \n{}".format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )

            if already_added_hash:
                output_message += "\nThe following entities are already a part of the allowlist in {}: \n{}".format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in already_added_hash]),
                )

        else:
            result = False
            output_message = (
                "None of the provided entities were added to the allowlist in "
                f"{INTEGRATION_NAME}."
            )

    except Exception as e:
        siemplify.LOGGER.error(
            "General error performing action "
            f"{ADD_ENTITIES_TO_ALLOWLIST_ACTIONS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            "Error executing action"
            f" {ADD_ENTITIES_TO_ALLOWLIST_ACTIONS_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
