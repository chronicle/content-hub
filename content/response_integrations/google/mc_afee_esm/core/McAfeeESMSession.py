from __future__ import annotations
import requests
import base64
import re
import json
import hashlib

from typing import Dict, Any
from urllib.parse import urljoin

from .McAfeeESMEncryption import McAfeeESMEncryption
from TIPCommon import read_content, write_content, is_empty_string_or_none
from .constants import (
    LOGIN_PAYLOAD,
    LOGIN_URL,
    CONNECTOR_TOKEN_FILE_NAME,
    CONNECTOR_TOKEN_DB_KEY,
    ACTION_TOKEN_DB_KEY,
    ACTION_TOKEN_FILE_NAME,
    ACTION_TOKEN_IDENTIFIER,
    TOKEN_FULL_PATH,
)


class McAfeeESMSession(requests.Session):
    """
    Class to wrap requests.Session and manipulate with concurrent sessions
    on it's level.
    """

    def __init__(
        self,
        username: str,
        password: str,
        api_root: str,
        is_connector: bool = False,
        siemplify_scope: Any = None,
        siemplify_logger: Any = None,
        use_aes_encryption: bool = False,
    ) -> None:
        requests.Session.__init__(self)
        self.esm_username = username
        self.esm_password = password
        self.esm_api_root = api_root
        self.esm_is_connector = is_connector
        self.generate_request_sent = False
        self.is_token_loaded = False
        self.siemplify_scope = siemplify_scope
        self.siemplify_logger = siemplify_logger
        self.use_aes_encryption = use_aes_encryption
        self.encryption = McAfeeESMEncryption()

    def get_token_full_path(self) -> str:
        """
        Get token full path.
        Returns:
            (str)
        """
        return TOKEN_FULL_PATH.format(file_name=self.get_token_file_name())

    def get_token_file_name(self) -> str:
        """
        Get token file name, we are using different files for connector and action.
        Returns:
            (str)
        """
        return (
            CONNECTOR_TOKEN_FILE_NAME
            if self.esm_is_connector
            else ACTION_TOKEN_FILE_NAME
        ).format(hashed_configs=self.get_hashed_configs())

    def get_action_token_db_key(self) -> str:
        """
        Get token DB key for actions
        Returns:
            (str)
        """
        return ACTION_TOKEN_DB_KEY.format(hashed_configs=self.get_hashed_configs())

    def get_connector_token_db_key(self) -> str:
        """
        Get token DB key for connector
        Returns:
            (str)
        """
        return CONNECTOR_TOKEN_DB_KEY.format(hashed_configs=self.get_hashed_configs())

    def get_hashed_configs(self) -> str:
        """
        Get hashed configs
        Returns:
            (str)
        """
        return hashlib.sha512(
            f"{self.esm_username}{self.esm_password}{self.esm_api_root}".encode("utf-8")
        ).hexdigest()

    def request(self, method: str, url: str, **kwargs: str) -> requests.Response:
        """
        Override request method, in order to handle expired tokens and set
        the working one.

        Args:
            method: Request method
            url: Request url
            **kwargs: additional arguments

        Returns:
            The response of the request.
        """
        response = super(McAfeeESMSession, self).request(method, url, **kwargs)

        # if applied token is valid, then do nothing, just return the response.
        if self.is_applied_token_valid(response):
            return response

        # if the token is not valid, we don't make a request to generate new one
        # we call set_token in order to generate new tokens, update the
        # headers accordingly
        # and make the request with valid tokens
        if not self.generate_request_sent:
            self.set_token()
            return self.request(method, url, **kwargs)

        # if applied tokens are invalid after generating new ones
        # we are just returning the response
        return response

    def set_token(self) -> None:
        """
        Set the tokens (from DB or send generate request) and update
        the headers with that tokens.
        """
        self.headers.update(self.get_token())

    def get_token(self) -> Dict:
        """
        Get the tokens (from DB or send generate request).
        If the method already tried to load from file and sent the request
        to generate new one. It means all methods to get tokens are
        unsuccessful, so it will rise exception
        Returns:
            (dict) The tokens dict.
            The structure is: {'Cookie': jwttoken, 'X-Xsrf-Token': xsrf_token}
        """
        if not self.is_token_loaded:
            self.siemplify_logger.info(f"Loading tokens from DB...")
            return self.load_token()
        if not self.generate_request_sent:
            self.siemplify_logger.info(f"Generating tokens from API...")
            return self.generate_token()

        raise Exception("Unable to load tokens")

    @staticmethod
    def validate_response(response: requests.Response) -> None:
        """
        Validate HTTP response.
        Args:
            response: HTTP response
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            raise Exception(
                f"Status code:{response.status_code}, Content:{response.content}, Error: {err}"
            )
        except Exception as err:
            raise Exception(f"Error occurred - Error: {err}")

    def generate_token(self) -> Dict:
        """
        Send request in order to get generated tokens.
        Returns:
            (dict) The tokens dict.
            The structure is: {'Cookie': jwttoken, 'X-Xsrf-Token': xsrf_token}
        """
        self.generate_request_sent = True
        encoded_username = base64.b64encode(self.esm_username.encode())
        encoded_password = base64.b64encode(self.esm_password.encode())

        if self.use_aes_encryption:
            LOGIN_PAYLOAD["username"] = self.esm_username
            LOGIN_PAYLOAD["password"] = self.esm_password

        else:
            LOGIN_PAYLOAD["username"] = encoded_username.decode()
            LOGIN_PAYLOAD["password"] = encoded_password.decode()

        login_url = urljoin(self.esm_api_root, LOGIN_URL)
        try:
            login_response = self.post(
                login_url, json=LOGIN_PAYLOAD, headers=self.headers, verify=False
            )
            self.validate_response(login_response)
            # Fetch token for headers.
            cookie = login_response.headers.get("Set-Cookie")
            jwttoken = re.search(
                "(^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*)", cookie
            ).group(1)
            xsrf_token = login_response.headers.get("Xsrf-Token")
            self.save_token(jwttoken, xsrf_token)
            self.siemplify_logger.info(f"Successfully generated new tokens from API.")
            return {"Cookie": jwttoken, "X-Xsrf-Token": xsrf_token}

        except (KeyError, TypeError) as err:
            raise

    def is_applied_token_valid(self, response: requests.Response) -> bool:
        """
        Determine whether the token is valid or not.
        Args:
            response: HTTP response

        Returns:
            (bool) Whether the applied tokens are valid or not.
        """
        try:
            if response.status_code in [401]:
                return False
            return True
        except Exception:
            return False

    def save_token(self, jwttoken: str, xsrf_token: str) -> None:
        """
        Saves the tokens to the file/db.
        Args:
            jwttoken: The jwttoken to save
            xsrf_token: The xsrf_token to save
        """
        token_json = {"jwt_token": jwttoken, "xsrf_token": xsrf_token}
        token_json_str = json.dumps(token_json)
        encrypted_token_json = self.encrypt_token_json(token_json_str)

        if not self.esm_is_connector:
            self.write_content_for_actions(
                content_to_write=encrypted_token_json.decode(), default_value_to_set={}
            )
        else:
            write_content(
                siemplify=self.siemplify_scope,
                content_to_write=encrypted_token_json.decode(),
                file_name=self.get_token_full_path(),
                db_key=self.get_connector_token_db_key(),
            )

    def decrypt_token_json(self, encrypted_token: bytes) -> str:
        """
        Decrypt token json.
        Args:
            encrypted_token: The encrypted token to decrypt

        Returns:
            (str)
        """
        return self.encryption.decrypt(encrypted_token, self.get_encryption_password())

    def encrypt_token_json(self, token_json: str) -> bytes:
        """
        Encrypt token json
        Args:
            token_json: Token json

        Returns:
            (bytes)
        """
        return self.encryption.encrypt(token_json, self.get_encryption_password())

    def get_encryption_password(self) -> str:
        """
        Retrieve password for encryption/decryption.
        Returns:
            (str) Password for encryption/decryption
        """
        return self.esm_password

    def load_token(self) -> Dict:
        """
        Try to load tokens from DB. If exception, we will call
        generate_token in order to get tokens.
        Returns:
            (dict) The tokens dict.
            The structure is: {'Cookie': jwttoken, 'X-Xsrf-Token': xsrf_token}
        """
        try:
            self.is_token_loaded = True
            if not self.esm_is_connector:
                encrypted_token = self.read_content_for_actions(
                    default_value_to_return="{}"
                )
            else:
                encrypted_token = read_content(
                    siemplify=self.siemplify_scope,
                    file_name=self.get_token_full_path(),
                    db_key=self.get_connector_token_db_key(),
                    default_value_to_return="{}",
                )
            if encrypted_token == "{}":
                response = self.generate_token()
            else:
                decrypted_token = self.decrypt_token_json(encrypted_token.encode())
                token_json = json.loads(decrypted_token)
                response = {
                    "Cookie": token_json.get("jwt_token"),
                    "X-Xsrf-Token": token_json.get("xsrf_token"),
                }
                self.siemplify_logger.info(f"Successfully loaded tokens from DB.")
        except Exception as e:
            self.siemplify_logger.error(f"Failed loading tokens from DB. Error: {e}")
            response = self.generate_token()
        return response

    def write_content_for_actions(
        self, content_to_write: Any, default_value_to_set: Any = None
    ) -> None:
        """
        Write content into a DB.
        If the object contains no data, does not exist, return the default
        Args:
            content_to_write: (dict/list/str) Content that would be written to
            the dedicated data stream.
            *Note that the content passes through "json.dumps" before
            getting written
            default_value_to_set: (dict/list/str) the default value to be set
            in case a new file/key is created.
            *Note that the default value passes through "json.dumps" before
            getting written. If no value is supplied (therefore the default
            value 'None' is used), an internal default value of {} (dict) will
            be set as the new default value
        """
        try:
            self.siemplify_scope.set_context_property(
                0,
                ACTION_TOKEN_IDENTIFIER,
                self.get_action_token_db_key(),
                content_to_write,
            )

        # If an error happened in the json.dumps methods
        except TypeError as err:
            self.siemplify_logger.error(
                f"Failed parsing JSON to string. "
                f'Writing default value instead: "{default_value_to_set}". '
                f"\nERROR: {err}"
            )
            self.siemplify_logger.exception(err)
            self.siemplify_scope.set_context_property(
                0,
                ACTION_TOKEN_IDENTIFIER,
                self.get_action_token_db_key(),
                json.dumps(default_value_to_set),
            )
        # If there is a connection problem with the DB
        except Exception as err:
            self.siemplify_logger.error(
                "Exception was raised from the database. ERROR: {err}"
            )
            self.siemplify_logger.exception(err)
            raise

    def read_content_for_actions(self, default_value_to_return: Any) -> Dict:
        """
        Read the content from DB.
        If the object contains no data, does not exist, return a default value
        Args:
            default_value_to_return: (dict/list/str) the default value to be
            set in case a new file/key is created. If no value is supplied
            (therefore the default value 'None' is used), an internal default
            value of {} (dict) will be set as the new default value

        Returns:
            (dict) The content inside the DB,
                 the content passes through 'json.loads' before returning.
                 If the content could not be parsed as a json or if no content
                 was found, the default value will return as-is
                 (see "default_value_to_return" parameter doc for further explanation)
        """
        try:
            str_data = self.siemplify_scope.get_context_property(
                0, ACTION_TOKEN_IDENTIFIER, self.get_action_token_db_key()
            )

            # Check if the db key exists
            if is_empty_string_or_none(str_data):
                self.siemplify_logger.info(
                    f'Key: "{self.get_action_token_db_key()}" does not exist '
                    f"in the database. Returning default value instead: "
                    f"{default_value_to_return}"
                )
                return default_value_to_return

            return str_data

        # If an error happened in the json.loads methods
        except TypeError as err:
            self.siemplify_logger.error(
                f"Failed to parse data as JSON. "
                f'Returning default value instead: "{default_value_to_return}".'
                f" \nERROR: {err}"
            )
            self.siemplify_logger.exception(err)
            return default_value_to_return

        # If there is a connection problem with the DB
        except Exception as error:
            self.siemplify_logger.error(
                f"Exception was raised from the database. ERROR: {error}."
            )
            self.siemplify_logger.exception(error)
            raise
