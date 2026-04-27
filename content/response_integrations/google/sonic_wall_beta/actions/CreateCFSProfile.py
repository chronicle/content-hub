from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SonicWallManager import SonicWallManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, CREATE_CFS_SCRIPT_NAME

from ..core.SonicWallExceptions import UnableToAddException, UnauthorizedException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_CFS_SCRIPT_NAME
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
    profile_name = extract_action_param(siemplify, param_name="Name", is_mandatory=True)
    allowed_uri = extract_action_param(
        siemplify, param_name="Allowed URI List or Group", is_mandatory=False
    )
    forbidden_uri = extract_action_param(
        siemplify, param_name="Forbidden URI List or Group", is_mandatory=False
    )
    search_order = extract_action_param(
        siemplify,
        param_name="Search Order",
        default_value="Allowed URI First",
        is_mandatory=True,
    )
    forbidden_operation = extract_action_param(
        siemplify,
        param_name="Operation for Forbidden URI",
        default_value="Block",
        is_mandatory=True,
    )
    smart_filter = extract_action_param(
        siemplify,
        param_name="Enable Smart Filter",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    google_search = extract_action_param(
        siemplify,
        param_name="Enable Google Safe Search",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    youtube_mode = extract_action_param(
        siemplify,
        param_name="Enable Youtube Restricted Mode",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    bing_search = extract_action_param(
        siemplify,
        param_name="Enable Bing Safe Search",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
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
        sonic_wall_manager.create_cfs_profile(
            profile_name=profile_name,
            allowed=allowed_uri,
            forbidden=forbidden_uri,
            search_order=search_order,
            forbidden_operation=forbidden_operation,
            smart_filter=smart_filter,
            safe_search=google_search,
            youtube_mode=youtube_mode,
            bing_search=bing_search,
        )
        sonic_wall_manager.confirm_changes()
        output_message = f'Successfully created SonicWall CFS Profile "{profile_name}"'
        result_value = "true"

    except UnableToAddException as e:
        reason_message = str(e.args[0].message)
        command_message = str(e.args[0].command)
        output_message = f'CFS Profile "{profile_name}" was not created in SonicWall:\nReason: {reason_message} \nCommand: {command_message}'

    except UnauthorizedException as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        output_message = f'Error executing action "Create CFS Profile". Reason: {e}'
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
