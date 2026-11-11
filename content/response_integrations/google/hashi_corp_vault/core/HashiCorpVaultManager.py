from __future__ import annotations
import requests
from typing import Dict
from urllib.parse import urljoin

from hashi_corp_vault.core.constants import ENDPOINTS
from hashi_corp_vault.core.datamodels import GenericResponse, KeyValueResponse
from hashi_corp_vault.core.HashiCorpVaultExceptions import HashiCorpVaultException, NotFoundException
from hashi_corp_vault.core.HashiCorpVaultParser import HashiCorpVaultParser
from hashi_corp_vault.core.UtilsManager import validate_response


class HashiCorpVaultManager:
    def __init__(
        self,
        api_root,
        api_token,
        username,
        password,
        verify_ssl,
        key_value_secret_engine_path,
        siemplify=None,
    ):
        """
        The method is used to init an object of Manager class
        Args:
            api_root (str): API root of the HashiCorp Vault instance
            api_token (str): API token of the HashiCorp Vault account
            username (str): Username of the HashiCorp Vault account
            password (str): Password of the HashiCorp Vault account
            verify_ssl (bool): Specifies if certificate that is configured on the api root should be validated
            key_value_secret_engine_path (str): The path used for the key-value secret storage
            siemplify: Siemplify connector or action execution instance
        """
        self.api_root = api_root
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.key_value_secret_engine_path = key_value_secret_engine_path
        self.siemplify = siemplify
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = HashiCorpVaultParser()

        if api_token:
            self.session.headers.update({"X-Vault-Token": api_token})
        elif username and password:
            self.session.headers.update(
                {"Authorization": f"Bearer {self._get_api_token()}"}
            )
        else:
            raise HashiCorpVaultException(
                "Please specify Token or Username and Password."
            )

    def _get_full_url(self, url_id, **kwargs) -> str:
        """
        Get full url from url identifier.
        Args:
            url_id (str): The id of url
            **kwargs: Variables passed for string formatting

        Returns:
            (str) The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _get_api_token(self) -> str:
        """
        Authenticate using Username and Password
        Args:

        Returns:
             (str) The api token
        """
        url = self._get_full_url("auth", username=self.username)
        payload = {"password": self.password}
        response = self.session.post(url, data=payload)
        validate_response(response)

        return response.json().get("auth", {}).get("client_token")

    def test_connectivity(self):
        """
        Test connectivity
        Args:

        Returns:
            () None
        """
        response = self.session.get(self._get_full_url("ping"))
        validate_response(response)

    def list_key_value_secret_keys(self, key_value, secret_path="") -> Dict:
        """
        Get key-value secret keys
        Args:
            key_value (str): The path used for the key-value secret storage
            secret_path (str): The secret path to fetch from
        Returns:
             (KeyValueResponse) KeyValueResponse object
        """
        url = self._get_full_url(
            "list_key_value", key_value=key_value, secret_path=secret_path or ""
        )
        response = self.session.request("LIST", url)
        if response.status_code == 404:
            raise NotFoundException
        validate_response(response)

        return self.parser.build_key_value_response_object(response.json())

    def read_key_value_secret(self, key_value, secret_path, version) -> Dict:
        """
        Read key-value secret
        Args:
            key_value (str): The path used for the key-value secret storage
            secret_path (str): The secret path to fetch from
            version (int): The secret version to fetch
        Returns:
             (dict) Response JSON
        """
        url = self._get_full_url(
            "read_key_value_secret", key_value=key_value, secret_path=secret_path
        )
        params = {"version": version} if version else {}
        response = self.session.get(url, params=params)
        if response.status_code == 404:
            raise NotFoundException
        validate_response(response)

        return response.json()

    def list_aws_roles(self, key_value: str) -> KeyValueResponse:
        """
        Get list of roles from specified kv storage
        Args:
            key_value (str): The path used for the key-value secret storage
        Returns:
             (KeyValueResponse) KeyValueResponse object
        """
        url = self._get_full_url("list_aws_roles", key_value=key_value)
        response = self.session.request("LIST", url)
        if response.status_code == 404:
            raise NotFoundException
        validate_response(response)

        return self.parser.build_key_value_response_object(response.json())

    def generate_aws_creds(
        self,
        key_value: str,
        role_name: str,
        role_arn: str,
        session_name: str,
        ttl_seconds: int,
    ) -> GenericResponse:
        """
        Generate creds for specified aws role inside kv storage
        Args:
            key_value: The path used for the key-value secret storage
            role_name: Specifies the name of the role to generate credentials against.
            role_arn: The ARN of the role to assume if credential_type on the Vault role is assumed_role.
            session_name: The role session name to attach to the assumed role ARN.
            ttl_seconds: Specifies the TTL for the use of the STS token.
                Valid only when credential_type is assumed_role or federation_token.
        Returns:
             (GenericResponse) GenericResponse object
        """
        query_dict = {
            "role_arn": role_arn,
            "role_session_name": session_name,
            "ttl": f"{ttl_seconds}s" if ttl_seconds is not None else None,
        }

        url = self._get_full_url(
            "generate_aws_creds", key_value=key_value, role_name=role_name
        )
        response = self.session.get(
            url, params={k: v for k, v in query_dict.items() if v is not None}
        )
        if response.status_code == 404:
            raise NotFoundException
        validate_response(response)

        return self.parser.build_generic_response_object(response.json())
