from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SonicWallManager import SonicWallManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param
from ..core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME
from ..core.SonicWallExceptions import UnauthorizedException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    try:
        sonic_wall_manager = SonicWallManager(
            api_root,
            username,
            password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        sonic_wall_manager.test_connectivity()
        output_message = "Successfully connected to the SonicWall server with the provided connection parameters!"
        connectivity_result = True
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {PING_SCRIPT_NAME}"
        )

    except UnauthorizedException as e:
        output_message = str(e)
        connectivity_result = False
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
    except Exception as e:
        output_message = f"Failed to connect to the SonicWall server! Error is {e}"
        connectivity_result = False
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {connectivity_result}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
