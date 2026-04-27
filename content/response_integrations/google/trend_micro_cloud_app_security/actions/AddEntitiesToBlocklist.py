from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
import re
import validators
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TrendMicroCloudAppSecurityManager import TrendMicroCloudAppSecurityManager
from TIPCommon import extract_configuration_param
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    ADD_ENTITIES_TO_BLOCKLIST_ACTION,
    SHA1_HASH_LENGTH,
    EMAIL_REGEX,
    DISPLAY_INTEGRATION_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ENTITIES_TO_BLOCKLIST_ACTION
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
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    failed_entities = []
    successful_entities = []
    entities_already_blocked = []
    found_target_entities = False

    try:
        trend_manager = TrendMicroCloudAppSecurityManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        already_blocked_entities = trend_manager.get_blocked_entities()

        for entity in siemplify.target_entities:
            block_entity = False
            if entity.entity_type == EntityTypes.URL:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                found_target_entities = True
                if validators.url(
                    entity.identifier
                ):  # the endpoint only supports valid URLs
                    if entity.identifier.lower() not in map(
                        str.lower, already_blocked_entities.urls
                    ):
                        block_entity = True
                    else:
                        siemplify.LOGGER.info(
                            f"Entity: {entity.identifier} is already in blocklist."
                        )
                        entities_already_blocked.append(entity)
                else:
                    siemplify.LOGGER.info(
                        f"Entity type URL: {entity.identifier} is in incorrect format."
                    )

            if entity.entity_type == EntityTypes.USER:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                found_target_entities = True
                if re.search(EMAIL_REGEX, entity.identifier.lower()):
                    if entity.identifier.lower() not in map(
                        str.lower, already_blocked_entities.senders
                    ):
                        block_entity = True
                    else:
                        siemplify.LOGGER.info(
                            f"Entity: {entity.identifier} is already in blocklist."
                        )
                        entities_already_blocked.append(entity)
                else:
                    siemplify.LOGGER.info(
                        f"Entity type USER: {entity.identifier} is in incorrect format."
                    )

            if entity.entity_type == EntityTypes.FILEHASH and entity.entity_type:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                found_target_entities = True
                if entity.identifier.lower() not in map(
                    str.lower, already_blocked_entities.hashes
                ):
                    if len(entity.identifier) == SHA1_HASH_LENGTH:
                        block_entity = True
                else:
                    siemplify.LOGGER.info(
                        f"Entity: {entity.identifier} is already in blocklist."
                    )
                    entities_already_blocked.append(entity)

            if block_entity:
                try:
                    trend_manager.add_entities_to_blocklist(
                        entity_type=entity.entity_type,
                        entity_to_remove=entity.identifier,
                    )
                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )
                except Exception as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

        if entities_already_blocked:
            output_message += "\nThe following entities are already a part of blocklist in {}: {}.".format(
                DISPLAY_INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in entities_already_blocked]),
            )

        if (
            not successful_entities
            and not failed_entities
            and not found_target_entities
        ):
            result_value = False
            output_message += f"\nNo entities were added using information from {DISPLAY_INTEGRATION_NAME}."

        if successful_entities:
            output_message += "\nSuccessfully added the following entities to blocklist in {}: {}".format(
                DISPLAY_INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

            if failed_entities:
                output_message += "\nAction wasn't able to add the following entities to blocklist in {}: {}".format(
                    DISPLAY_INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )

    except Exception as e:
        output_message += (
            f"Error executing action {ADD_ENTITIES_TO_BLOCKLIST_ACTION}. Reason: {e}."
        )
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
