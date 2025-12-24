from __future__ import annotations

import json
import urllib

import requests
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "SupernaZeroTrust"
SCRIPT_NAME = "Cyber Lockout"


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("================= Main - Param Init =================")

    url = "https://"
    apiroute = "/sera/v2/ransomware/lockout/"
    apitoken = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="api_token",
    )
    eyeglassip = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="eyeglass_ip",
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        print_value=True,
        input_type=bool,
    )
    eyeglassip = eyeglassip.replace('"', "")
    apitoken = apitoken.replace('"', "")
    siemplify.LOGGER.info("debug api token " + apitoken)
    siemplify.LOGGER.info("debug eyeglass ip " + eyeglassip)
    user = siemplify.extract_action_param(param_name="UserName", print_value=True)
    user = urllib.parse.quote_plus(user)  ### url encode the username

    ##### build api to lockout the user ############
    apicall = url + eyeglassip + apiroute + user
    siemplify.LOGGER.info("debug api route " + apicall)

    siemplify.LOGGER.info("================= Lockout the user =================")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "api_key": apitoken,
    }
    siemplify.LOGGER.info("Headers (Pretty Printed):")
    siemplify.LOGGER.info(json.dumps(headers, indent=4, sort_keys=True))

    response = None
    try:
        response = requests.post(
            apicall,
            headers=headers,
            timeout=30,
            verify=verify_ssl,
        )
        response.raise_for_status()  # This will raise an HTTPError for bad responses

        siemplify.LOGGER.info("\nSuccessful Response:")
        siemplify.LOGGER.info(response.text)
        status = EXECUTION_STATE_COMPLETED
        result_value = response.text
        output_message = "Eyeglass Zero Trust API Call Successful"

    except requests.exceptions.Timeout:
        siemplify.LOGGER.info("The request timed out")
        status = EXECUTION_STATE_TIMEDOUT
        result_value = "Timeout"
        output_message = "Eyeglass Zero Trust API Call Timed Out"

    except requests.exceptions.ConnectionError:
        siemplify.LOGGER.info("Connection error occurred")
        status = EXECUTION_STATE_FAILED
        result_value = "Connection Error"
        output_message = "Eyeglass Zero Trust API Call Connection Failed"

    except requests.exceptions.HTTPError as e:
        siemplify.LOGGER.info(f"HTTP error occurred: {e}")
        status = EXECUTION_STATE_FAILED
        result_value = "HTTP Error"
        output_message = f"Eyeglass Zero Trust API Call HTTP Error: {e}"

    except requests.exceptions.RequestException as e:
        siemplify.LOGGER.info(f"An error occurred: {e}")
        status = EXECUTION_STATE_FAILED
        result_value = "Request Error"
        output_message = f"Eyeglass Zero Trust API Call Error: {e}"

    siemplify.LOGGER.info(
        f"\nstatus: {status}\nresult_value: {result_value}\noutput_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
