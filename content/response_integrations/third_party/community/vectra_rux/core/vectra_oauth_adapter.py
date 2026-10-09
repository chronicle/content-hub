"""OAuth adapter and manager for VectraRUX integration.

This module implements TIPCommon OAuth components for secure token management
with automatic refresh and encrypted storage.
"""
from __future__ import annotations

import urllib.parse

import requests
from TIPCommon.oauth import CredStorage, DB_TOKEN_KEY, OAuthAdapter, OauthManager, OauthToken, Response
from TIPCommon.smp_time import unix_now

from .constants import DEFAULT_REQUEST_TIMEOUT, ENDPOINTS, PING
from .UtilsManager import compute_expiry
from .VectraRUXExceptions import RefreshTokenException, UnauthorizeException


class JobCredStorage(CredStorage):
    """CredStorage variant for SiemplifyJob execution contexts.

    TIPCommon's CredStorage.get_instance_identifier() only recognizes an
    Action (integration_identifier/integration_instance) or a Connector
    (context.connector_info.identifier) execution context; a SiemplifyJob
    has neither, so it raises AuthenticationError. Jobs have their own
    scoped-context storage instead (get_scoped_job_context_property /
    set_scoped_job_context_property), so this stores the cached token
    there, reusing the same encrypt/decrypt logic as the base class.
    """

    def get_token(self):
        encrypted_data = self.chronicle_soar.get_scoped_job_context_property(
            property_key=DB_TOKEN_KEY,
        )
        if encrypted_data is None:
            return None

        token_data = self._decrypt(encrypted_data.encode())
        return OauthToken.from_cache(token_data)

    def set_token(self, token):
        encrypted_data = self._encrypt(token.to_cache())
        self.chronicle_soar.set_scoped_job_context_property(
            property_key=DB_TOKEN_KEY,
            property_value=encrypted_data.decode(),
        )


class VectraOAuthManager(OauthManager):
    """Custom OAuth manager for VectraRUX.

    Handles token lifecycle:
    - Fetches saved token from encrypted storage
    - Checks token expiration before each request
    - Triggers token refresh when needed
    """

    def _token_is_expired(self):
        """Check if the current token is expired.

        Returns:
            bool: True if token is None, signer mismatch, or expired.

        """
        if self._token is None:
            return True

        if not self._oauth_adapter.check_signer(self._token):
            return True

        return self._token.expiration_time <= unix_now()


class VectraOAuthAdapter(OAuthAdapter):
    """OAuth adapter for VectraRUX.

    Generates access tokens for the VectraRUX API using the OAuth2 client
    credentials grant, or the refresh token grant when a refresh token is
    available.
    """

    def __init__(self, api_root, client_id, client_secret, verify_ssl=False):
        """Initialize the VectraRUX OAuth adapter.

        Args:
            api_root (str): API root of the VectraRUX server.
            client_id (str): OAuth client ID of the VectraRUX account.
            client_secret (str): OAuth client secret of the VectraRUX account.
            verify_ssl (bool): Whether to verify SSL certificates.

        """
        self.api_root = api_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        self.token_url = urllib.parse.urljoin(api_root, ENDPOINTS[PING])

    def check_signer(self, token):
        """Verify the token signer matches the client id.

        Args:
            token (OauthToken): OAuth token to validate.

        Returns:
            bool: True if signer matches the configured client id.

        """
        return bool(getattr(token, "signer", None) == self.client_id)

    def refresh_token(self, refresh_token=None):
        """Generate a new access token from the VectraRUX API.

        Uses the refresh token grant when a refresh token is available,
        otherwise falls back to the client credentials grant.

        Args:
            refresh_token (str, optional): Previously issued refresh token.

        Returns:
            OauthToken: New token with access_token, refresh_token and
                expiration_time.

        Raises:
            RefreshTokenException: If refreshing with the refresh token fails.
            UnauthorizeException: If the provided credentials are invalid.

        """
        if refresh_token:
            try:
                response_data = self._request_token(
                    body={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                )
                return self._build_token(response_data)
            except RefreshTokenException:
                pass

        response_data = self._request_token(
            body="grant_type=client_credentials",
            auth=(self.client_id, self.client_secret),
        )
        return self._build_token(response_data)

    def _request_token(self, body, auth=None):
        """Send the token request and return the parsed JSON response.

        Args:
            body (dict|str): Request payload.
            auth (tuple, optional): Basic auth credentials.

        Returns:
            dict: Parsed JSON response.

        Raises:
            RefreshTokenException: If refreshing with the refresh token fails.
            UnauthorizeException: If the provided credentials are invalid.

        """
        response = requests.post(
            self.token_url,
            data=body,
            auth=auth,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            verify=self.verify_ssl,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )

        if not response.ok:
            error_msg = "An error occurred"
            try:
                error_msg = response.json().get("error", error_msg)
            except Exception:
                pass

            if auth is None:
                raise RefreshTokenException(
                    f"Failed to generate token using refresh token. Error - {error_msg}",
                )
            raise UnauthorizeException(
                "Provided Credentials are not valid!. Please verify provided credentials.",
            )

        return response.json()

    def _build_token(self, response_data):
        """Build an OauthToken from a token endpoint response.

        Args:
            response_data (dict): Parsed JSON response from the token endpoint.

        Returns:
            OauthToken: New token.

        """
        return OauthToken(
            access_token=response_data.get("access_token"),
            expiration_time=compute_expiry(response_data),
            refresh_token=response_data.get("refresh_token"),
            signer=self.client_id,
        )

    @staticmethod
    def validate_bad_credentials(response: Response) -> bool:
        """Validate bad credentials.

        Returns:
            bool: True always; unauthorized responses are handled by the
                caller's retry logic in VectraRUXManager.

        """
        return True

    def prepare_authorized_client(self, token, auth_client):
        """No-op; VectraRUXManager applies the Authorization header itself."""
        pass
