from __future__ import annotations

import json

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

BASE_URL = "https://api.logz.io/"
WHOAMI_API_SUFFIX = "v1/account-management/whoami"

"""
This action validates the tokens and sends a request to Logz.io's API,
that should return 200 if the token is valid and the connection to the API is established
"""


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_FAILED
    is_success = False
    security_token = siemplify.extract_configuration_param(
        "Logzio",
        "logzio_security_token",
        default_value="-",
        is_mandatory=True,
    )
    operations_token = siemplify.extract_configuration_param(
        "Logzio",
        "logzio_operations_token",
        default_value="-",
        is_mandatory=True,
    )
    logzio_region = siemplify.extract_configuration_param(
        "Logzio",
        "logzio_region",
        default_value="",
    )

    try:
        validate_token(siemplify, security_token)
        validate_token(siemplify, operations_token)
        ping_api(siemplify, logzio_region, operations_token)
        ping_api(siemplify, logzio_region, security_token)
        status = EXECUTION_STATE_COMPLETED
        is_success = True
    except Exception as e:
        siemplify.LOGGER.error(f"Error occurred. {e}")

    output_message = create_output_msg(status)
    siemplify.end(output_message, is_success, status)


def validate_token(siemplify, token):
    """Minimum validation of the tokens -
    Checks that they have a value and that they're strings
    """
    if token is None or token == "-" or token == "":
        raise ValueError("Must insert Logzio operations & security tokens")
    if type(token) is not str:
        raise TypeError("Logzio tokens must be strings")
    siemplify.LOGGER.info(f"Valid token: {token}")
    return True


def ping_api(siemplify, logzio_region, token):
    """Creates a request to Logz.io API.
    If request is valid, returnes True, otherwise raises a ConnectionError.
    """
    url = get_logzio_api_endpoint(siemplify, logzio_region)
    headers = {"Content-Type": "application/json", "X-API-TOKEN": token}

    try:
        siemplify.LOGGER.info(f"Sending request to {url}")
        response = requests.get(url, headers=headers, timeout=5)
        if response is not None:
            siemplify.LOGGER.info(
                f"Logz.io returned status code: {response.status_code}",
            )
            if response.status_code == 200:
                accountName = json.loads(response.content)
                siemplify.LOGGER.info(
                    f"Logz.io response returned account name: {accountName['accountName']}",
                )
                return True
            raise ConnectionError(f"Logz.io returned {response.status_code}")
        raise ConnectionError("Logz.io response is None")
    except Exception as e:
        raise ConnectionError(f"Error occurred while trying to ping API:\n{e}")


def get_base_api_url(region):
    """Returnes API url, in accordance to user's input"""
    if region == "us" or region == "" or region == "-":
        return BASE_URL
    return BASE_URL.replace("api.", f"api-{region}.")


def create_output_msg(status):
    """Returns output message in accordance to the status"""
    if status == EXECUTION_STATE_COMPLETED:
        return "Tokens are valid, ping successful."
    return "Error occurred while trying to validate tokens or ping Logz.io API"


def get_logzio_api_endpoint(siemplify, region):
    """Returns the endpoint of Logz.io API.
    Prioritizing a custom endoint, if entered.
    If not, falling back to the regaular enspoints, based on the logzio_region (defaults to us).
    """
    custom_endpoint = siemplify.extract_configuration_param(
        "Logzio",
        "logzio_custom_endpoint",
        is_mandatory=False,
        default_value="",
    )
    if custom_endpoint is not None and custom_endpoint != "":
        siemplify.LOGGER.info(f"Using custom endpoint: {custom_endpoint}")
        return custom_endpoint + WHOAMI_API_SUFFIX
    return get_base_api_url(region) + WHOAMI_API_SUFFIX


if __name__ == "__main__":
    main()
