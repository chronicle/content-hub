from __future__ import annotations
import requests
import json
from .EasyVistaParser import EasyVistaParser
from .EasyVistaExceptions import (
    EasyVistaException,
    EasyVistaInternalError,
    EasyVistaUnauthorizedError,
)

from .constants import (
    PING_QUERY,
    TICKET_MODIFICATION,
    TICKET_COMMENT,
    TICKET_DESCRIPTION,
    TICKET_DOCUMENTS,
    TICKET_ACTIONS,
)


class EasyVistaManager:
    def __init__(
        self,
        api_root=None,
        account_id=None,
        username=None,
        password=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the EasyVista instance.
        :param account_id: Account ID of the EasyVista acccount
        :param username: EasyVista username.
        :param password: EasyVista password.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the EasyVista server is valid.
        :param siemplify_logger: Siemplify logger.
        """

        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.account_id = account_id
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger

        self.parser = EasyVistaParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = (self.username, self.password)

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:

            if response.status_code == 500 or b"Resource not found" in response.content:
                raise EasyVistaInternalError(
                    f"Status Code: {response.status_code}, Content: {response.content}"
                )

            if response.status_code == 401:
                raise EasyVistaUnauthorizedError(
                    f"Status Code: {response.status_code}, Content: {'Given credentials are incorrect, please check your Account ID, Username and Password.'}"
                )

            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise EasyVistaException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise EasyVistaException(
                f"{error_msg}: {response.json().get('name')} {json.dumps(response.json())}"
            )

    def test_connectivity(self, account_id):
        """
        Test integration connectivity.
        :param account_id: {str} Account ID of the EasyVista account
        :return: {bool}
        """

        request_url = f"{self.api_root}{PING_QUERY.format(account_id)}"
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

    def add_comment(self, account_id, ticket_id, comment):
        """
        Add Comment to EasyVista Ticket
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :param comment: {str} Comment added to the ticket
        """

        payload = {"Comment": comment}

        request_url = (
            f"{self.api_root}{TICKET_MODIFICATION.format(account_id, ticket_id)}"
        )
        result = self.session.put(request_url, json=payload)
        # Verify result.
        self.validate_response(result)

    def close_ticket(
        self, account_id, ticket_id, comment, close_date, delete_ongoing_actions=False
    ):
        """
        Close EasyVista Ticket
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :param comment: {str} Reason to close the ticket
        :param close_date: {str}
        :param delete_ongoing_actions: {bool}
        """
        delete_actions = 0
        if not delete_ongoing_actions:
            delete_actions = 1

        payload = {
            "closed": {
                "end_date": close_date,
                "delete_actions": delete_actions,
                "comment": comment,
            }
        }

        request_url = (
            f"{self.api_root}{TICKET_MODIFICATION.format(account_id, ticket_id)}"
        )
        result = self.session.put(request_url, json=payload)
        # Verify result.
        self.validate_response(result)

    def get_ticket_general_info(self, account_id, ticket_id):
        """
        Get General Info about EasyVista Ticket
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :return: Ticket object
        """

        request_url = (
            f"{self.api_root}{TICKET_MODIFICATION.format(account_id, ticket_id)}"
        )
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_ticket_object(result.json())

    def get_ticket_description(self, account_id, ticket_id):
        """
        Get EasyVista Ticket Description
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :return: Ticket Description object
        """

        request_url = (
            f"{self.api_root}{TICKET_DESCRIPTION.format(account_id, ticket_id)}"
        )
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_ticket_description_object(result.json())

    def get_ticket_comment(self, account_id, ticket_id):
        """
        Get EasyVista Ticket Comment
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :return: Ticket Comment object
        """

        request_url = f"{self.api_root}{TICKET_COMMENT.format(account_id, ticket_id)}"
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_ticket_comment_object(result.json())

    def get_ticket_attachments(self, account_id, ticket_id):
        """
        Get EasyVista Ticket Attachments
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :return: Ticket Attachment object
        """

        request_url = f"{self.api_root}{TICKET_DOCUMENTS.format(account_id, ticket_id)}"
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_ticket_attachments_list(result.json())

    def get_ticket_actions_raw(self, account_id, ticket_id):
        """
        Get EasyVista Ticket Actions in Raw Form
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :return: Ticket Actions object
        """
        request_url = f"{self.api_root}{TICKET_ACTIONS.format(account_id, ticket_id)}"
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_ticket_actions_object(result.json())

    def get_ticket_actions(self, account_id, ticket_id):
        """
        Get EasyVista Ticket Actions
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :return: Ticket Action object
        """

        request_url = f"{self.api_root}{TICKET_ACTIONS.format(account_id, ticket_id)}"
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_ticket_actions_list(result.json())

    def get_ticket_information(self, account_id, ticket_id):
        """
        Function that puts all the ticket information together
        :param account_id: {str} Account ID of the EasyVista account
        :param ticket_id: {str} EasyVista Ticket ID
        :return: TicketInformation object
        """

        general_ticket_info = self.get_ticket_general_info(account_id, ticket_id)
        ticket_description = self.get_ticket_description(account_id, ticket_id)
        ticket_comment = self.get_ticket_comment(account_id, ticket_id)
        ticket_actions = self.get_ticket_actions(account_id, ticket_id)
        ticket_attachments = self.get_ticket_attachments(account_id, ticket_id)

        return self.parser.build_final_object(
            general_ticket_info,
            ticket_description,
            ticket_comment,
            ticket_actions,
            ticket_attachments,
        )
