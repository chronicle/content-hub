from __future__ import annotations
import datetime
import requests
from requests.auth import AuthBase

from .exceptions import NetskopeAuthError


class NetskopeV2BearerAuth(AuthBase):
    """Attach static Netskope V2 Bearer token authentication to a requests session."""

    def __init__(self, access_token: str):
        self.access_token = access_token

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        return request


class NetskopeV2OAuth(AuthBase):
    """Attach dynamic Netskope V2 OAuth2 authentication to a requests session."""

    def __init__(
        self,
        api_root: str,
        client_id: str,
        client_secret: str,
        verify_ssl: bool = True,
    ):
        self.api_root = api_root.rstrip("/") + "/"
        self.client_id = client_id
        self.client_secret = client_secret
        self.generated_token: str | None = None
        self.expiry_time: datetime.datetime | None = None
        self._safety_buffer: datetime.timedelta = datetime.timedelta(seconds=5)
        self.verify_ssl = verify_ssl

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        if self._is_token_expired():
            self._generate_access_token()

        request.headers["Authorization"] = f"Bearer {self.generated_token}"
        return request

    def _is_token_expired(self) -> bool:
        if not self.expiry_time:
            return True

        return datetime.datetime.now(datetime.timezone.utc) >= (
            self.expiry_time - self._safety_buffer
        )

    def _generate_access_token(self) -> None:
        url: str = f"{self.api_root}api/v2/platform/oauth2/token/generate"
        payload = {
            "clientID": self.client_id,
            "secretKey": self.client_secret,
        }
        response = requests.post(url, json=payload, timeout=60, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise NetskopeAuthError(
                f"Unable to generate access token: {error}"
            ) from error
        data = response.json()
        token = data.get("oAuth2AccessToken")
        if not token:
            raise NetskopeAuthError("OAuth token was not found in the response")
        self.generated_token = token

        try:
            self.expiry_time = datetime.datetime.fromisoformat(data["expiryTime"])

            now = datetime.datetime.now(datetime.timezone.utc)
            total_lifetime_sec = (self.expiry_time - now).total_seconds()

            if total_lifetime_sec > 0:
                buffer_sec = max(5.0, min(60.0, total_lifetime_sec * 0.10))
                self._safety_buffer = datetime.timedelta(seconds=buffer_sec)
            else:
                self._safety_buffer = datetime.timedelta(seconds=5)

        except (KeyError, ValueError, AttributeError) as e:
            raise NetskopeAuthError(
                f"Missing or invalid expiryTime in response: {data.get('expiryTime')}"
            ) from e


class NetskopeV1Auth(AuthBase):
    """Attach Netskope V1 token authentication to a requests session."""

    def __init__(self, token: str) -> None:
        self._token = token

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        request.prepare_url(request.url, params={"token": self._token})
        return request
