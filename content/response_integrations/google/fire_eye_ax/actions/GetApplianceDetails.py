from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from ..core.FireEyeAXManager import FireEyeAXManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    GET_APPLIANCE_DETAILS_SCRIPT_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_APPLIANCE_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = FireEyeAXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        details = manager.get_appliance_details()
        siemplify.result.add_result_json(details)
        output_message = (
            f"Successfully retrieved details about {INTEGRATION_DISPLAY_NAME}"
        )
        result = True
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = (
            f'Error executing action "{GET_APPLIANCE_DETAILS_SCRIPT_NAME}". Reason: {e}'
        )
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"General error performing action {GET_APPLIANCE_DETAILS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Status: {status}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
