from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AbuseIPDB import AbuseIPDBInvalidAPIKeyManagerError, AbuseIPDBManager

IDENTIFIER = "AbuseIPDB"
SCRIPT_NAME = "AbuseIPDB - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_key = siemplify.extract_configuration_param(siemplify, param_name="Api Key")
    verify_ssl = siemplify.extract_configuration_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        ipdb = AbuseIPDBManager(api_key, verify_ssl)
        status = EXECUTION_STATE_COMPLETED
        ipdb.test_connectivity()
        output_message = "Connection Established"
        result_value = "true"
        siemplify.LOGGER.info("Finished processing")

    except AbuseIPDBInvalidAPIKeyManagerError:
        siemplify.LOGGER.error("Invalid API key was provided. Access is forbidden.")
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = "Invalid API key was provided. Access is forbidden."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}",
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
