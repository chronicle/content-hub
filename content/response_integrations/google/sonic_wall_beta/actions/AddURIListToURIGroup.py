from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SonicWallManager import SonicWallManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    ADD_URI_TO_GROUP_SCRIPT_NAME,
    NOT_FOUND_ERROR_CODE,
)

from ..core.SonicWallExceptions import UnableToAddException, UnauthorizedException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_URI_TO_GROUP_SCRIPT_NAME
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
    uri_group = extract_action_param(
        siemplify, param_name="URI Group Name", is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"

    try:
        sonic_wall_manager = SonicWallManager(
            api_root,
            username,
            password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        sonic_wall_manager.add_uri_list_to_uri_group(uri_list, uri_group)
        sonic_wall_manager.confirm_changes()
        output_message = f'Successfully added the URI List "{uri_list}" to the SonicWall URI Group "{uri_group}"'
        result_value = "true"

    except UnableToAddException as e:
        reason_message = str(e.args[0].message)
        command_message = str(e.args[0].command)
        error_code = str(e.args[0].code)
        if error_code == NOT_FOUND_ERROR_CODE:
            output_message = f'URI Group "{uri_group}" wasn\'t found in SonicWall'
        else:
            output_message = (
                'URI List "{}" was not added to the SonicWall URI Group "{}":\nReason: '
                "{} \nCommand: {}".format(
                    uri_list, uri_group, reason_message, command_message
                )
            )

    except UnauthorizedException as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        output_message = (
            f'Error executing action "Add URI List to URI Group". Reason: {e}'
        )
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
