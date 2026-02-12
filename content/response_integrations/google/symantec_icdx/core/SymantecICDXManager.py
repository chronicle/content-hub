# ==============================================================================
# title           :SymantecICDXManager.py
# description     :This Module contain all SymantecICDX search API functionality
# author          :victor@siemplify.co
# date            :07-04-19
# python_version  :2.7
# ==============================================================================
# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations

import copy

import requests

# =====================================
#             CONSTANTS               #
# =====================================
FIELDS_KEY_NAME = "fields"
START_TIME_KEY_NAME = "start"
END_TIME_KEY_NAME = "end"
QUERY_KEY_NAME = "where"
LIMIT_KEY_NAME = "limit"
NEXT_PAGE_KEY_NAME = "next"
EVENT_ID_KEY_NAME = "uuid"

EVENT_LIMIT = 10

# URLs.
SEARCH_REQUEST_URL = "{0}/r3_epmp_i/dx/archives/search"

AUTH_HEADER = {"Content-Type": "application/json", "Authorization": "Basic {}"}


# =====================================
#              CLASSES                #
# =====================================
class SymantecICDXContentError(Exception):
    pass


class SymantecICDXManagerError(Exception):
    pass


class SymantecICDXManager:
    def __init__(self, api_root, api_key, verify_ssl=False):
        self.api_root = api_root
        self.session = requests.session()
        self.session.headers = copy.deepcopy(AUTH_HEADER)
        self.session.headers["Authorization"] = self.session.headers["Authorization"].format(
            api_key
        )
        self.session.verify = verify_ssl

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} The message to display on error
        """
        try:
            if response.status_code == 204 and not response.content:
                raise SymantecICDXContentError("No content")

            response.raise_for_status()

        except requests.HTTPError as error:
            raise SymantecICDXManagerError(f"{error_msg}: {error} - {response.content}")

        def _paginate_results(self, request_url, payload, next_uuid):
            """
            Get all paginated results.
            :param request_url: {string} Target request URL.
            :param payload: {dict} Last payload sent.
            :param next_uuid: {string} Next page UUID.
            :return: {list} list of dicts.
            """
            result_list = []
            payload[NEXT_PAGE_KEY_NAME] = next_uuid
            response = self.session.post(request_url, json=payload)
            if response.content:
                result_list.extend(response.json().get("result"))
                while response.json().get(NEXT_PAGE_KEY_NAME):
                    payload[NEXT_PAGE_KEY_NAME] = response.json().get(NEXT_PAGE_KEY_NAME)
                    response = self.session.post(request_url, json=payload)
                    if response.content:
                        result_list.extend(response.json().get("result"))
                    else:
                        break

            return result_list

    def test_connectivity(self):
        """
        Test connectivity
        :return: {bool} True if successful, exception otherwise.
        """
        self.get_event("c196fb70-591a-11e9-c000-0000000000aa")
        return True

    def find_events(self, query, start_time, end_time=None, fields=None, limit=EVENT_LIMIT):
        """
        Find events in ICDX
        :param query: {string}
        :param start_time: {long} in milliseconds
        :param end_time: {long} in milliseconds
        :param fields: {list of strings} events fields names to return
        :param limit: {init}
        :return: {list of dicts} events
        """
        result_events = []

        request_url = SEARCH_REQUEST_URL.format(self.api_root)

        payload = {
            "id": 1,  # Request type.
            "start": start_time,  # Start time milliseconds.
            "where": query,  # Query string.
            "limit": limit,  # Limit for the number of the events.
        }

        if fields:
            payload[FIELDS_KEY_NAME] = fields

        if end_time:
            payload[END_TIME_KEY_NAME] = end_time

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        if response.content:
            result_events = response.json().get("result", [])

            if NEXT_PAGE_KEY_NAME in response.json():
                result_events.extend(
                    self._paginate_results(
                        request_url, payload, response.json().get(NEXT_PAGE_KEY_NAME)
                    )
                )

        return result_events

    def get_event(self, event_uuid):
        """
        Get event data by it's ID.
        :param event_uuid: {string} Event ID.
        :return: {dict} Event data.
        """
        request_url = SEARCH_REQUEST_URL.format(self.api_root)
        payload = {
            "id": 0,  # Request type - Always will be 0 for get event request.
            "uuid": event_uuid,  # Event ID.
        }
        response = self.session.post(request_url, json=payload)
        try:
            self.validate_response(response)
        except SymantecICDXContentError:
            return None
        return response.json()
