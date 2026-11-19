from __future__ import annotations

import json
from urllib.parse import urljoin
import requests

from TIPCommon.types import SingleJson
from google_forms.core import exceptions
from google_forms.core import constants


def validate_response(
    response: SingleJson,
    error_msg: str | None = "An error occurred",
) -> None:
    """Validate Google Forms response

    Args:
        response(json/html): Response from Google Forms api
        error_msg(str): Error message to display.
    """
    try:
        if response.status_code == constants.API_BAD_REQUEST_STATUS_CODE:
            raise exceptions.GoogleFormsValidationException(
                f"{error_msg}: {response.json().get('error', {}).get('message')}"
            )
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            response.json()

        except json.JSONDecodeError as err:
            error_message = f"{error_msg}: {error.response.content}"
            raise exceptions.GoogleFormsManagerError(error_message) from err

        raise exceptions.GoogleFormsManagerError(
            f"{error_msg}: {response.json().get('error', {}).get('message')}"
        ) from error


def get_full_url(
    api_root: str,
    url_id: str,
    connector_api: bool = False,
    **kwargs,
) -> str:
    """Gets the full URL based on the provided URL ID.

    Args:
        url_id: The key of the URL in the ENDPOINTS or CONNECTOR_ENDPOINTS
        dictionary.
        connector_api:  A boolean indicating whether to use the connector API root
        or the main API root.
        **kwargs: Keyword arguments for string formatting.

    Returns:
        str: The full URL.
    """
    endpoints = constants.CONNECTOR_ENDPOINTS if connector_api else constants.ENDPOINTS
    return urljoin(api_root, endpoints[url_id].format(**kwargs))
