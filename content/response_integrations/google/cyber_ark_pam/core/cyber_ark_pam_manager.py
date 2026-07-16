# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ============================= IMPORTS ===================================== #
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

from .authentication import CyberArkPamAuthenticator
from .cyber_ark_pam_parser import CyberArkPamParser
from .datamodels import ListAccountsQuery
from .utils import build_full_url, validate_response

if TYPE_CHECKING:
    from .datamodels import Account


class CyberArkPamManager:
    """CyberArk PAM Manager."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        api_root: str,
        username: str,
        password: str,
        logger: Any = None,  # noqa: ANN401
        verify_ssl: bool = False,  # noqa: FBT001, FBT002
        ca_certificate: str | None = None,
        client_certificate: str | None = None,
        client_certificate_passphrase: str | None = None,
    ) -> None:
        """Initialize the CyberArk PAM client.

        Args:
            api_root: Base URL of the CyberArk PAM instance.
            username: Username for authentication.
            password: Password for authentication.
            logger: Optional logger instance.
            verify_ssl: Whether to verify SSL certificates.
            ca_certificate: Base64 encoded CA certificate content.
            client_certificate: Base64 encoded client PKCS12 certificate.
            client_certificate_passphrase: Passphrase for the client certificate.

        """
        self.logger = logger
        self.session = requests.Session()
        self.api_root = api_root
        self.username = username
        self.password = password
        self.parser = CyberArkPamParser()
        self.authenticator = CyberArkPamAuthenticator(
            session=self.session,
            api_root=self.api_root,
            verify_ssl=verify_ssl,
            ca_certificate=ca_certificate,
            client_certificate=client_certificate,
            client_certificate_passphrase=client_certificate_passphrase,
            logger=self.logger,
        )
        if self.logger:
            self.logger.info("CyberArk PAM Manager initialized")

    def test_connectivity(self) -> None:
        """Test connectivity and authenticate with CyberArk PAM server."""
        self.authenticator.authenticate(self.username, self.password)

    def _ensure_authenticated(self) -> None:
        """Ensure session authorization token is populated."""
        if "Authorization" not in self.session.headers:
            self.test_connectivity()

    def list_accounts(  # noqa: PLR0913, PLR0917
        self,
        search_query: str | None,
        search_operator: str | None,
        max_records_to_return: int | None,
        records_offset: int | None,
        filter_query: str | None,
        saved_filter: str | None,
    ) -> list[Account]:
        """List PAM accounts matching specified criteria.

        Args:
            search_query: Free text search query.
            search_operator: Operator for text search.
            max_records_to_return: Maximum number of records to return.
            records_offset: Number of records to skip.
            filter_query: Query filter.
            saved_filter: Saved filter name.

        Returns:
            A list of Account data models.

        """
        self._ensure_authenticated()
        list_accounts_query = ListAccountsQuery(
            search=search_query,
            searchType=search_operator,
            limit=max_records_to_return,
            offset=records_offset,
            filter=filter_query,
            savedfilter=saved_filter,
        )

        response = self.session.get(
            url=build_full_url(self.api_root, "list_accounts"),
            params=list_accounts_query.as_query(),
        )
        validate_response(response)

        return self.parser.build_accounts(response.json())

    def get_password(
        self,
        account: str,
        reason: str,
        ticketing_system_name: str | None = None,
        ticket_id: int | None = None,
        version: int | None = None,
    ) -> str:
        """Get password from CyberArk PAM for a specified account and version.

        Args:
            account: ID of the account.
            reason: Reason for retrieving the password.
            ticketing_system_name: Name of the ticketing system.
            ticket_id: The ID of the ticket.
            version: Version of secret to be retrieved.

        Returns:
            The password value.

        """
        self._ensure_authenticated()
        payload = {
            "reason": reason,
            "TicketingSystemName": ticketing_system_name,
            "TicketId": ticket_id,
            "Version": version,
        }
        prepared_payload = {
            key: value for key, value in payload.items() if value is not None
        }

        response = self.session.post(
            url=build_full_url(self.api_root, "get_password", account_id=account),
            json=prepared_payload,
        )
        validate_response(response)

        return response.text

    def change_password(self, account: str) -> None:
        """Mark an account for password rotation.

        Args:
            account: ID of the account to rotate.

        """
        self._ensure_authenticated()
        payload = {"ChangeEntireGroup": True}
        response = self.session.post(
            url=build_full_url(self.api_root, "change_password", account_id=account),
            json=payload,
        )
        validate_response(response)

    def get_secret_versions(self, account: str) -> list[Any]:
        """Get secret versions from CyberArk PAM for a specified account.

        Args:
            account: ID of the account.

        Returns:
            A list of secret versions.

        """
        self._ensure_authenticated()
        response = self.session.get(
            url=build_full_url(
                self.api_root, "get_secret_versions", account_id=account
            ),
        )
        validate_response(response)

        return self.parser.build_versions(response.json())
