from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

from ..core.constants import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME
from ..core.TrendmicroDeepSecurityManager import TrendmicroManager


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Secret Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    api_version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Version",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        manager = TrendmicroManager(
            api_root=api_root,
            api_secret_key=api_key,
            api_version=api_version,
            verify_ssl=verify_ssl,
        )
        manager.test_connectivity()
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            "Successfully connected to the "
            f"{INTEGRATION_DISPLAY_NAME} server with the provided "
            "connection parameters!"
        )

    except Exception as error:
        siemplify.LOGGER.error("General error performing action " f"{PING_SCRIPT_NAME}")
        siemplify.LOGGER.exception(error)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME}"
            f"server! Error is {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
