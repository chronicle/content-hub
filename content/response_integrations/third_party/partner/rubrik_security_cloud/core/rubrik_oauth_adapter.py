"""OAuth adapter and manager for Rubrik Security Cloud integration.

This module implements TIPCommon OAuth components for secure token management
with automatic refresh and encrypted storage.
"""

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

from .constants import DEFAULT_REQUEST_TIMEOUT
from .rubrik_exceptions import RubrikException
from .utils import compute_expiry


class RubrikOAuthManager(OauthManager):
    """Custom OAuth manager for Rubrik Security Cloud.

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


class RubrikOAuthAdapter(OAuthAdapter):
    """OAuth adapter for Rubrik Security Cloud.

    Implements the Access Token Regeneration for Rubrik's API.
    """

    def __init__(
        self,
        service_account_json: dict,
        verify_ssl: bool = False,
        client_id: str = None,
    ):
        """Initialize the Rubrik OAuth adapter.

        Args:
            service_account_json: Service account credentials containing
                client_id, client_secret, access_token_uri and expires_in
            verify_ssl: Whether to verify SSL certificates
            client_id: Client ID of the user for token signing
        """
        self.service_account_json = service_account_json
        self.verify_ssl = verify_ssl
        self.client_id = client_id

    def check_signer(self, token: OauthToken) -> bool:
        """Verify the token signer matches the client id.

        Args:
            token: OAuth token to validate

        Returns:
            True if signer is valid or not required, False otherwise
        """
        if hasattr(token, "signer") and self.client_id:
            return token.signer == self.client_id
        return False

    def refresh_token(self) -> OauthToken:
        """Generate a new access token from Rubrik API.

        This method is called when:
        1. No saved token is found
        2. Saved token is expired
        3. JWT validation fails (401 with jwt+invalid/fail in error)

        Returns:
            OauthToken: New token with access_token and expiration_time

        Raises:
            RubrikException: If token generation fails
        """
        # Prepare credentials
        payload = {
            "client_id": self.service_account_json.get("client_id"),
            "client_secret": self.service_account_json.get("client_secret"),
        }
        url = self.service_account_json.get("access_token_uri")

        # Request new token from Rubrik
        response = requests.post(
            url,
            json=payload,
            verify=self.verify_ssl,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        # Extract access token
        response_data = response.json()
        access_token = response_data.get("access_token")
        if not access_token:
            raise RubrikException("Failed to retrieve access token from response")

        # Calculate expiration time
        # unix_now() returns milliseconds, expires_in is in seconds
        expiration_time = compute_expiry(response_data)

        # Return new token (will be saved by AuthorizedOauthClient)
        return OauthToken(
            access_token=access_token,
            expiration_time=expiration_time,
            refresh_token=None,
            signer=self.client_id,
        )

    @staticmethod
    def validate_bad_credentials(response: Response) -> bool:
        """Validate bad credentials"""

        return True

    def prepare_authorized_client(
        self,
        token: OauthToken,
        auth_client: Any,
    ) -> Any:
        """Set authorization header with the access token."""
        pass
