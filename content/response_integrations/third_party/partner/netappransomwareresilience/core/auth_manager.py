"""
OAuth adapter and manager for NetApp RRS integration.

This module implements TIPCommon OAuth components for secure token management
with automatic refresh and encrypted storage.
"""
from __future__ import annotations

from __future__ import annotations

from typing import Any

import requests
from TIPCommon.oauth import (
    OAuthAdapter,
    OauthManager,
    OauthToken,
    Response,
)
from TIPCommon.smp_time import unix_now

from .constants import OAUTH_CONFIG
from .utils import compute_expiry


class RRSOAuthManager(OauthManager):
    """Custom OAuth manager for NetApp RRS.

    Handles token lifecycle:
    - Fetches saved token from encrypted storage
    - Checks token expiration before each request
    - Triggers token refresh when needed
    """

    def _token_is_expired(self) -> bool:
        """Check if the current token is expired.

        Returns:
            True if token is None, signer mismatch, or expired
        """
        if self._token is None:
            return True

        if not self._oauth_adapter.check_signer(self._token):
            return True

        # Check expiration: token is expired if expiration_time <= current_time
        current_time = unix_now()
        return self._token.expiration_time <= current_time


class RRSOAuthAdapter(OAuthAdapter):
    """OAuth adapter for NetApp RRS.

    Implements the Access Token generation for RRS API.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        verify_ssl: bool = False,
    ):
        """Initialize the RRS OAuth adapter.

        Args:
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl

    def check_signer(self, token: OauthToken) -> bool:
        """Verify the token signer matches the client id.

        Args:
            token: OAuth token to validate

        Returns:
            True if signer is valid or not required, False otherwise
        """
        if hasattr(token, "signer") and self.client_id:
            return token.signer == self.client_id
        return True

    def refresh_token(self) -> OauthToken:
        """Generate a new access token from RRS API.

        This method is called when:
        1. No saved token is found
        2. Saved token is expired
        3. JWT validation fails (401 with jwt errors)

        Returns:
            OauthToken: New token with access_token and expiration_time

        Raises:
            Exception: If token generation fails
        """
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": OAUTH_CONFIG["AUDIENCE"],
            "grant_type": OAUTH_CONFIG["GRANT_TYPE"]
        }

        response = requests.post(
            OAUTH_CONFIG["ENDPOINT"],
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            verify=self.verify_ssl,
            timeout=30
        )

        response.raise_for_status()
        response_data = response.json()
        access_token = response_data.get("access_token")
        
        if not access_token:
            raise Exception("Failed to retrieve access token from response")

        # Calculate expiration time
        expiration_time = compute_expiry(response_data)

        return OauthToken(
            access_token=access_token,
            expiration_time=expiration_time,
            refresh_token=None,
            signer=self.client_id,
        )

    @staticmethod
    def validate_bad_credentials(response: Response) -> bool:
        """Validate bad credentials."""
        return True

    def prepare_authorized_client(
        self,
        token: OauthToken,
        auth_client: Any,
    ) -> Any:
        """Set authorization header with the access token."""
        pass


