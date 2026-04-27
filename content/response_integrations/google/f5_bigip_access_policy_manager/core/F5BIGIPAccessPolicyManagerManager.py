from __future__ import annotations
import requests
import json
from .F5BIGIPAccessPolicyManagerExceptions import F5BIGIPAccessPolicyManagerException
from .F5BIGIPAccessPolicyManagerParser import F5BIGIPAccessPolicyManagerParser
from .constants import (
    LOGIN_QUERY,
    UPDATE_TIMEOUT_QUERY,
    PING_QUERY,
    LIST_ACTIVE_SESSIONS_QUERY,
    DISCONNECT_SESSIONS_DELETE_QUERY,
    TOKEN_FILE_PATH,
    DEFAULT_ENCODING,
)
from .TokenEncryption import encrypt, decrypt


class F5BIGIPAccessPolicyManagerManager:
    def __init__(
        self,
        api_root=None,
        username=None,
        password=None,
        token_timeout=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API Root for the F5 platform
        :param username: {str} Username to connect to the F5 platform
        :param password: {str} Password to connect to the F5 platform
        :param token_timeout: {int} Token expiration timeout
        :param verify_ssl: {bool} True if SSL should be verified, False otherwise
        :param siemplify_logger: {int} Siemplify Logger instance
        """
        self.username = username
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.password = password
        self.token_timeout = token_timeout
        self.siemplify_logger = siemplify_logger
        self.parser = F5BIGIPAccessPolicyManagerParser()

        self.session = requests.session()
        self.session.verify = verify_ssl
        self.token_file_password = f"{self.username}{self.password}"
        self.token_mechanism()

    def token_mechanism(self):
        """
        Function that handles the token update mechanism
        Firstly it will try to read the token from a file, if found this token is tested.
        If a token is not found of the token doesn't work -> generate a new token and store it in a file.
        """
        try:
            with open(TOKEN_FILE_PATH) as f:
                encrypted_token = f.read()
                self.access_token = decrypt(
                    encrypted_token, self.token_file_password
                ).decode(DEFAULT_ENCODING)
                self.session.headers.update({"X-F5-Auth-Token": self.access_token})

                self.test_connectivity()  # test the validity of the token

        except Exception:
            self.session.headers = {}  # set the headers to empty
            self.access_token = self.generate_token()

            self.session.headers.update({"X-F5-Auth-Token": self.access_token})

            # If the Token Timeout value is set, the action will change the token timeout for the newly generated token
            if self.token_timeout:
                self.update_token_timeout()

            self.test_connectivity()

    def generate_token(self):
        """
        Generate F5 Token
        :return: {string} Access token. The app can use this token in API requests
        """
        payload = {
            "username": self.username,
            "password": self.password,
            "loginProviderName": "tmos",
        }

        res = self.session.post(LOGIN_QUERY.format(self.api_root), json=payload)
        self.validate_response(res)

        token = res.json().get("token", {}).get("token")

        with open(TOKEN_FILE_PATH, "wb") as f:
            encryted_token = encrypt(token, self.token_file_password)
            f.write(encryted_token)

        return token

    def update_token_timeout(self):
        """
        Update Token Timeout based on the given timeout in sec
        """
        payload = {"timeout": self.token_timeout}

        res = self.session.patch(
            UPDATE_TIMEOUT_QUERY.format(self.api_root, self.access_token), json=payload
        )
        self.validate_response(res)

    def test_connectivity(self):
        """
        Test integration connectivity.
        """

        result = self.session.get(PING_QUERY.format(self.api_root))
        self.validate_response(result)

    def list_active_sessions(self, limit):
        """
        Function that gets actibe sessions from F5 BIG IP
        :param limit: {str} Limit of number of active sessions
        :return {ActiveSession} List of active session objects
        """

        result = self.session.get(
            LIST_ACTIVE_SESSIONS_QUERY.format(self.api_root, limit)
        )
        self.validate_response(result)
        return self.parser.build_active_sessions_object(result.json())

    def disconnect_session(self, session_id):
        """
        Function that disconnects active session based on session id
        :param session_id: {str} Session ID that should be disconnected
        """

        result = self.session.delete(
            DISCONNECT_SESSIONS_DELETE_QUERY.format(self.api_root, session_id)
        )
        self.validate_response(result)

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise F5BIGIPAccessPolicyManagerException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise F5BIGIPAccessPolicyManagerException(
                f"{error_msg}: {response.json().get('message', '')} {json.dumps(response.json())}"
            )
