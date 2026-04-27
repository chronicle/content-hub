from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.WhoisManager import WhoisManager
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "BulkWhoIS"
SCRIPT_NAME = "BulkWhoIS - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )
    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        is_mandatory=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        whois = WhoisManager(api_key, api_secret, verify_ssl=verify_ssl)
        status = EXECUTION_STATE_COMPLETED
        is_connected = whois.test_connectivity()

        if is_connected:
            output_message = "Connection Established"
            result_value = "true"
            siemplify.LOGGER.info("Finished processing")
        else:
            output_message = "Connection Failed"
            result_value = "false"
            status = EXECUTION_STATE_FAILED
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = "Some errors occurred. Please check log"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
