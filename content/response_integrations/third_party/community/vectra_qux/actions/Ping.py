from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

from ..core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
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
        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        vectra_manager.test_connectivity()
        output_message = "Successfully connected to the VectraQUX server!"
        connectivity_result = True
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {PING_SCRIPT_NAME}",
        )

    except Exception as e:
        output_message = f"Failed to connect to the Vectra server! {e}"
        connectivity_result = False
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {connectivity_result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
