from __future__ import annotations
from .utils import parse_string_to_dict
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from .constants import SCOPES, API_ROOT, ENDPOINTS, INTEGRATION_NAME
from .GoogleChatParser import GoogleChatParser
from urllib.parse import urljoin
import requests
from .exceptions import GoogleChatException


class GoogleChatManager:
    """
    Google Chat Manager
    """

    def __init__(
        self,
        api_root,
        service_account_string,
        verify_ssl,
        force_check_connectivity=False,
    ):
        self.api_root = api_root or API_ROOT
        self.service_account_string = service_account_string
        self.service_account_json = parse_string_to_dict(
            self.service_account_string,
            'Invalid JSON payload provided in the parameter "Service Account".\
                Please check the structure.',
        )
        self.verify_ssl = verify_ssl
        self.http_client = None
        self._prepare_http_client()
        self.parser = GoogleChatParser()
        if force_check_connectivity:
            self.test_connectivity()

    def _prepare_http_client(self):
        credentials = service_account.Credentials.from_service_account_info(
            info=self.service_account_json, scopes=SCOPES
        )
        self.session = AuthorizedSession(credentials)

    def _get_full_url(self, url_key, **kwargs):
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity with GChat
        :return: raise Exception if failed to validate response
        """
        response = self.session.get(self._get_full_url("list-spaces"))
        self.validate_response(
            response, error_msg=f"Unable to test connectivity with {INTEGRATION_NAME}"
        )

        return True

    def list_spaces(self, filter_key, filter_logic, filter_value, limit):
        """
        Get spaces list
        :param filter_key: {str} Filter key
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Filtered items limit
        :return: {list}
        """
        response = self.session.get(self._get_full_url("list-spaces"))
        self.validate_response(response)

        return self.parser.build_spaces_obj_list(
            response.json(), filter_key, filter_logic, filter_value, limit
        )

    def fetch_space_membership(self, space_name):
        """
        Get membership of space
        :param space_name: {str} Filter key
        :return: {list}
        """
        response = self.session.get(
            self._get_full_url("get-memberships", space=space_name)
        )
        self.validate_response(response)

        return self.parser.build_membership_obj_list(response.json())

    def create_message(self, space_name, message):
        """
        Create Message.
        :param message: {str} Message to send
        :param space_name: {str} Space to send message to
        :return: {Message}
        """
        request_url = self._get_full_url("create-message", space_name=space_name)
        data = {"text": message}

        response = self.session.post(request_url, json=data)
        self.validate_response(response)
        return self.parser.build_message_obj(response.json())

    def create_advanced_message(self, space_name, message):
        """
        Create Message.
        :param message: {str} Message to send
        :param space_name: {str} Space to send message to
        :return: {Message}
        """
        response = self.session.post(
            self._get_full_url("create-message", space_name=space_name), json=message
        )
        self.validate_response(response)

        return self.parser.build_message_obj(response.json())

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate GSuite response
        :param response: {json/html} response from GSuite api
        :param error_msg: {str} error message to display
        :return:
            raise GSuiteManagerError exception if failed to validate response's status code
            raise GSuiteEntityExistsException exception if entity already exists in GSuite
            raise GSuiteNotFoundException exception if entity was not found in GSuite
            raise GChatValidationError exception if failed to validate request
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()
            except Exception as exc:
                # Not a JSON - return content
                raise GoogleChatException(f"{error_msg}: {error.response.content}") \
                    from exc
            raise GoogleChatException(
                f"{error_msg}: {response.json().get('error', {}).get('message')}"
            )
