from __future__ import annotations

from .constants import API_VERSION_V1
from .exceptions import DoppelConfigError


class AuthProviderV1:
    version = API_VERSION_V1

    def __init__(self, api_key: str, user_api_key: str | None = None, org_code: str | None = None) -> None:
        if not api_key:
            raise DoppelConfigError("API Key is required for API v1")
        self.api_key = api_key
        self.user_api_key = user_api_key
        self.org_code = org_code

    def get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        del force_refresh
        headers = {
            "accept": "application/json",
            "x-api-key": self.api_key,
        }
        if self.user_api_key:
            headers["x-user-api-key"] = self.user_api_key
        if self.org_code:
            headers["x-organization-code"] = self.org_code
        return headers

    def invalidate_token(self) -> None:
        return None
