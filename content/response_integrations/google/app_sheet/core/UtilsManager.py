from __future__ import annotations
import requests


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """

    try:
        # The product returns status code 200, but nothing in the response.
        # If there is nothing in the response, an error related to the payload occured
        response.json()
    except Exception as error:
        raise Exception(
            "Invalid payload was provided. Please check the spelling of Table Name and "
            "structure of the JSON object of the record"
        ) from error

    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}") from error

    return True
