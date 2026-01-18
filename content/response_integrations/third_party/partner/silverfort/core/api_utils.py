"""API utility functions for Silverfort integration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests

from .constants import ENDPOINTS
from .exceptions import SilverfortAPIError, SilverfortHTTPError

if TYPE_CHECKING:
    from collections.abc import Mapping


def get_full_url(
    api_root: str,
    endpoint_id: str,
    endpoints: Mapping[str, str] | None = None,
    **kwargs,
) -> str:
    """Construct the full URL using a URL identifier and optional variables.

    Args:
        api_root: The root of the API endpoint.
        endpoint_id: The identifier for the specific URL.
        endpoints: Optional endpoints dictionary (defaults to ENDPOINTS).
        **kwargs: Variables passed for string formatting.

    Returns:
        The full URL constructed from API root, endpoint identifier and variables.
    """
    endpoints = endpoints or ENDPOINTS
    endpoint = endpoints[endpoint_id].format(**kwargs)
    return urljoin(api_root + "/", endpoint.lstrip("/"))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate API response and raise appropriate exceptions on errors.

    Args:
        response: Response to validate.
        error_msg: Default message to display on error.

    Raises:
        SilverfortAPIError: If there is an API-specific error.
        SilverfortHTTPError: If there is an HTTP error.
    """
    try:
        if response.status_code == 422:
            try:
                error_data = response.json()
                detail = error_data.get("detail", error_data.get("message", "Unknown Error"))
                raise SilverfortAPIError(
                    f"Invalid request parameters: {detail}",
                    error_code="VALIDATION_ERROR",
                    details=error_data,
                )
            except json.JSONDecodeError:
                raise SilverfortAPIError(
                    f"Invalid request parameters: {response.text}",
                    error_code="VALIDATION_ERROR",
                )

        if response.status_code == 401:
            raise SilverfortHTTPError(
                "Authentication failed. Please verify your API credentials.",
                status_code=401,
            )

        if response.status_code == 403:
            raise SilverfortHTTPError(
                "Access forbidden. Please verify your API permissions.",
                status_code=403,
            )

        if response.status_code == 404:
            try:
                error_data = response.json()
                detail = error_data.get("detail", error_data.get("message", "Resource not found"))
                raise SilverfortAPIError(
                    detail,
                    error_code="NOT_FOUND",
                    details=error_data,
                )
            except json.JSONDecodeError:
                raise SilverfortAPIError("Resource not found", error_code="NOT_FOUND")

        response.raise_for_status()

    except requests.HTTPError as error:
        msg = f"{error_msg}: {error}"
        if error.response is not None:
            try:
                error_content = error.response.json()
                msg = f"{error_msg}: {error_content}"
            except json.JSONDecodeError:
                content = error.response.content.decode("utf-8", errors="ignore")
                msg = f"{error_msg}: {error} - {content}"

        raise SilverfortHTTPError(
            msg,
            status_code=error.response.status_code if error.response else None,
        ) from error
