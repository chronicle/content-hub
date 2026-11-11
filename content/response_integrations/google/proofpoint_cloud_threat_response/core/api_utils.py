from __future__ import annotations

from urllib.parse import urljoin
from json import JSONDecodeError
import requests

from proofpoint_cloud_threat_response.core.constants import ENDPOINTS
from proofpoint_cloud_threat_response.core.exceptions import ProofpointCTRError, ProofpointCTRRateLimitError


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


def validate_response(response: requests.Response):
    """
    Validate response
    :param response: {Response} The response to validate
    """
    try:
        response.raise_for_status()

    except Exception as e:
        try:
            message = response.json().get("errorMessage", response.text)

        except JSONDecodeError:
            message = response.text

        if response.status_code == 429:
            raise ProofpointCTRRateLimitError(
                f"ProofPointCTR API rate limit exceeded. Reason: {message}"
            ) from e

        raise ProofpointCTRError(f"{response.status_code}: {message}") from e
