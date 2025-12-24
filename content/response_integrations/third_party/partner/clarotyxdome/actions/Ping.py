from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param
import requests

SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"Claroty xDome - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name="Claroty xDome",
        param_name="xdomeHost",  # Updated name, change if your UI uses another
        is_mandatory=True,
        print_value=True,
    )
    token = extract_configuration_param(
        siemplify,
        provider_name="Claroty xDome",
        param_name="xdomeApiToken",  # Updated name, change if your UI uses another
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name="Claroty xDome",
        param_name="Verify SSL",  # Use "Verify SSL", not verify_ssl, for metadata pattern
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        url = f"{api_root.rstrip('/')}/api/v1/alerts/"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"offset": 0, "limit": 1, "fields": ["id", "alert_name"]}
        response = requests.post(url, json=payload, headers=headers, verify=verify_ssl, timeout=10)
        response.raise_for_status()
        status = EXECUTION_STATE_COMPLETED  # This is 0
        output_message = (
            "Successfully connected to Claroty XDome with the provided connection parameters!"
        )
        result_value = True
    except Exception as e:
        siemplify.LOGGER.error(f"❌ Failed to connect to Claroty XDome. Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED  # This is 1
        output_message = f"Failed to connect to Claroty XDome. Error is {e}"
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
