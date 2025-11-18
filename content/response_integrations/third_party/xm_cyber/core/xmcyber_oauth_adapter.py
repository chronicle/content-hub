import requests
from httpx import Client
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon.oauth import (
    AuthenticationError,
    AuthorizedOauthClient,
    CredStorage,
    OAuthAdapter,
    OauthManager,
    OauthToken,
)

from .constants import PING_ENDPOINT, REFRESH_TOKEN_ENDPOINT
from .utils import compute_expiry


class XMCyberOAuthAdapter(OAuthAdapter):
    """Adapter for XMCyber OAuth implementation."""

    def __init__(self, base_url: str, api_key: str, tenant: str):
        self.base_url = base_url
        self.api_key = api_key
        self.tenant = tenant
        self.auth_url = f"{self.base_url}{PING_ENDPOINT}"
        self.refresh_url = f"{self.base_url}{REFRESH_TOKEN_ENDPOINT}"
        self.session = None  # Will be set by prepare_authorized_client
        self._refresh_token = None  # Store refresh token for future use

    def check_signer(self, token: OauthToken) -> bool:
        """Verify if the token signer is valid."""
        return token.signer == self.api_key

    def refresh_token(self) -> OauthToken:
        """
        Refresh the access token using the refresh token if valid, otherwise use API key.

        Returns:
            OauthToken: New access and refresh tokens
        """
        if self.session is None:
            print("Call the prepare_authorized_client method first")
            self.session = Client()

        # Try to use refresh token first if available and not expired
        if self._refresh_token:
            try:
                print("Attempting to refresh token using refresh token")
                response = self.session.post(
                    self.refresh_url,
                    json={"refreshToken": self._refresh_token},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    # Update refresh token if a new one is provided
                    new_refresh_token = data.get("refreshToken")
                    if new_refresh_token:
                        self._refresh_token = new_refresh_token
                    print("Updating the oauth token")
                    return OauthToken(
                        access_token=data["accessToken"],
                        refresh_token=self._refresh_token,
                        expiration_time=compute_expiry(data),
                        signer=self.api_key,
                    )
                else:
                    print(
                        f"Refresh token failed with status {response.status_code}: {response.text}"
                    )

            except Exception as e:
                print(f"Error refreshing token: {str(e)}")

        # Fall back to API key authentication
        print("Using API key to get new tokens")
        response = self.session.post(
            self.auth_url,  # Adjust endpoint as needed
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
        )

        if response.status_code != 200:
            error_msg = (
                f"Failed to get new token with API key: {response.status_code} - {response.text}"
            )
            print(error_msg)
            raise AuthenticationError(error_msg)

        data = response.json()
        self._refresh_token = data.get("refreshToken")
        print("Updating the oauth token")
        return OauthToken(
            access_token=data["accessToken"],
            refresh_token=self._refresh_token,
            expiration_time=compute_expiry(data),
            signer=self.api_key,
        )

    @staticmethod
    def validate_bad_credentials(response: requests.Response) -> bool:
        """Check if the response indicates expired credentials."""
        print("Validating the bad credentials. Status Code:", response.status_code)
        if response.status_code in (419, 401, 400, 403):
            print("Token expired or invalid")
            raise AuthenticationError("Token expired or invalid")
        return False

    def prepare_authorized_client(
        self, token: OauthToken, auth_client: "AuthorizedOauthClient"
    ) -> "AuthorizedOauthClient":
        """Prepare the authorized client with proper headers."""
        print("Preparing the Auth Client")
        auth_client.headers.update({
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        })
        return auth_client


class XMCyberOAuthManager(OauthManager):
    def __init__(self, oauth_adapter: OAuthAdapter, cred_storage: CredStorage) -> None:
        super().__init__(oauth_adapter, cred_storage)

    def _token_is_expired(self) -> bool:
        """Override the token expiration check with correct logic."""
        if self._token is None:
            return True

        if not self._oauth_adapter.check_signer(self._token):
            return True

        # Corrected expiration check
        current_time = unix_now()
        is_expired = self._token.expiration_time <= current_time
        return is_expired
