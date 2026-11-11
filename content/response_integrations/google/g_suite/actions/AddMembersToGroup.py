from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_comma_separated_to_list

from g_suite.core.action_init import create_api_client
from g_suite.core.consts import INTEGRATION_NAME, ADD_MEMBERS_TO_GROUP_SCRIPT_NAME
from g_suite.core.exceptions import GSuiteEntityExistsException

SUPPORTED_ENTITIES = [EntityTypes.USER]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ADD_MEMBERS_TO_GROUP_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    group_email_address = extract_action_param(
        siemplify, param_name="Group Email Address", is_mandatory=True, print_value=True
    )
    user_email_addresses = convert_comma_separated_to_list(
        extract_action_param(
            siemplify, param_name="User Email Addresses", print_value=True
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    successful_entities = []
    failed_entities = []
    existing_entities = []

    json_results = []
    try:
        gsuite_manager = create_api_client(siemplify)

        suitable_entities = [
            entity.identifier.lower()
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITIES
        ]
        user_email_addresses = [email.lower() for email in user_email_addresses]
        suitable_entities = set(suitable_entities + user_email_addresses)

        for entity in suitable_entities:

            siemplify.LOGGER.info(f"Adding member {entity.strip()} to group")
            try:
                member = gsuite_manager.add_member_to_group(
                    group_email_address=group_email_address,
                    primary_email_address=entity.strip(),
                )
                json_results.append(member.as_json())
                successful_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Member {entity.strip()} was successfully added to \
                    group"
                )
            except GSuiteEntityExistsException as error:
                existing_entities.append(entity)
                siemplify.LOGGER.error(f"Member {entity} already exists in group")
                siemplify.LOGGER.exception(error)

            except Exception as error:
                siemplify.LOGGER.error(f"Failed to add member {entity} to group")
                siemplify.LOGGER.exception(error)
                failed_entities.append(entity)

        if successful_entities:
            siemplify.result.add_result_json(json_results)
            formatted_entities = "\n   ".join(successful_entities)
            output_message = (
                "The following users were added to the group:"
                f"\n   {formatted_entities}\n\n"
            )
        else:
            output_message = "No users were added to the group.\n\n"

        if existing_entities:
            formatted_entities = "\n   ".join(existing_entities)
            output_message += (
                "The following members already exist in group:"
                f"\n   {formatted_entities}\n\n"
            )

        if failed_entities:
            formatted_entities = "\n   ".join(failed_entities)
            output_message += (
                "Action failed to add the following members to group:"
                f"\n   {formatted_entities}"
            )

    except Exception as error:
        output_message = (
            f"Error executing action {ADD_MEMBERS_TO_GROUP_SCRIPT_NAME}."
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
