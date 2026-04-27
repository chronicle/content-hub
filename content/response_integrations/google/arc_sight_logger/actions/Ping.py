from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ArcSightLoggerManager import ArcSightLoggerManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param

from ..core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        input_type=str
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        input_type=str
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED

    try:
        arcsight_logger_manager = ArcSightLoggerManager(
            api_root,
            username,
            password,
            verify_ssl,
            siemplify_logger=siemplify.LOGGER
        )
        arcsight_logger_manager.login()
        arcsight_logger_manager.test_connectivity()
        output_message = (
            "Successfully connected to the ArcSight "
            "Logger with the provided connection parameters!"
        )
        connectivity_result = True
        siemplify.LOGGER.info(
            "Connection to API established, "
            f"performing action {PING_SCRIPT_NAME}"
        )
        arcsight_logger_manager.logout()

    except Exception as e:
        output_message = f'Error executing action "Ping". Reason: {e}'
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
