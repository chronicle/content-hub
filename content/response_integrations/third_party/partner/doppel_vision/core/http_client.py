from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.types import SingleJson

from .auth_provider_v1 import AuthProviderV1
from .auth_provider_v2 import AuthProviderV2
from .constants import API_VERSION_V2, DOPPEL_CLIENT_HEADER, HTTP_TIMEOUT_SECONDS, MAX_HTTP_RETRIES
from .exceptions import DoppelHttpError

AuthProvider = AuthProviderV1 | AuthProviderV2


@dataclass(frozen=True, slots=True)
class _RequestSpec:
    method: str
    url: str
    params: SingleJson | None = None
    json_body: SingleJson | None = None


def _retry_after_seconds(response: requests.Response) -> float:
    header = response.headers.get("Retry-After") if response.headers else None
    if header:
        try:
            return max(float(header), 1.0)
        except (TypeError, ValueError):
            pass
    return 1.0


class HttpClient:
    """Authenticated HTTP client with retry and v2 token refresh."""

    def __init__(
        self,
        auth_provider: AuthProvider,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Initialize the client with an auth provider and optional session.

        Args:
            auth_provider: v1 or v2 authentication provider.
            session: Optional shared requests session.
            sleep: Optional sleep callable used by retries. Defaults to time.sleep.
        """
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
        params: SingleJson | None = None,
        json_body: SingleJson | None = None,
    ) -> SingleJson:
        """Send an authenticated HTTP request with retry and v2 token refresh.

        Args:
            method: HTTP method.
            url: Absolute request URL.
            params: Optional query parameters.
            json_body: Optional JSON body.

        Returns:
            Parsed JSON payload.

        Raises:
            DoppelHttpError: If the request fails after retries.
        """
        unauthorized_retried = False
        headers = self.auth_provider.get_auth_headers()
        spec = _RequestSpec(method=method, url=url, params=params, json_body=json_body)

        for attempt in range(MAX_HTTP_RETRIES):
            response, payload, headers, unauthorized_retried = self._send_with_refresh(
                spec,
                headers,
                attempt,
                unauthorized_retried,
            )
            if response is None or self._sleep_for_retry(response, attempt):
                continue
            if not response.ok:
                raise DoppelHttpError(
                    response.status_code,
                    self._error_message(response.status_code, payload, spec.url),
                )
            return payload if payload != {} or response.content else {}

        raise DoppelHttpError(0, "Doppel API request failed after retries")

    def _send_with_refresh(
        self,
        spec: _RequestSpec,
        headers: dict[str, str],
        attempt: int,
        unauthorized_retried: bool,
    ) -> tuple[requests.Response | None, SingleJson, dict[str, str], bool]:
        response = self._send(spec, headers, attempt)
        if response is None:
            return None, {}, headers, unauthorized_retried
        payload = self._parse_payload(response)
        refreshed = self._refresh_headers_if_unauthorized(response, unauthorized_retried)
        if refreshed is None:
            return response, payload, headers, unauthorized_retried
        response = self._send(spec, refreshed, attempt)
        payload = self._parse_payload(response) if response is not None else {}
        return response, payload, refreshed, True

    def _send(self, spec: _RequestSpec, headers: dict[str, str], attempt: int) -> requests.Response | None:
        try:
            return self.session.request(
                method=spec.method.upper(),
                url=spec.url,
                headers={
                    "Content-Type": "application/json",
                    "x-doppel-client": DOPPEL_CLIENT_HEADER,
                    **headers,
                },
                params=spec.params,
                json=spec.json_body,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            if attempt >= MAX_HTTP_RETRIES - 1:
                raise DoppelHttpError(0, "Doppel API request failed") from exc
            self._sleep(attempt + 1)
            return None

    def _parse_payload(self, response: requests.Response) -> SingleJson:
        payload: SingleJson = {}
        try:
            parsed = response.json() if response.content else {}
        except ValueError:
            return payload
        return parsed if isinstance(parsed, dict) else payload

    def _refresh_headers_if_unauthorized(
        self,
        response: requests.Response,
        unauthorized_retried: bool,
    ) -> dict[str, str] | None:
        if response.status_code != 401 or self.auth_provider.version != API_VERSION_V2:
            return None
        if unauthorized_retried:
            return None
        self.auth_provider.invalidate_token()
        return self.auth_provider.get_auth_headers(force_refresh=True)

    def _sleep_for_retry(self, response: requests.Response, attempt: int) -> bool:
        if response.status_code == 429 and attempt < MAX_HTTP_RETRIES - 1:
            self._sleep(_retry_after_seconds(response))
            return True
        if response.status_code >= 500 and attempt < MAX_HTTP_RETRIES - 1:
            self._sleep(attempt + 1)
            return True
        return False

    def _error_message(self, status_code: int, payload: object, url: str) -> str:
        api_message: object = None
        if isinstance(payload, dict):
            api_message = payload.get("message") or payload.get("error")
        detail = str(api_message) if api_message else self._auth_error_message
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
