from __future__ import annotations

from urllib.parse import urljoin
from json import JSONDecodeError
import requests

from proofpoint_threat_protection.core.constants import (
    BAD_REQUEST_STATUS_CODE,
    ENDPOINTS,
    RATE_LIMIT_STATUS_CODE,
)
from proofpoint_threat_protection.core.exceptions import ProofpointTPError, ProofpointTPRateLimitError


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


def validate_response(response: requests.Response) -> None:
    """
    Validate response
    :param response: {Response} The response to validate
    """
    try:
        response.raise_for_status()

    except Exception as e:
        try:
            message = response.json().get("errorMessage", response.text)
            if (
                response.status_code == BAD_REQUEST_STATUS_CODE
                and response.json().get("error_code") == "invalid_client"
            ):
                raise ProofpointTPError(
                    "Invalid credentials provided. "
                    "Please check the integration configuration."
                ) from e

        except JSONDecodeError:
            message = response.text

        if response.status_code == RATE_LIMIT_STATUS_CODE:
            raise ProofpointTPRateLimitError(
                f"ProofPointCTR API rate limit exceeded. Reason: {message}"
            ) from e

        raise ProofpointTPError(f"{response.status_code}: {message}") from e
