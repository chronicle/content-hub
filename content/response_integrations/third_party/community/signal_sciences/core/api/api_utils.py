from __future__ import annotations

from urllib.parse import urljoin

import requests

from ..constants import ENDPOINTS
from ..exceptions import SignalSciencesIntegrationHTTPError


def get_full_url(api_root: str, endpoint_id: str, endpoints: dict[str, str] = None, **kwargs) -> str:
    endpoints = endpoints or ENDPOINTS
    return urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(response: requests.Response, error_msg: str = "An error occurred") -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        msg = f"{error_msg}: {error} {error.response.content}"
        raise SignalSciencesIntegrationHTTPError(msg, status_code=error.response.status_code) from error
