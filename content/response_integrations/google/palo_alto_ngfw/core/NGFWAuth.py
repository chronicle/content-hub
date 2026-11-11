from __future__ import annotations
import base64
import binascii
import os

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from defusedxml import minidom

from palo_alto_ngfw.core.exceptions import NGFWException
from palo_alto_ngfw.core.utils import normalize_string


class XmlHelper:
    """
    A class for extending action on xml
    """

    def get_simple_value(self, input_string, node_name, root=None):
        """Get simple value from XML.

        :param input_string: XML content
        :param node_name: Node name to find
        :param root: Optional root node
        :return: Node value
        """
        xmldoc = minidom.parseString(input_string)

        if not root:
            root = xmldoc

        nodes = root.getElementsByTagName(node_name)

        if len(nodes) != 1:
            raise NGFWException(f"Matching nodes count != 1! {node_name}")

        node = nodes[0]
        return node.firstChild.data if node.firstChild else ""


class NGFWAuth(requests.auth.AuthBase):
    """Attach API key to requests and handle rotation."""

    def __init__(self, manager):
        self.manager = manager
        self._xml_helper = XmlHelper()

    def _get_encryption_key(self, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self.manager.password.encode())

    def _encrypt(self, data: str) -> str:
        salt = os.urandom(16)
        key = self._get_encryption_key(salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
        return base64.b64encode(salt + nonce + ciphertext).decode()

    def _decrypt(self, enc_data: str) -> str:
        data = base64.b64decode(enc_data.encode())
        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]
        key = self._get_encryption_key(salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode()

    def __call__(self, r):
        if "type=keygen" in r.url:
            return r

        parsed = urlparse(r.url)
        params = parse_qs(parsed.query)
        params["key"] = [self.manager.api_key]
        new_query = urlencode(params, doseq=True)
        r.url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )
        return r

    def _get_identifier(self) -> str:
        env = self.manager.siemplify.environment
        env = normalize_string(env) if env else "default"
        instance_id = self.manager.siemplify.integration_instance
        return f"{env}_{instance_id}_PaloAltoNGFW"

    def refresh_key(self):
        """Refresh API key by generating a new one."""
        identifier = self._get_identifier()

        self.manager.logger.info("Attempting to refresh API key.")

        cached_key = self.manager.siemplify.get_context_property(
            context_type=0,
            identifier=identifier,
            property_key="api_key"
        )

        if cached_key:
            try:
                cached_key = self._decrypt(cached_key)
            except (binascii.Error, InvalidTag, UnicodeDecodeError) as e:
                self.manager.logger.error(f"Failed to decrypt cached key: {e}")
                cached_key = None

        if cached_key and cached_key != self.manager.api_key:
            self.manager.logger.info(
                "Key in context is different. Updating local key."
            )
            self.manager.api_key = cached_key
            return

        self.manager.logger.info(
            "Key in context is same or missing. Generating new key."
        )
        new_key = self._get_api_key_via_auth()

        encrypted_key = self._encrypt(new_key)
        self.manager.siemplify.set_context_property(
            context_type=0,
            identifier=identifier,
            property_key="api_key",
            property_value=encrypted_key
        )

        self.manager.api_key = new_key

    def load_initial_key(self) -> str:
        """Load initial API key from context or generate new one."""
        identifier = self._get_identifier()

        key = self.manager.siemplify.get_context_property(
            context_type=0,
            identifier=identifier,
            property_key="api_key"
        )
        if key:
            try:
                decrypted_key = self._decrypt(key)
                self.manager.logger.info("Loaded API key from context.")
                return decrypted_key
            except (binascii.Error, InvalidTag, UnicodeDecodeError) as e:
                self.manager.logger.error(f"Failed to decrypt initial key: {e}")

        self.manager.logger.info(
            "No key in context or volatile session. Generating new key."
        )
        key = self._get_api_key_via_auth()

        encrypted_key = self._encrypt(key)
        self.manager.siemplify.set_context_property(
            context_type=0,
            identifier=identifier,
            property_key="api_key",
            property_value=encrypted_key
        )

        return key

    def _get_api_key_via_auth(self) -> str:
        try:
            response = self._get_api_key_using_post()
        except requests.exceptions.HTTPError as e:
            self.manager.logger.info(
                "POST failed with HTTP error, falling back to GET. "
                f"Reason: {str(e)}"
            )
            response = self._get_api_key_using_get()
        return self._xml_helper.get_simple_value(response, "key")

    def _get_api_key_using_post(self) -> bytes:
        url = f"{self.manager.server_address}/?type=keygen"
        payload = {"user": self.manager.username, "password": self.manager.password}

        # We need to use a session without auth to get the key, or at least not
        # trigger 403 retry loop. Since we are using a fresh session without auth
        # assigned, it's safe.
        with requests.Session() as s:
            s.verify = self.manager.session.verify
            response = s.post(url, data=payload)
            self._validate_authentication(response)
            return response.content

    def _get_api_key_using_get(self) -> bytes:
        url = (
            f"{self.manager.server_address}/?type=keygen&user="
            f"{self.manager.username}&password={self.manager.password}"
        )
        with requests.Session() as s:
            s.verify = self.manager.session.verify
            response = s.get(url)
            self._validate_authentication(response)
            return response.content

    def _validate_authentication(self, response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            safe_message = f"Client error: {e.response.reason}"
            raise requests.exceptions.HTTPError(
                safe_message, response=response
            ) from None

        if not self.manager.is_valid_response(response):
            error_message = self._get_error_message(response)
            raise NGFWException(f"Could not login: {error_message}")

    def _get_error_message(self, response: requests.Response) -> str:
        return (
            self._xml_helper.get_simple_value(response.content, "msg")
            if hasattr(response, "content")
            else "Unknown error"
        )
