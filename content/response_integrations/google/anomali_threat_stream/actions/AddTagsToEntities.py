from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AnomaliThreatStreamManager import AnomaliManager
from ..core.constants import INTEGRATION_NAME, ADD_TAGS_TO_ENTITIES_SCRIPT_NAME, EMAIL_TYPE
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.utils import string_to_multi_value, get_entity_original_identifier, get_entity_type
from soar_sdk.SiemplifyDataModel import EntityTypes

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EMAIL_TYPE,
]


def entity_exists_in_indicators(entity_identifier, indicators):
    return bool(
        list(
            filter(
                lambda indicator: (
                    entity_identifier.lower() == indicator.value.lower()
                ),
                indicators,
            )
        )
    )


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_TAGS_TO_ENTITIES_SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    web_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Root",
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Email Address",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    tags = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Tags", is_mandatory=True, print_value=True
        )
    )
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, indicators = [], [], []

    try:
        manager = AnomaliManager(
            web_root=web_root,
            api_root=api_root,
            username=username,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        try:
            siemplify.LOGGER.info(f"Retrieving indicators.")

            # Get indicators for entities
            indicators = manager.get_indicators(
                entities=[
                    get_entity_original_identifier(entity)
                    for entity in suitable_entities
                ]
            )
        except Exception as e:
            siemplify.LOGGER.error(f"Failed to get indicators.")
            siemplify.LOGGER.exception(e)

        if indicators:
            for entity in suitable_entities:
                entity_identifier = get_entity_original_identifier(entity)
                if not entity_exists_in_indicators(entity_identifier, indicators):
                    failed_entities.append(entity_identifier)
                    continue

                try:
                    entity_indicator = list(
                        filter(
                            lambda indicator: (
                                entity_identifier.lower() == indicator.value.lower()
                            ),
                            indicators,
                        )
                    )[0]
                    manager.add_tags_to_entity(
                        indicator_id=entity_indicator.id, tags=tags
                    )
                    successful_entities.append(entity_identifier)
                except Exception as e:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.error(
                        "An error occurred during adding tag for the following entity "
                        f"{entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                "Successfully added tags to the following entities in "
                f"{INTEGRATION_NAME}: {', '.join(successful_entities)}"
            )

            if failed_entities:
                output_message += (
                    f"\nThe following entities were not found in {INTEGRATION_NAME}: "
                    f"{', '.join(failed_entities)}"
                )

        else:
            output_message = "None of the provided entities were found."
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action '{ADD_TAGS_TO_ENTITIES_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
