from __future__ import annotations

from typing import Any

import requests

from .constants import (
    API_VERSION_V2,
    DEFAULT_TOKEN_EXPIRES_IN_SECONDS,
    DOPPEL_CLIENT_HEADER,
    HTTP_TIMEOUT_SECONDS,
    OAUTH_AUDIENCE,
    OAUTH_TOKEN_URL,
)
from .exceptions import DoppelConfigError, DoppelHttpError
from .token_cache import TokenCache


def _oauth_error_message(payload: Any, status_code: int) -> str:
    detail = None
    if isinstance(payload, dict):
        detail = payload.get("error_description") or payload.get("error") or payload.get("message")
    suffix = f": {detail}" if detail else ""
    return (
        f"OAuth token request failed (HTTP {status_code}){suffix}. "
        "Check Client ID and Client Secret on the Version 2 tab of Doppel Vision API Settings."
    )


class AuthProviderV2:
    version = API_VERSION_V2

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_cache: TokenCache | None = None,
        session: requests.Session | None = None,
    ) -> None:
        if not client_id or not client_secret:
            raise DoppelConfigError("Client ID and Client Secret are required for API v2")
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_cache = token_cache or TokenCache()
        self.session = session or requests.Session()

    def get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        token = None if force_refresh else self.token_cache.get_token()
        if not token:
            token = self._mint_token()
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def invalidate_token(self) -> None:
        self.token_cache.invalidate()

    def _mint_token(self) -> str:
        try:
            response = self.session.post(
                OAUTH_TOKEN_URL,
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "audience": OAUTH_AUDIENCE,
                    "grant_type": "client_credentials",
                },
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "x-doppel-client": DOPPEL_CLIENT_HEADER,
                },
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise DoppelHttpError(0, "OAuth token request failed") from exc

        payload: Any
        try:
            payload = response.json() if response.content else {}
        except ValueError:
            payload = {}

        if not response.ok:
            raise DoppelHttpError(response.status_code, _oauth_error_message(payload, response.status_code))

        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        if not access_token:
            raise DoppelHttpError(response.status_code, "OAuth token response did not include access_token")

        expires_in = payload.get("expires_in") if isinstance(payload, dict) else None
        try:
            expires_in_int = int(expires_in) if expires_in else DEFAULT_TOKEN_EXPIRES_IN_SECONDS
        except (TypeError, ValueError):
            expires_in_int = DEFAULT_TOKEN_EXPIRES_IN_SECONDS

        self.token_cache.set_token(access_token, expires_in_int)
        return access_token
