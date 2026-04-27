from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SonicWallManager import SonicWallManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.constants import INTEGRATION_NAME, ADD_URL_SCRIPT_NAME, NOT_FOUND_ERROR_CODE

from ..core.SonicWallExceptions import UnableToAddException, UnauthorizedException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_URL_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        input_type=str,
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        input_type=str,
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Parameters
    uri_list = extract_action_param(
        siemplify, param_name="URI List Name", is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    output_message = ""
    successful_entities = []
    failed_entities = []
    uri_list_exists = True

    try:
        sonic_wall_manager = SonicWallManager(
            api_root,
            username,
            password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        url_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.URL
        ]
        for entity in url_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                sonic_wall_manager.add_url_to_uri_list(uri_list, entity.identifier)
                sonic_wall_manager.confirm_changes()
                successful_entities.append(entity)
            except UnableToAddException as e:
                reason_message = str(e.args[0].message)
                command_message = str(e.args[0].command)
                error_code = str(e.args[0].code)
                if error_code == NOT_FOUND_ERROR_CODE:
                    uri_list_exists = False
                    break
                else:
                    failed_entities.append(
                        {
                            "entity": entity,
                            "reason": reason_message,
                            "command": command_message,
                        }
                    )

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if successful_entities:
            output_message = 'Successfully added the following URLs to the SonicWall URI List "{}": {}'.format(
                uri_list,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if failed_entities:
            for item in failed_entities:
                output_message += (
                    '\n\nAction was not able to add the following URL to the SonicWall URI List "{}"'
                    ": {}. \nReason: {}. Command: {}.".format(
                        uri_list,
                        item.get("entity"),
                        item.get("reason"),
                        item.get("command"),
                    )
                )

        if not successful_entities:
            output_message = ""
            for item in failed_entities:
                output_message += (
                    '\nURL was not added to the SonicWall URI List "{}"'
                    ": {}. \nReason: {}. Command: {}.".format(
                        uri_list,
                        item.get("entity"),
                        item.get("reason"),
                        item.get("command"),
                    )
                )
            result_value = "false"

        if not url_entities:
            output_message = "No suitable entities found"
            result_value = "false"

        if not uri_list_exists:
            output_message = f'URI List "{uri_list}" wasn\'t found in SonicWall'
            result_value = "false"

    except UnauthorizedException as e:
        output_message = str(e)
        result_value = "false"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        output_message = f'Error executing action "Add URL to URI List". Reason: {e}'
        result_value = "false"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
