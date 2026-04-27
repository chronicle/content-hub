from __future__ import annotations
import requests
from .InternetStormCenterExceptions import (
    InternetStormCenterException,
    InvalidResponseException,
)
from soar_sdk.SiemplifyUtils import unix_now

TIMEOUT_THRESHOLD = 0.9
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()
        if "text/html" in response.headers.get("content-type", []):
            raise InvalidResponseException(
                "please check the configuration. Additionally, your IP might have been "
                "blocked."
            )
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise InternetStormCenterException(
                f"{error_msg}: {error} {error.response.content}"
            )

        raise InternetStormCenterException(
            f"{error_msg}: {error} {response.json().get('error') or response.content}"
        )


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


# Move to TIPCommon
def is_approaching_timeout(
    python_process_timeout, connector_starting_time, timeout_threshold=TIMEOUT_THRESHOLD
):
    """
    Check if a timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :param connector_starting_time: {int} The connector start unix time
    :param timeout_threshold: {int} Determines which part of the execution time is available for execution
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * timeout_threshold
