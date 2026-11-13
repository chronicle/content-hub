from __future__ import annotations

from .constants import API_VERSION_V1
from .exceptions import DoppelConfigError


class AuthProviderV1:
    """API-key authentication for Doppel Vision API v1."""

    version = API_VERSION_V1

    def __init__(self, api_key: str, user_api_key: str | None = None, org_code: str | None = None) -> None:
        """Initialize v1 authentication headers from API key credentials.

        Args:
            api_key: Organization API key.
            user_api_key: Optional user API key.
            org_code: Optional organization code for multi-tenant setups.

        Raises:
            DoppelConfigError: If the organization API key is missing.
        """
        if not api_key:
            raise DoppelConfigError("API Key is required for API v1")
        self.api_key = api_key
        self.user_api_key = user_api_key
        self.org_code = org_code

    def get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """Return static v1 authentication headers.

        Args:
            force_refresh: Unused. Present for interface compatibility with v2.

        Returns:
            Headers required by Doppel API v1.
        """
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
        """No-op for v1, which does not mint or cache tokens."""
        return None
