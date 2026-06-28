# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import time
import urllib.parse
import uuid

import jwt

import requests

from okta.core.constants import (
    ENDPOINTS,
)

from okta.core.exceptions import (
    HTTPException,
)


def get_full_url(
    api_root: str, endpoint_id: str, endpoints: dict[str, str] = None, **kwargs
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
    return urllib.parse.urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        HTTPException: If there is any error in the response

    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise HTTPException(
            f"{error_msg}: {error} {error.response.content}",
            status_code=error.response.status_code,
        ) from error

def generate_jwt_assertion(
    client_id: str,
    base_uri: str,
    private_key: str,
    key_id: str | None = None
) -> str:
    """Generate a signed JWT assertion for OAuth 2.0 authentication.

    Args:
        client_id (str): The unique identifier for the Okta OAuth application.
        base_uri (str): The base URL of the Okta authorization server.
        private_key (str): The RSA private key in PEM format used for signing.
        key_id (str | None): The optional 'kid' header value for the public key.

    Returns:
        The encoded and signed JWT assertion string.
    """
    clean_base: str = base_uri.strip().rstrip("/")
    token_url: str = f"{clean_base}/oauth2/v1/token"

    payload: dict[str, str] = {
        "iss": client_id,
        "sub": client_id,
        "aud": token_url,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "jti": str(uuid.uuid4()),
    }

    jwt_headers: dict[str, str] = {}
    if key_id:
        jwt_headers["kid"] = key_id

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers=jwt_headers,
    )

def get_access_token(
    client_id: str,
    base_uri: str,
    private_key: str,
    session: requests.Session,
    key_id: str | None = None
) -> str:
    """Get OAuth 2.0 access token from Okta using a signed JWT assertion.

    Args:
        client_id (str): The unique identifier for the Okta OAuth application.
        base_uri (str): The base URL of the Okta authorization server
        private_key (str): The RSA private key in PEM format used for signing.
        session (requests.Session): The requests session object of the HTTP call.
        key_id (str | None): The optional 'kid' header value for the public key.

    Return:
        str: The access token string.
    """
    signed_jwt: str = generate_jwt_assertion(
        client_id=client_id,
        base_uri=base_uri,
        private_key=private_key,
        key_id=key_id
    )
    clean_base: str = base_uri.strip().rstrip("/")
    token_url: str = f"{clean_base}/oauth2/v1/token"

    payload: dict[str, str] = {
        "grant_type": "client_credentials",
        "scope": "okta.users.read okta.groups.read",
        "client_assertion_type": (
            "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
        ),
        "client_assertion": signed_jwt,
    }

    headers: dict[str, str] = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    response: requests.Response = session.post(token_url, data=payload, headers=headers)
    validate_response(response, "Failed to get OAuth token")

    return response.json().get("access_token")
