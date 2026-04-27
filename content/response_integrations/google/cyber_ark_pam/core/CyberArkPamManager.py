# ============================= IMPORTS ===================================== #
from __future__ import annotations
import base64
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    load_key_and_certificates,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from cryptography.hazmat.backends import default_backend
from typing import Optional
from dataclasses import dataclass
import requests
from requests_toolbelt.adapters.x509 import X509Adapter
from urllib.parse import urljoin

from .CyberArkPamParser import CyberArkPamParser


# ============================= CONSTS ===================================== #
CA_CERT_PATH = "cacert.pem"
URLS = {
    "get_access_token": "/PasswordVault/API/Auth/CyberArk/Logon",
    "list_accounts": "PasswordVault/API/Accounts",
    "get_password": "PasswordVault/API/Accounts/{account_id}/Password/Retrieve/",
}
MAX_RETRIES = 1
GET_TOKEN_TIMEOUT = 60
# ============================= CLASSES ===================================== #


@dataclass
class ListAccountsQuery:
    search: Optional[str] = None
    searchType: Optional[str] = None
    offset: Optional[int] = None
    limit: Optional[int] = None
    filter: Optional[str] = None
    savedfilter: Optional[str] = None

    def as_query(self):
        return {key: value for key, value in self.__dict__.items() if value is not None}


class CyberArkPamManagerError(Exception):
    """
    General Exception for CyberArk PAM manager
    """

    pass


class CyberArkPamNotFoundError(CyberArkPamManagerError):
    """
    Not Found Exception for CyberArk PAM manager
    """

    pass


class CyberArkPamManager:
    """
    CyberArk PAM Manager
    """

    def __init__(
        self,
        api_root: str,
        username: str,
        password: str,
        siemplify=None,
        verify_ssl: bool = False,
        ca_certificate: str = None,
        client_certificate: str = None,
        client_certificate_passphrase: str = None,
    ):
        self.siemplify = siemplify
        self.session = requests.Session()
        self.api_root = api_root
        self.__set_certificates(client_certificate_passphrase, client_certificate)
        self.__set_verify(verify_ssl, ca_certificate)
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": self.__get_access_token(username, password),
            }
        )
        self.parser = CyberArkPamParser()
        self.siemplify.LOGGER.info("CyberArk PAM Manager initialized")

    def __set_certificates(
        self, client_certificate_passphrase: str = None, client_certificate: str = None
    ):
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

    def __set_verify(self, verify_ssl: bool, ca_certificate: str = None):
        """
        Set verify ssl
        :param verify_ssl: {bool} True if verify ssl
        :param ca_certificate: {str} CA certificate
        :return: None
        """
        if verify_ssl and ca_certificate:
            ca_cert = base64.b64decode(ca_certificate)
            with open(CA_CERT_PATH, "w+") as f:
                f.write(ca_cert.decode())

            self.session.verify = CA_CERT_PATH
            self.siemplify.LOGGER.info("Set CA's certificate for session")
        elif verify_ssl:
            self.session.verify = True
        else:
            self.session.verify = False

    def __build_full_uri(self, url_key: str, **kwargs) -> str:
        """
        Build full uri from url key
        :param url_key: {str} The key
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full uri
        """
        return urljoin(self.api_root, URLS[url_key].format(**kwargs))

    def __get_access_token(self, username: str, password: str):
        """
        Get token from CyberArk PAM
        :param username
        :param password
        :return: {str} Token
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
    def validate_response(response):
        """
        Check for error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise CyberArkPamNotFoundError(e)
            raise CyberArkPamManagerError(e)

    def list_accounts(
        self,
        search_query: Optional[str],
        search_operator: Optional[str],
        max_records_to_return: Optional[int],
        records_offset: Optional[int],
        filter_query: Optional[str],
        saved_filter: Optional[str],
    ):
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
        ticketing_system_name: str = None,
        ticket_id: int = None,
        version: int = None,
    ):
        """
        Get password from CyberArk PAM for specified account and optionally version
        :param account: ID of the account
        :param reason: Reason of retrieval
        :param ticketing_system_name: Ticketing System Name
        :param ticket_id: Ticket ID
        :param version: Version of secret to be retrieved
        :return: Password value
        """
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
            url=self.__build_full_uri("get_password", account_id=account),
            json=prepared_payload,
        )
        self.validate_response(response)

        return response.text
