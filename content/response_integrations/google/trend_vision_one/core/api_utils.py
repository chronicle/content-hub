from __future__ import annotations

from typing import Any

import requests

from .TrendVisionOneExceptions import TrendVisionOneException


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error

    Raises:
        TrendVisionOneException: If the response status is not successful.
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            error_content: dict[str, Any] = response.json()
            error_message: str = error_content["error"]["message"]
            raise TrendVisionOneException(error_message) from error

        except (ValueError, KeyError):
            pass

        raise TrendVisionOneException(
            f"{error_msg}: {error} {error.response.content}"
        ) from error
