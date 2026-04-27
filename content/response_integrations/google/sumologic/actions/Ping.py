from __future__ import annotations
from TIPCommon import extract_configuration_param

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SumoLogicManager import SumoLogicManager
from ..core.consts import INTEGRATION_NAME, INTEGRATION_IDENTIFIER, PING_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {PING_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    access_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Access ID",
        is_mandatory=True,
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Access Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
        is_mandatory=True,
    )

    try:

        sumologic_manager = SumoLogicManager(
            server_address=api_root,
            access_id=access_id,
            access_key=access_key,
            verify_ssl=verify_ssl,
        )
        sumologic_manager.test_connectivity()
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Successfully connected to {INTEGRATION_NAME} with the provided connection parameters!"

    except Exception as error:
        output_message = (
            f"Failed to connect to the {INTEGRATION_NAME} server! Error is: {error}"
        )
        siemplify.LOGGER.exception(error)
        siemplify.LOGGER.error(output_message)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
