from __future__ import annotations

import re
import time
from typing import Optional
from urllib.parse import urljoin

import requests

from .constants import PROTECT_API_ENDPOINTS, PROTECT_PREVENT_TYPE_MAP, USER_AGENT
from .exceptions import JamfError


class JamfProtectManager:
    """
    Jamf Protect API Manager for handling authentication and GraphQL API operations
    """

    def __init__(
        self,
        api_root: str,
        client_api_id: str,
        client_api_secret: str,
        verify_ssl: bool = True,
        logger=None,
    ) -> None:
        """
        Initialize Jamf Protect Manager

        Args:
            api_root: Jamf Protect server URL (e.g., https://yourserver.protect.jamfcloud.com)
            client_api_id: Jamf Protect API client ID
            client_api_secret: Jamf Protect API client secret
            verify_ssl: Whether to verify SSL certificates
            logger: Logger instance
        """
        self.api_root = (api_root or "").rstrip("/")
        self.client_api_id = client_api_id
        self.client_api_secret = client_api_secret
        self.verify_ssl = verify_ssl
        self.logger = logger

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        })

        self.access_token: Optional[str] = None
        self.token_expiration_epoch: int = 0
        self.auth_timeout = 30
        self.graphql_timeout = 60

    def _log(self, level: str, message: str) -> None:
        if self.logger:
            getattr(self.logger, level.lower(), self.logger.info)(message)

    def _get_full_url(self, endpoint: str) -> str:
        """
        Construct full URL for API endpoint

        Args:
            endpoint: API endpoint path

        Returns:
            Full URL string
        """
        return urljoin(self.api_root, endpoint.lstrip("/"))

    def get_access_token(self) -> str:
        """Obtain Jamf Protect access token using client_id + password."""
        token_url = self._get_full_url(PROTECT_API_ENDPOINTS["auth"])
        payload = {"client_id": self.client_api_id, "password": self.client_api_secret}
        self._log("info", f"Requesting Jamf Protect token at: {token_url}")
        resp = self.session.post(token_url, json=payload, timeout=self.auth_timeout)
        if resp.status_code != 200:
            raise JamfError(
                f"Jamf Protect token request failed: HTTP {resp.status_code} - {resp.text}"
            )
        data = resp.json()
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0))
        if not token:
            raise JamfError(f"Jamf Protect token response missing access_token: {data}")
        self.access_token = token
        self.token_expiration_epoch = int(time.time()) + max(expires_in - 1, 0)
        return token

    def check_token_expiration(self) -> bool:
        """
        Check if current token is valid and get new one if needed

        Returns:
            True if valid token is available
        """
        current_epoch = int(time.time())

        if self.token_expiration_epoch >= current_epoch and self.access_token:
            self._log("info", f"Token valid until epoch time: {self.token_expiration_epoch}")
            return True
        else:
            self._log("info", "No valid token available, getting new token")
            self.get_access_token()
            return True

    def invalidate_token(self) -> bool:
        self.access_token = None
        self.token_expiration_epoch = 0
        return True

    def test_connectivity(self) -> bool:
        """
        Test connectivity to Jamf Protect API

        Returns:
            True if connection successful

        Raises:
            JamfError: If connection fails
        """
        try:
            # Ensure we have a valid token
            self._log("info", "Testing connectivity to Jamf Protect API")
            self.check_token_expiration()
            return True

        except Exception as e:
            error_msg = f"Unexpected error during connectivity test: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def graphql(self, query: str, variables: Optional[dict] = None) -> dict:
        """Call Jamf Protect GraphQL API endpoint.

        Args:
            query: GraphQL query string
            variables: GraphQL variables

        Returns:
            dict: API response containing the result of the GraphQL query

        Raises:
            JamfError: If the API request fails
        """
        try:
            self.check_token_expiration()

            url = self._get_full_url(PROTECT_API_ENDPOINTS["graphQL"])

            headers = {
                "Authorization": self.access_token or "",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if variables:
                payload = {"query": query, "variables": variables}
            else:
                payload = {"query": query}
            self._log("info", f"POST {url} (GraphQL)")

            response = self.session.post(
                url, json=payload, headers=headers, timeout=self.graphql_timeout
            )

            if response.status_code == 200:
                result = response.json()

                if isinstance(result, dict) and result.get("errors"):
                    try:
                        msgs = [e.get("message") or str(e) for e in result.get("errors", [])]
                    except Exception:
                        msgs = [str(result.get("errors"))]
                    raise JamfError(f"Jamf Protect GraphQL errors: {'; '.join(msgs)}")

                if result.get("data") is None:
                    raise JamfError(f"Jamf Protect GraphQL data is None: {result.get('data', {})}")

                self._log("info", "Successfully executed GraphQL query")

                return result.get("data")
            elif response.status_code == 401:
                error_msg = "Authentication failed - invalid or expired token"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 403:
                error_msg = "Insufficient permissions for GraphQL request"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            else:
                error_msg = (
                    f"Failed to execute GraphQL query. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except JamfError:
            # Preserve original JamfError exceptions (matches JamfManager pattern)
            raise
        except Exception as e:
            error_msg = f"Unexpected error during GraphQL request: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def update_protect_prevent_list(
        self,
        name: str,
        description: str | None,
        prevent_type: str,
        values: list[str],
        tags: list[str] | None = None,
        id: str | None = None,
    ) -> dict:
        """
        Update a Jamf Protect prevent list and add items in a single mutation.

        Args:
            name (str): The name of the prevent list to update
            description (str | None): The description of the prevent list
            prevent_type (str): The type of prevent list (e.g., "FILEHASH", "CDHASH", "TEAMID")
            values (list[str]): List of values to add to the prevent list
            tags (list[str] | None): List of tags to add to the prevent list
            id (str | None): The ID of the prevent list to update

        Returns:
            dict: API response containing the updated prevent list information

        Raises:
            JamfError: If the API request fails
        """
        try:
            # Sanitize and validate inputs
            sanitized_name = self._sanitize_prevent_list_name(name)
            if not values:
                raise JamfError("At least one value must be provided for the prevent list")
            if not tags:
                raise JamfError("At least one tag must be provided for the prevent list")
            if not prevent_type:
                raise JamfError(f"Unsupported Prevent Type: {prevent_type}")

            self.validate_prevent_values(prevent_type, values)

            # Helper to escape GraphQL string values
            def _gql_escape(s: str) -> str:
                return (s or "").replace("\\", "\\\\").replace('"', '\\"')

            name_esc = _gql_escape(sanitized_name)
            desc_esc = _gql_escape(description or "")
            values_list = ",".join([f'"{_gql_escape(v)}"' for v in values])
            tags_list = ",".join([f'"{_gql_escape(t)}"' for t in (tags or [])])

            mutation = (
                "mutation { "
                f'updatePreventList(input: {{ name:"{name_esc}", description:"{desc_esc}", '
                f'type: {prevent_type}, list:[{values_list}], tags:[{tags_list}] }} id: "{id}") '
                "{ id name description type list tags } }"
            )

            response = self.graphql(mutation)
            result = response.get("updatePreventList", {})
            if not result:
                raise JamfError("Failed to update prevent list")

            return result

        except JamfError:
            # Preserve original JamfError exceptions
            raise
        except Exception as e:
            error_msg = f"Unexpected error updating prevent list: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def list_prevent_lists(self) -> list[dict]:
        """
        List all prevent lists from Jamf Protect

        Returns:
            List of prevent lists

        Raises:
            JamfError: If request fails
        """
        try:
            self._log("info", "Retrieving prevent lists")

            query = "query {listPreventLists {items {id name description type list tags}}}"

            response = self.graphql(query)
            result = response.get("listPreventLists", {}).get("items", [])
            return result
        except JamfError:
            # Preserve original JamfError exceptions
            raise
        except Exception as e:
            error_msg = f"Unexpected error retrieving prevent lists: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    # Local validation helpers for prevent list values
    def _is_sha1(self, s: str) -> bool:
        return bool(re.fullmatch(r"^[A-Fa-f0-9]{40}$", str(s).strip()))

    def _is_sha256(self, s: str) -> bool:
        return bool(re.fullmatch(r"^[A-Fa-f0-9]{64}$", str(s).strip()))

    def _is_team_id(self, s: str) -> bool:
        # Apple Team ID is 10 uppercase alphanumeric characters
        return bool(re.fullmatch(r"^[A-Z0-9]{10}$", str(s).strip().upper()))

    def _is_signing_id(self, s: str) -> bool:
        # Bundle identifier style: segments of [A-Za-z0-9-]+ separated by dots,
        # must have at least one dot
        # Disallow leading/trailing dots and consecutive dots
        return bool(
            re.fullmatch(
                r"^[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+$",
                str(s).strip(),
            )
        )

    def validate_prevent_values(self, prevent_type: str, values: list[str]) -> None:
        if prevent_type not in PROTECT_PREVENT_TYPE_MAP.values():
            raise JamfError(f"Unsupported Prevent Type: {prevent_type}")
        invalid: list[tuple[str, str]] = []
        for v in values or []:
            if prevent_type == "FILEHASH":
                if not (self._is_sha1(v) or self._is_sha256(v)):
                    invalid.append((v, "not SHA-1 or SHA-256 hash"))
            elif prevent_type == "CDHASH":
                if not self._is_sha1(v):
                    invalid.append((v, "not SHA-1 hash"))
            elif prevent_type == "TEAMID":
                if not self._is_team_id(v):
                    invalid.append((
                        v,
                        "invalid Apple Team ID (expected 10 uppercase alphanumerics)",
                    ))
            elif prevent_type == "SIGNINGID":
                if not self._is_signing_id(v):
                    invalid.append((v, "invalid signing identifier"))

        if invalid:
            details = "; ".join([f"'{val}' ({reason})" for val, reason in invalid[:10]])
            more = f" and {len(invalid) - 10} more" if len(invalid) > 10 else ""
            raise JamfError(f"Invalid values for Prevent Type '{prevent_type}': {details}{more}")

    def _sanitize_prevent_list_name(self, name: str) -> str:
        if not name or not isinstance(name, str):
            raise JamfError("Prevent list name must be a non-empty string")

        sanitized = name.strip()

        if not sanitized:
            raise JamfError("Prevent list name cannot be empty or only whitespace")
        if len(sanitized) > 255:
            raise JamfError("Prevent list name cannot exceed 255 characters")

        # Remove only control characters that would break GraphQL
        sanitized = "".join(c for c in sanitized if c.isprintable())

        return sanitized
