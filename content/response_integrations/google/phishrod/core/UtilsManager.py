from __future__ import annotations
import requests
from requests import Response

from ..core.PhishrodExceptions import PhishrodException
from ..core.constants import FORBIDDEN_STATUS
from ..core.exceptions import PhishrodUnauthorizedError


def validate_response(response: Response, error_msg: str = "An error occurred") -> None:
    """
    Validates response

    Args:
        response: The response to validate
        error_msg: Default message to display on error

    Returns:
        None
    """
    phishrod_code_key = "code"
    phishrod_status_key = "status"
    phishrod_bad_request_code = "400"
    try:
        response.raise_for_status()

        response_dict = response.json()
        if (
            phishrod_code_key in response_dict
            and response_dict[phishrod_code_key] == phishrod_bad_request_code
        ):
            raise requests.HTTPError(
                response_dict.get(phishrod_status_key), response=response
            )

    except requests.HTTPError as error:
        if response.status_code == FORBIDDEN_STATUS:
            raise PhishrodUnauthorizedError(
                "Credentials is invalid or expired."
            ) from error
        raise PhishrodException(
            f"{error_msg}: {error} {error.response.content}"
        ) from error
