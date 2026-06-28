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

import dataclasses
import json
import time

import requests

from soar_sdk.SiemplifyAction import SiemplifyAction

import TIPCommon.encryption
from TIPCommon.base.interfaces import Session
from TIPCommon.base.utils import CreateSession
from TIPCommon.types import ChronicleSOAR
from TIPCommon.consts import GLOBAL_CONTEXT_SCOPE, NUM_OF_SEC_IN_MIN
from zoho_desk.core import ZohoDeskExceptions
from zoho_desk.core import constants


ACTION_BUFFER_TIME = NUM_OF_SEC_IN_MIN * 15


def get_access_token(siemplify: ChronicleSOAR, comps: AccessTokenComponents) -> str:
    """Get ZohoDesk access token if exist in cache and not expired, or create a new one

    Args:
        siemplify: Siemplify SDK object
        comps: The components for creating a refresh token

    Returns:
        The refresh token
    """
    cached_token: CachedAccessToken | None = _get_token_from_cache(siemplify)
    if cached_token is not None and _is_expiry_time_valid(cached_token.expiry_time):
        siemplify.LOGGER.info("Cached access token is valid and will be used")
        return _decrypt_token(cached_token.value, comps.client_secret)

    siemplify.LOGGER.info("Access token isn't found or expired, creating a new one")
    new_token: CachedAccessToken = _get_new_access_token(comps)

    encrypted_token: str = _encrypt_token(new_token.value, comps.client_secret)
    cache_value: str = json.dumps(new_token.to_cache(encrypted_token))
    _set_token_in_cache(siemplify, cache_value)

    return new_token.value


def _get_token_from_cache(siemplify: SiemplifyAction) -> CachedAccessToken | None:
    siemplify.LOGGER.info("Getting token from cache")
    cached_token: str = siemplify.get_context_property(
        context_type=GLOBAL_CONTEXT_SCOPE,
        identifier=constants.ACTION_IDENTIFIER,
        property_key=constants.ACCESS_TOKEN_DB_KEY,
    )
    if cached_token is not None:
        siemplify.LOGGER.info("Access token found")
        token = cached_token
        if isinstance(cached_token, str):
            token = json.loads(cached_token)

        return CachedAccessToken.from_cache(token)

    siemplify.LOGGER.info("No access token found")
    return None


def _is_expiry_time_valid(expiry_time: int) -> bool:
    return time.time() < expiry_time


def _get_new_access_token(components: AccessTokenComponents) -> CachedAccessToken:
    if not components.refresh_token:
        raise ZohoDeskExceptions.MissingRefreshTokenError(
            'In order to authenticate, you need to provide "Refresh Token". It can be '
            'generated via action "Get Refresh Token". For now you can put dummy data '
            "in that field. For more information, please visit our doc portal."
        )

    session: Session = CreateSession.create_session()
    response: requests.Response = session.post(
        constants.OAUTH_URL.format(region=components.region),
        data=components.to_json(),
        timeout=NUM_OF_SEC_IN_MIN,
    )
    _validate_access_token_response(response, "Unable to obtain access token")

    return CachedAccessToken.from_zoho_response_json(response.json())


def _set_token_in_cache(siemplify: SiemplifyAction, cache_value: str) -> None:
    siemplify.LOGGER.info("Setting new token in cache")
    siemplify.set_context_property(
        context_type=GLOBAL_CONTEXT_SCOPE,
        identifier=constants.ACTION_IDENTIFIER,
        property_key=constants.ACCESS_TOKEN_DB_KEY,
        property_value=cache_value,
    )


def _validate_access_token_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    try:
        response.raise_for_status()

        response_json = response.json()
        error_message = response_json.get(constants.ERROR_KEY)
        if error_message is None:
            error_message = response_json.get("errors")

        if (
            response.status_code == 200
            and constants.ERROR_KEY in response_json
            or "errors" in response_json
        ):
            raise ZohoDeskExceptions.ZohoDeskException(f"{error_msg}: {error_message}")

    except requests.HTTPError as he:
        response_json = response.json()
        error_message = response_json.get(constants.ERROR_KEY)
        if error_message is None:
            error_message = response_json.get("errors")

        raise ZohoDeskExceptions.ZohoDeskException(
            f"{error_msg}: {he} - {error_message}"
        ) from he

    except json.JSONDecodeError as jde:
        raise ZohoDeskExceptions.ZohoDeskException(
            f"Response could not be parsed to JSON. Response: {response.json()}"
        ) from jde


def _calc_expiry_time(expires_in: int) -> int:
    """Calculates the expiry time of the access token based on the expires_in value

    Args:
        expires_in: The expires_in value from the response

    Returns:
        The expiry time of the access token
    """
    return int(time.time()) + expires_in - NUM_OF_SEC_IN_MIN


def _encrypt_token(token: str, client_secret: str) -> str:
    return TIPCommon.encryption.encrypt(token, client_secret).decode()


def _decrypt_token(token: str, client_secret: str) -> str:
    return TIPCommon.encryption.decrypt(token.encode(), client_secret)


@dataclasses.dataclass
class CachedAccessToken:
    value: str
    expires_in: int = 0
    expiry_time: int = 0

    @classmethod
    def from_zoho_response_json(cls, json_: dict[str, str | int]) -> CachedAccessToken:
        expires_in: int = json_.get("expires_in", 0)
        return cls(
            value=json_["access_token"],
            expires_in=expires_in,
            expiry_time=_calc_expiry_time(expires_in),
        )

    @classmethod
    def from_cache(cls, json_: dict[str, str | int]) -> CachedAccessToken:
        return cls(
            value=json_["token"],
            expires_in=json_["expires_in"],
            expiry_time=json_["valid_until"],
        )

    def to_cache(self, encrypted_token: str) -> dict[str, str | int]:
        return {
            "token": encrypted_token,
            "expires_in": self.expires_in,
            "valid_until": self.expiry_time,
        }


@dataclasses.dataclass
class AccessTokenComponents:
    region: str
    client_id: str
    client_secret: str
    refresh_token: str

    def to_json(self) -> dict[str, str]:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
