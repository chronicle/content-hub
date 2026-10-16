from __future__ import annotations

import time
from typing import Any

import requests

from .auth_provider_v1 import AuthProviderV1
from .auth_provider_v2 import AuthProviderV2
from .constants import API_VERSION_V2, DOPPEL_CLIENT_HEADER, HTTP_TIMEOUT_SECONDS, MAX_HTTP_RETRIES
from .exceptions import DoppelHttpError

AuthProvider = AuthProviderV1 | AuthProviderV2


def _error_message(status_code: int, payload: Any, auth_error_message: str, url: str) -> str:
    api_message = None
    if isinstance(payload, dict):
        api_message = payload.get("message") or payload.get("error")
    detail = str(api_message) if api_message else auth_error_message
    if status_code == 401:
        return f"{url} failed (HTTP 401): {detail}"
    if status_code == 403:
        return f"{url} failed (HTTP 403): {detail if api_message else 'Forbidden'}"
    if status_code == 404:
        return f"{url} failed (HTTP 404): {detail if api_message else 'Not found'}"
    if status_code == 429:
        return f"{url} failed (HTTP 429): {detail if api_message else 'Rate limit exceeded'}"
    if status_code >= 500:
        return f"{url} failed (HTTP {status_code}): {detail if api_message else 'Doppel API server error'}"
    return f"{url} failed (HTTP {status_code}): {detail if api_message else 'Doppel API request failed'}"


def _retry_after_seconds(response: requests.Response) -> float:
    header = response.headers.get("Retry-After") if response.headers else None
    if header:
        try:
            return max(float(header), 1.0)
        except (TypeError, ValueError):
            pass
    return 1.0


class HttpClient:
    def __init__(
        self,
        auth_provider: AuthProvider,
        session: requests.Session | None = None,
        sleep: Any | None = None,
    ) -> None:
        self.auth_provider = auth_provider
        self.session = session or requests.Session()
        self._sleep = sleep or time.sleep
        self._auth_error_message = (
            "Unauthorized - invalid or expired access token"
            if auth_provider.version == API_VERSION_V2
            else "Invalid API key"
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        unauthorized_retried = False
        headers = self.auth_provider.get_auth_headers()

        for attempt in range(MAX_HTTP_RETRIES):
            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    headers={
                        "Content-Type": "application/json",
                        "x-doppel-client": DOPPEL_CLIENT_HEADER,
                        **headers,
                    },
                    params=params,
                    json=json_body,
                    timeout=HTTP_TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                if attempt >= MAX_HTTP_RETRIES - 1:
                    raise DoppelHttpError(0, "Doppel API request failed") from exc
                self._sleep(attempt + 1)
                continue

            payload: Any
            try:
                payload = response.json() if response.content else {}
            except ValueError:
                payload = {}

            if (
                response.status_code == 401
                and self.auth_provider.version == API_VERSION_V2
                and not unauthorized_retried
            ):
                self.auth_provider.invalidate_token()
                headers = self.auth_provider.get_auth_headers(force_refresh=True)
                unauthorized_retried = True
                continue

            if response.status_code == 429 and attempt < MAX_HTTP_RETRIES - 1:
                self._sleep(_retry_after_seconds(response))
                continue

            if response.status_code >= 500 and attempt < MAX_HTTP_RETRIES - 1:
                self._sleep(attempt + 1)
                continue

            if not response.ok:
                raise DoppelHttpError(
                    response.status_code,
                    _error_message(response.status_code, payload, self._auth_error_message, url),
                )
            return payload if payload != {} or response.content else {}

        raise DoppelHttpError(0, "Doppel API request failed after retries")
