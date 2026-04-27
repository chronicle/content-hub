from __future__ import annotations
import requests
from .SnowflakeExceptions import SnowflakeException


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise SnowflakeException(f"{error_msg}: {error} {error.response.content}")

        raise SnowflakeException(
            f"{error_msg}: {error} {response.json().get('message') or response.content}"
        )
