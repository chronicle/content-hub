from __future__ import annotations
from urllib.parse import urljoin
import requests

from extrahop.core.constants import ENDPOINTS, INVALID_CREDS
from extrahop.core.ExtrahopExceptions import (
    ExtrahopException,
    InvalidCredentialsError,
    InvalidDetectionIDError,
)


def get_full_url(api_root: str, url_id: str, **kwargs) -> str:
    return urljoin(api_root, ENDPOINTS[url_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response.

    Args:
        response(requests.Response): The response to validate.
        error_msg(str): Default message to display on error
    """
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        try:
            error_details = response.json()
        except Exception as e:
            raise ExtrahopException(
                f"{error_msg}: {error} {error.response.content}"
            ) from e
        if INVALID_CREDS in error_details.get("error", "").lower():
            raise InvalidCredentialsError(
                "Please check the credentials. Either "
                'invalid "Client ID or Client Secret."'
            ) from error
        if response.status_code == 404:
            raise InvalidDetectionIDError("Detection not found.") from error

        raise ExtrahopException(
            f"{error_msg}: {error} {response.json().get('message') or response.content}"
        ) from error
