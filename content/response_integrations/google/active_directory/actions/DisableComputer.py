from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.ActiveDirectoryManager import (
    ActiveDirectoryManager,
    ActiveDirectoryNotFoundManagerError,
)

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "ActiveDirectory"
SCRIPT_NAME = "ActiveDirectory - DisableComputer"

SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    result_value = False
    successful_entities = []
    failed_entities = []
    missing_entities = []
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
                    if manager.disable_computer(entity.identifier):
                        successful_entities.append(entity)
                    else:
                        failed_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

                except ActiveDirectoryNotFoundManagerError as e:
                    # Entity was not found in AD
                    siemplify.LOGGER.info(e)
                    missing_entities.append(entity)

                except Exception as e:
                    output_message += (
                        f"Disable account for entity {entity.identifier}: \n"
                    )
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)
            if successful_entities:
                output_message += "Active Directory - Disabled computer for following entities: \n   {} \n".format(
                    "\n   ".join([entity.identifier for entity in successful_entities])
                )
                result_value = True
            else:
                siemplify.LOGGER.info("\n No entities were processed.")
                output_message = "No entities were processed."

            if missing_entities:
                output_message += "\nThe following entities were not found in Active Directory:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in missing_entities])
                )

            if failed_entities:
                output_message += "\nFailed processing entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
        else:
            output_message = "No suitable entities found.\n"
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
