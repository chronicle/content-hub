from __future__ import annotations
from urllib.parse import urljoin
import requests

from zerofox.core.constants import (
    ENDPOINTS,
    FAILED_TO_TAKE_REQUEST_DOWN_ERR,
    INVALID_ATTACHMENT_ERR,
    INVALID_TOKEN_ERROR,
)
from zerofox.core.exceptions import (
    AuthenticationError,
    RequestTakeDownError,
    UnsupportedAttachmentError,
    ZerofoxManagerError,
)


def get_full_url(api_root: str, url_id: str, **kwargs) -> str:
    return urljoin(api_root, ENDPOINTS[url_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg="An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error.
            Defaults to 'An error occurred'.
    """
    try:
        response.raise_for_status()

    except requests.exceptions.HTTPError as http_error:
        try:
            error_details = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ZerofoxManagerError("Invalid request.") from e

        if error_details.get("detail", "").lower() == INVALID_TOKEN_ERROR:
            raise AuthenticationError(
                "Authentication failed: Invalid API token."
            ) from http_error
        if FAILED_TO_TAKE_REQUEST_DOWN_ERR in error_details.get("error", "").lower():
            raise RequestTakeDownError(error_details.get("error")) from http_error
        if INVALID_ATTACHMENT_ERR in " ".join(error_details.get("file", [])).lower():
            raise UnsupportedAttachmentError(
                " ".join(error_details.get("file"))
            ) from http_error

        raise ZerofoxManagerError(
            f"{error_msg}: {http_error} {response.content}"
        ) from http_error
