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

"""Authentication module for CyberArk PAM integration."""

from __future__ import annotations

import base64
import pathlib
from typing import TYPE_CHECKING, Any

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

from .constants import AUTHENTICATION_TIMEOUT, CA_CERT_PATH, MAX_RETRIES
from .exceptions import CyberArkPamManagerError
from .utils import build_full_url, validate_response

if TYPE_CHECKING:
    import requests


class CyberArkPamAuthenticator:
    """Handles authentication and SSL configuration for CyberArk PAM."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        session: requests.Session,
        api_root: str,
        verify_ssl: bool = False,  # noqa: FBT001, FBT002
        ca_certificate: str | None = None,
        client_certificate: str | None = None,
        client_certificate_passphrase: str | None = None,
        logger: Any = None,  # noqa: ANN401
    ) -> None:
        """Initialize the CyberArk PAM Authenticator.

        Args:
            session: requests.Session instance to configure.
            api_root: Base URL of the CyberArk PAM instance.
            verify_ssl: Whether to verify SSL certificates.
            ca_certificate: Base64 encoded CA certificate content.
            client_certificate: Base64 encoded client PKCS12 certificate.
            client_certificate_passphrase: Passphrase for the client certificate.
            logger: Optional logger instance.

        """
        self.session = session
        self.api_root = api_root
        self.logger = logger
        self.__set_certificates(client_certificate_passphrase, client_certificate)
        self.__set_verify(verify_ssl, ca_certificate)

    def __set_certificates(
        self,
        client_certificate_passphrase: str | None = None,
        client_certificate: str | None = None,
    ) -> None:
        """Configure the HTTP session with client-side SSL certificates.

        Args:
            client_certificate_passphrase: The passphrase for the certificate.
            client_certificate: Base64 encoded PKCS12 certificate.

        Raises:
            CyberArkPamManagerError: If the certificate or private key is missing or invalid.

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

        decoded_cert = load_key_and_certificates(
            data=encoded_cert, password=encoded_passphrase, backend=backend
        )
        if self.logger:
            self.logger.info("Loaded Client's certificate")

        private_key = decoded_cert[0]
        certificate = decoded_cert[1]

        if private_key is None or certificate is None:
            error_message = "Client certificate or private key is missing or invalid."
            raise CyberArkPamManagerError(error_message)

        cert_bytes = certificate.public_bytes(Encoding.DER)
        pk_bytes = private_key.private_bytes(
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
        if self.logger:
            self.logger.info("Set Client's certificate for session")

    def __set_verify(self, verify_ssl: bool, ca_certificate: str | None = None) -> None:  # noqa: FBT001
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
            if self.logger:
                self.logger.info("Set CA's certificate for session")
        elif verify_ssl:
            self.session.verify = True
        else:
            self.session.verify = False

    def logon(self, username: str, password: str) -> str:
        """Logon to CyberArk PAM and retrieve the session token.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            The session token.

        """
        payload = {"username": username, "password": password}
        url = build_full_url(self.api_root, "logon")

        response = self.session.post(
            url=url,
            json=payload,
            timeout=AUTHENTICATION_TIMEOUT,
        )
        validate_response(response)
        if self.logger:
            self.logger.info("Received session token")

        return response.text[1:-1]

    def authenticate(self, username: str, password: str) -> None:
        """Authenticate session with CyberArk PAM by setting Authorization header.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        """
        token = self.logon(username, password)
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": token,
            }
        )
        if self.logger:
            self.logger.info("Connectivity test completed successfully.")
