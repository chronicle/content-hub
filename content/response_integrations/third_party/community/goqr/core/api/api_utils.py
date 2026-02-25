from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests

from ..constants import ENDPOINTS
from ..exceptions import GOQRHTTPError

if TYPE_CHECKING:
    pass


def get_full_url(
    api_root: str,
    endpoint_id: str,
    endpoints: dict[str, str] = None,
    **kwargs,
) -> str:
    """Construct the full URL using a URL identifier and optional variables"""
    endpoints = endpoints or ENDPOINTS
    return urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response"""
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            response_json = response.json()
            error_details = response_json.get("error", response.text)
        except json.JSONDecodeError:
            error_details = response.text

        msg = f"{error_msg}: {error} {error_details}"
        raise GOQRHTTPError(
            msg,
            status_code=error.response.status_code,
        ) from error
