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

import base64
import pathlib
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    load_key_and_certificates,
)
from requests_toolbelt.adapters.x509 import X509Adapter

from .CyberArkPamParser import CyberArkPamParser
from .datamodels import Account

# ============================= CONSTS ===================================== #
CA_CERT_PATH = "cacert.pem"
URLS = {
    "get_access_token": "/PasswordVault/API/Auth/CyberArk/Logon",
    "list_accounts": "PasswordVault/API/Accounts",
    "get_password": "PasswordVault/API/Accounts/{account_id}/Password/Retrieve/",
    "change_password": "PasswordVault/API/Accounts/{account_id}/Change",
}
MAX_RETRIES = 1
GET_TOKEN_TIMEOUT = 60
# ============================= CLASSES ===================================== #


@dataclass
class ListAccountsQuery:
    search: str | None = None
    searchType: str | None = None
    offset: int | None = None
    limit: int | None = None
    filter: str | None = None
    savedfilter: str | None = None

    def as_query(self):
        return {key: value for key, value in self.__dict__.items() if value is not None}


class CyberArkPamManagerError(Exception):
    """General Exception for CyberArk PAM manager."""


class CyberArkPamNotFoundError(CyberArkPamManagerError):
    """Not Found Exception for CyberArk PAM manager."""


class CyberArkPamAccountNotManagedError(CyberArkPamManagerError):
    """Account Not Managed Exception for CyberArk PAM manager."""


class CyberArkPamManager:
    """CyberArk PAM Manager."""

    def __init__(
        self,
        api_root: str,
        username: str,
        password: str,
        siemplify=None,
        verify_ssl: bool = False,
        ca_certificate: str | None = None,
        client_certificate: str | None = None,
        client_certificate_passphrase: str | None = None,
    ) -> None:
        """Initialize the CyberArk PAM client.

        Args:
            api_root: Base URL of the CyberArk PAM instance.
            username: Username for authentication.
            password: Password for authentication.
            siemplify: Optional SiemplifyAction/SOAR SDK instance for logging.
            verify_ssl: Whether to verify SSL certificates.
            ca_certificate: Base64 encoded CA certificate content.
            client_certificate: Base64 encoded client PKCS12 certificate.
            client_certificate_passphrase: Passphrase for the client certificate.
        """
        self.siemplify = siemplify
        self.session = requests.Session()
        self.api_root = api_root
        self.__set_certificates(client_certificate_passphrase, client_certificate)
        self.__set_verify(verify_ssl, ca_certificate)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": self.__get_access_token(username, password),
        })
        self.parser = CyberArkPamParser()
        self.siemplify.LOGGER.info("CyberArk PAM Manager initialized")

    def __set_certificates(
        self,
        client_certificate_passphrase: str | None = None,
        client_certificate: str | None = None,
    ) -> None:
        """Configure the HTTP session with client-side SSL certificates.

        Args:
            client_certificate_passphrase: The passphrase for the certificate.
            client_certificate: Base64 encoded PKCS12 certificate.
        """
        if not client_certificate:
            return

        backend = default_backend()
        encoded_cert = base64.b64decode(client_certificate)
        encoded_passphrase = (
            client_certificate_passphrase.encode("utf-8")
            if client_certificate_passphrase is not None
            else client_certificate_passphrase
        )

        decoded_cert = load_key_and_certificates(data=encoded_cert, password=encoded_passphrase, backend=backend)
        self.siemplify.LOGGER.info("Loaded Client's certificate")

        cert_bytes = decoded_cert[1].public_bytes(Encoding.DER)
        pk_bytes = decoded_cert[0].private_bytes(
            encoding=Encoding.DER,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        adapter = X509Adapter(
            max_retries=MAX_RETRIES,
            cert_bytes=cert_bytes,
            pk_bytes=pk_bytes,
            encoding=Encoding.DER,
        )
        self.session.mount("https://", adapter)
        self.siemplify.LOGGER.info("Set Client's certificate for session")

    def __set_verify(self, verify_ssl: bool, ca_certificate: str | None = None) -> None:
        """Set SSL verification for the session.

        Args:
            verify_ssl: True if SSL certificates should be verified.
            ca_certificate: Base64 encoded CA certificate content.
        """
        if verify_ssl and ca_certificate:
            ca_cert = base64.b64decode(ca_certificate)
            with pathlib.Path(CA_CERT_PATH).open("w+", encoding="utf-8") as f:
                f.write(ca_cert.decode())

            self.session.verify = CA_CERT_PATH
            self.siemplify.LOGGER.info("Set CA's certificate for session")
        elif verify_ssl:
            self.session.verify = True
        else:
            self.session.verify = False

    def __build_full_uri(self, url_key: str, **kwargs) -> str:
        """Build the full URI from a URL key.

        Args:
            url_key: The key in URLS dictionary mapping to the endpoint path.
            **kwargs: Variables passed for URL path formatting.

        Returns:
            The formatted full URI.
        """
        return urljoin(self.api_root, URLS[url_key].format(**kwargs))

    def __get_access_token(self, username: str, password: str) -> str:
        """Get the access token from CyberArk PAM.

        Args:
            username: The username to authenticate with.
            password: The password to authenticate with.

        Returns:
            The access token.
        """
        payload = {"username": username, "password": password}

        response = self.session.post(
            url=self.__build_full_uri("get_access_token"),
            json=payload,
            timeout=GET_TOKEN_TIMEOUT,
        )
        self.validate_response(response)
        self.siemplify.LOGGER.info("Received access token")

        return response.text[1:-1]

    @staticmethod
    def validate_response(response: requests.Response) -> None:
        """Validate HTTP response and raise appropriate exceptions on failure.

        Args:
            response: The Response object to validate.

        Raises:
            CyberArkPamNotFoundError: If HTTP status code is 404.
            CyberArkPamManagerError: If any other HTTP error status is returned.
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_code = ""
            try:
                error_json = response.json()
                error_message = error_json.get("ErrorMessage", "")
                error_code = error_json.get("ErrorCode", "")
                if error_message:
                    msg = error_message
                else:
                    msg = response.reason or str(e)
            except Exception:
                msg = response.reason or str(e)

            if response.status_code == 404:
                raise CyberArkPamNotFoundError(msg) from e
            if response.status_code == 400 and (error_code == "CAWS00001E" or "not managed by the cpm" in msg.lower()):
                raise CyberArkPamAccountNotManagedError(msg) from e
            raise CyberArkPamManagerError(msg) from e

    def list_accounts(
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
        list_accounts_query = ListAccountsQuery(
            search=search_query,
            searchType=search_operator,
            limit=max_records_to_return,
            offset=records_offset,
            filter=filter_query,
            savedfilter=saved_filter,
        )

        response = self.session.get(
            url=self.__build_full_uri("list_accounts"),
            params=list_accounts_query.as_query(),
        )
        self.validate_response(response)

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
        payload = {
            "reason": reason,
            "TicketingSystemName": ticketing_system_name,
            "TicketId": ticket_id,
            "Version": version,
        }
        prepared_payload = {key: value for key, value in payload.items() if value is not None}

        response = self.session.post(
            url=self.__build_full_uri("get_password", account_id=account),
            json=prepared_payload,
        )
        self.validate_response(response)

        return response.text

    def change_password(self, account: str) -> None:
        """Mark an account for password rotation.

        Args:
            account: ID of the account to rotate.
        """
        payload = {"ChangeEntireGroup": "true"}
        response = self.session.post(
            url=self.__build_full_uri("change_password", account_id=account),
            json=payload,
        )
        self.validate_response(response)
