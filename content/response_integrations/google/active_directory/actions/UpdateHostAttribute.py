from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.ActiveDirectoryManager import (
    ActiveDirectoryManager,
    ActiveDirectoryNotFoundManagerError,
    ActiveDirectoryNotExistPropertyError,
)

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "ActiveDirectory"
SCRIPT_NAME = "ActiveDirectory - UpdateHostAttribute"

SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    result_value = False
    successful_entities = []
    missing_entities = []
    failed_entities = []
    not_updated_entities = []
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATIONS:
    server = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Server",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Username",
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Password",
        input_type=str,
    )
    domain = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Domain",
        input_type=str,
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Use SSL",
        input_type=bool,
    )
    custom_query_fields = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Custom Query Fields",
        input_type=str,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    # INIT ACTION CONFIGURATIONS:
    attribute_name = extract_action_param(
        siemplify,
        param_name="Attribute Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    attribute_value = extract_action_param(
        siemplify,
        param_name="Attribute Value",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = ActiveDirectoryManager(
            server,
            domain,
            username,
            password,
            use_ssl,
            custom_query_fields,
            ca_certificate,
            siemplify.LOGGER,
        )
        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
        if target_entities:
            for entity in target_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    manager.update_host(
                        entity.identifier, attribute_name, attribute_value
                    )
                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

                except ActiveDirectoryNotExistPropertyError as e:
                    not_updated_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

                except ActiveDirectoryNotFoundManagerError as e:
                    # Entity was not found in AD
                    siemplify.LOGGER.info(e)
                    missing_entities.append(entity)

                except Exception as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

            if successful_entities:
                output_message += "Successfully updated attribute for the following entities:\n   {} \n".format(
                    "\n   ".join([entity.identifier for entity in successful_entities])
                )
                result_value = True
            else:
                siemplify.LOGGER.info("\n No entities were updated.")
                output_message = "No entities were updated."

            if missing_entities:
                output_message += "\nThe following entities were not found in Active Directory:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in missing_entities])
                )

            if failed_entities:
                output_message += (
                    "\nFailed to update {} for the following entities:\n   {}".format(
                        attribute_name,
                        "\n   ".join([entity.identifier for entity in failed_entities]),
                    )
                )

            if not_updated_entities:
                output_message += (
                    "\nFailed updating the  attribute for the following entities: \n {} \n "
                    "Please make sure the attribute you are trying to update is not a unique "
                    "attribute, or a non-editable attribute , and try again".format(
                        "\n".join(
                            [entity.identifier for entity in not_updated_entities]
                        )
                    )
                )
        else:
            output_message = "No suitable entities found.\n"

    except Exception as e:
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
