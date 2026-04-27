from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.ExabeamAdvancedAnalyticsManager import ExabeamAdvancedAnalyticsManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ADD_ENTITY_COMMENT_SCRIPT_NAME,
    ENTITY_USER_TYPE,
    ENTITY_ASSET_TYPE,
)
from ..core.exceptions import ExabeamAdvancedAnalyticsNotFoundError

SUPPORTED_ENTITIES = [EntityTypes.USER, EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ADD_ENTITY_COMMENT_SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action configuration
    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    successful_entities = []
    failed_entities = []
    json_results = []

    try:
        manager = ExabeamAdvancedAnalyticsManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Checking if entity {entity.identifier} exists")
                entity_type = (
                    ENTITY_USER_TYPE
                    if entity.entity_type == EntityTypes.USER
                    else ENTITY_ASSET_TYPE
                )

                entity_details = manager.get_entity_details(
                    entity_type=entity_type, entity_identifier=entity.identifier
                )

                if not entity_details.exists:
                    raise ExabeamAdvancedAnalyticsNotFoundError(
                        f"Entity {entity.identifier} wasn't found in {INTEGRATION_DISPLAY_NAME}"
                    )

                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} found to exist in {INTEGRATION_DISPLAY_NAME}"
                )
                siemplify.LOGGER.info(f"Adding comment to entity {entity.identifier}")

                if entity_type == ENTITY_USER_TYPE:
                    entity_comment = manager.add_entity_comment(
                        entity_type=entity_type,
                        entity_identifier=entity_details.username,
                        comment=comment,
                    )
                else:
                    entity_comment = manager.add_entity_comment(
                        entity_type=entity_type,
                        entity_identifier=entity_details.host_name,
                        comment=comment,
                    )

                json_results.append(entity_comment.as_json())
                successful_entities.append(entity)

                siemplify.LOGGER.info(
                    f"Successfully submitted comment for entity: {entity.identifier}"
                )

            except Exception as error:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(error)

        if successful_entities:
            output_message += "Successfully added comment to the following entities in {}:\n   {}\n\n".format(
                INTEGRATION_DISPLAY_NAME,
                "\n   ".join([entity.identifier for entity in successful_entities]),
            )
            siemplify.result.add_result_json(json_results)
            result_value = True
        else:
            output_message += "No comments were added to the provided entities."

        if failed_entities and successful_entities:
            output_message += "Action wasn't able to add comment to the following entities in {}:\n   {}\n\n".format(
                INTEGRATION_DISPLAY_NAME,
                "\n   ".join([entity.identifier for entity in failed_entities]),
            )

    except Exception as error:
        output_message = f'Error executing action "{ADD_ENTITY_COMMENT_SCRIPT_NAME}". Reason: {error}'
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
