from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core import exceptions
from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from TIPCommon import extract_script_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "Netskope"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    config = siemplify.get_configuration(INTEGRATION_NAME)

    v1_api_key = extract_script_param(
        siemplify,
        input_dictionary=config,
        param_name="V1 Api Key",
        is_mandatory=False,
    )
    v2_api_key = extract_script_param(
        siemplify,
        input_dictionary=config,
        param_name="V2 Api Key",
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    siemplify.LOGGER.info("Starting to perform the action")
    status = EXECUTION_STATE_FAILED
    connectivity_result = False

    try:
        if not v1_api_key and not v2_api_key:
            raise exceptions.NetskopeParamError(
                "Either V1 or V2 API Key needs to be provided"
            )
        if v1_api_key:
            v1_manager = NetskopeManagerFactory.get_manager(siemplify, api_version="v1")
            v1_manager.test_connectivity()
        if v2_api_key:
            v2_manager = NetskopeManagerFactory.get_manager(siemplify, api_version="v2")
            v2_manager.test_connectivity()
        connectivity_result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = "Connected successfully."
        siemplify.LOGGER.info("Finished performing the action")
    except exceptions.NetskopeParamError as e:
        output_message = f"Failed to connect to the {INTEGRATION_NAME}! Error: {e}"
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = f"Failed to connect to the {INTEGRATION_NAME}! Error is {e}"
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {connectivity_result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
