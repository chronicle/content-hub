from __future__ import annotations
import requests
import json
from urllib.parse import urljoin

from .GoogleGRRParser import GoogleGRRParser
from . import consts
from .exceptions import (
    GoogleGRRNotFoundException,
    GoogleGRRInvalidCredentialsException,
    GoogleGRRBadRequestException,
    GoogleGRRStatusCodeException,
    GoogleGRRNotConnectedException,
)


ENDPOINTS = {
    "ping": "/api/config",
    "list_clients": "api/clients",
    "get_client": "/api/clients/{client_id}",
    "get_client_id": "/api/clients",
    "list_launched_flows": "api/clients/{client_id}/flows",
    "list_hunts": "api/hunts",
    "stop_hunt": "api/hunts/{hunt_id}",
    "start_hunt": "api/hunts/{hunt_id}",
    "get_hunt_details": "api/hunts/{hunt_id}",
}

HEADERS = {"Content-Type": 'Content-Type": "application/json;charset=UTF-8'}


class GoogleGRRManager:

    def __init__(
        self, api_root, username, password, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the Google GRR instance.
        :param username: username of the Google GRR instance.
        :param password: password of the Google GRR instance
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the Google GRR server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password

        self.session = requests.session()
        self.session.auth = (username, password)
        self.session.headers = HEADERS
        try:
            response = self.session.get(api_root)
            for cookie in response.cookies:
                if cookie.name == "csrftoken":
                    self.session.headers.update({"x-csrftoken": cookie.value})
                    self.session.cookies.update({"csrftoken": cookie.value})

            self.session.verify = verify_ssl
            self.siemplify_logger = siemplify_logger
            self.parser = GoogleGRRParser()

        except requests.exceptions.ConnectionError as error:
            raise GoogleGRRNotConnectedException(f"Error: {error}")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate Google GRR response
        :param response: GRR Google API response
        :param error_msg: {str} error message to display
        :return: {bool} True if successfully validated response
            raise GoogleGRRStatusCode exceptions if failed to validate response's status code
        """
        try:
            if (
                response.status_code == consts.API_NOT_FOUND_ERROR
                or consts.INVALID_HUNT_ID in response.text
            ):
                raise GoogleGRRNotFoundException(
                    f"Not Found in {consts.INTEGRATION_NAME}"
                )
            if response.status_code == consts.API_UNAUTHORIZED_ERROR:
                raise GoogleGRRInvalidCredentialsException(
                    "Invalid credentials were provided"
                )
            if response.status_code == consts.API_BAD_REQUEST:
                raise GoogleGRRBadRequestException(response.json().get("message"))
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()

            except:
                # Not a JSON - return content
                raise GoogleGRRStatusCodeException(
                    f"{error_msg}: {error} - {error.response.text}"
                )

            raise GoogleGRRStatusCodeException(
                f"{error_msg}: {response.json().get('message') or response.json().get('error')} status code: {response.status_code}"
            )

    def _get_full_url(self, url_key, **kwargs):
        """
        Get full url from url key.
        :param url_key: {str} the key of url
        :param kwargs: {dict}  Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS.get(url_key).format(**kwargs))

    def test_connectivity(self):
        f"""
        Test connectivity to the {consts.INTEGRATION_DISPLAY_NAME} with parameters provided at the integration
        configuration page on the Marketplace tab.
        raise GoogleGRRStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("ping")
        params = {"limit": 1}
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to connect to {consts.INTEGRATION_DISPLAY_NAME}",
        )

    def list_clients(self, max_results_to_return, offset):
        """
        Search Clients in order to start interacting with them.
        :param max_results_to_return: {int} Specify how many clients to return in the response.
        :param offset: {int} Specify Found clients starting offset.
        :return: {[datamodels.Client]} Client datamodel list.
        """
        params = {}
        if offset:
            params["offset"] = offset
        if max_results_to_return:
            params["count"] = max_results_to_return

        request_url = self._get_full_url("list_clients")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get clients from {consts.INTEGRATION_DISPLAY_NAME}",
        )
        search_result = json.loads(response.text.replace(")]}'", ""))
        return self.parser.build_clients_obj(search_result)

    def get_client_details(self, client_id):
        """
        Get client full details.
        :param client_id: {str} ID of the client. Comma separated.
        :return: {datamodels.Client} Client datamodel object.
        """
        request_url = self._get_full_url("get_client", client_id=client_id)
        response = self.session.get(request_url)
        self.validate_response(
            response,
            error_msg=f"Failed to fetch details for specified client {client_id} from {consts.INTEGRATION_DISPLAY_NAME}",
        )
        search_result = json.loads(response.text.replace(")]}'", ""))
        return self.parser.build_client_obj(search_result)

    def get_client_id(self, identifier):
        """
        Get client id from entity identifier
        :param identifier: Entity identifier Address to retrieve the client id from
        :return: {str} Client ID
        """
        params = {"count": 50, "offset": 0, "query": identifier}

        request_url = self._get_full_url("get_client_id")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get ID of given address from {consts.INTEGRATION_DISPLAY_NAME}",
        )
        search_result = json.loads(response.text.replace(")]}'", ""))

        return self.parser.build_client_obj_from_client_id(search_result)

    def list_launched_flows(self, client_id, max_results_to_return, offset):
        """
        Get client full details.
        :param client_id: {str} The client ID to list his launched flows
        :param offset: {str} Specify Found flows starting offset
        :param max_results_to_return: {str} Specify how many flows to return in the response.
        :return: {[datamodels.Flow]} list of flows objects.
        """
        params = {}

        if max_results_to_return:
            params["count"] = max_results_to_return

        if offset:
            params["offset"] = offset

        request_url = self._get_full_url("list_launched_flows", client_id=client_id)
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to list flow for client {client_id} from"
            f" {consts.INTEGRATION_DISPLAY_NAME}",
        )
        search_result = json.loads(response.text.replace(")]}'", ""))
        return self.parser.build_flows_obj(search_result)

    def list_hunts(self, creator, offset, max_results_to_return):
        """
        Get all available hunts.
        :param creator: {str} Return hunts created by a specified user.
        :param offset: {str} Specify Found hunts starting offset
        :param max_results_to_return: {str} Specify how many hunts to return in the response.
        :return: All available hunts.
        """
        params = {}

        if creator:
            params["created_by"] = creator

        if max_results_to_return:
            params["count"] = max_results_to_return

        if offset:
            params["offset"] = int(offset)

        request_url = self._get_full_url("list_hunts")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Error executing action 'List Hunts'. Reason:"
            f" {consts.INTEGRATION_DISPLAY_NAME}",
        )
        search_results = json.loads(response.text.replace(")]}'", ""))
        return self.parser.build_hunts_obj(search_results)

    def stop_hunt(self, hunt_id):
        """
        Stopping a hunt will prevent new clients from being scheduled and interrupt in-progress flows the next time
        they change state. This is a hard stop, so in-progress results will be lost, but results already reported are
        unaffected. Once a hunt is stopped, there is no way to start it again.
        :param hunt_id: {str} ID of the hunt to stop.
        :return: {datamodels.Hunt} Hunt object correspond to the hunt_id parameter
        """
        state = {"state": consts.STOP_STATE}

        request_url = self._get_full_url("stop_hunt", hunt_id=hunt_id)
        response = self.session.patch(request_url, json=state)
        self.validate_response(
            response,
            error_msg=f"Error executing action 'Stop a Hunt'. Reason:"
            f" {consts.INTEGRATION_DISPLAY_NAME}",
        )
        search_results = json.loads(response.text.replace(")]}'", ""))
        return self.parser.build_hunt_obj(search_results)

    def start_hunt(self, hunt_id):
        """
        Use this to start a newly created hunt. New hunts are created in the PAUSED state,
        so you’ll need to do this to run them. Hunts that reach their client limit will
        also be set to PAUSED, use this to restart them after you have removed the client limit.
        :param hunt_id: {str} ID of the hunt to start.
        :return: {datamodels.Hunt} The Hunt that was changed.
        """

        state = {"state": consts.START_STATE}

        request_url = self._get_full_url("start_hunt", hunt_id=hunt_id)
        response = self.session.patch(request_url, json=state)
        self.validate_response(
            response,
            error_msg=f"Error executing action 'Start a Hunt'. Reason:"
            f" {consts.INTEGRATION_DISPLAY_NAME}",
        )
        search_results = json.loads(response.text.replace(")]}'", ""))
        return self.parser.build_hunt_obj(search_results)

    def get_hunt_details(self, hunt_id):
        """
        Get Hunt details.
        :param hunt_id: {str} ID of the hunt to fetch.
        :return: {datamodels.Hunt} Hunt object with given id
        """
        request_url = self._get_full_url("get_hunt_details", hunt_id=hunt_id)
        response = self.session.get(request_url)
        self.validate_response(
            response,
            error_msg=f"Error executing action “Get Hunt Details” for {hunt_id}. Reason: ",
        )
        search_results = json.loads(response.text.replace(")]}'", ""))
        return self.parser.build_hunt_obj(search_results)
