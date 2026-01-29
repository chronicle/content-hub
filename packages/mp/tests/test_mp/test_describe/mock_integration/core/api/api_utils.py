from __future__ import annotations

import json
from urllib.parse import urljoin

import requests

from ..constants import ENDPOINTS
from ..exceptions import InvalidRequestParametersError, SampleIntegrationHTTPError


def get_full_url(
    api_root: str,
    endpoint_id: str,
    endpoints: dict[str, str] = None,
    **kwargs,
) -> str:
    """Construct the full URL using a URL identifier and optional variables

    Args:
        api_root (str): The root of the API endpoint
        endpoint_id (str): The identifier for the specific URL
        endpoints (dict[str, str]): endpoints dictionary object
        kwargs (dict): Variables passed for string formatting

    Returns:
        str: The full URL constructed from API root, endpoint identifier and variables

    """
    endpoints = endpoints or ENDPOINTS
    return urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        SampleIntegrationHTTPException: If there is any error in the response

    """
    try:
        if response.status_code == 422:
            errors = response.json().get("query", {})
            err_msg = json.dumps(errors) if errors else "Unknown Error"
            raise InvalidRequestParametersError(err_msg)

        response.raise_for_status()

    except requests.HTTPError as error:
        msg = f"{error_msg}: {error} {error.response.content}"
        raise SampleIntegrationHTTPError(
            msg,
            status_code=error.response.status_code,
        ) from error
