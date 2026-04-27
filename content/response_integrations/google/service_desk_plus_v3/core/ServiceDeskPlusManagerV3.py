from __future__ import annotations
import json
import requests
from .ServiceDeskPlusV3Exceptions import (
    ServiceDeskPlusV3Exception,
    NoteNotFoundException,
)
from .ServiceDeskPlusV3Parser import ServiceDeskPlusV3Parser
from .constants import (
    ADD_NOTE_URL,
    CLOSE_REQUEST_URL,
    REQUESTS_URL,
    SPECIFIC_REQUEST_URL,
    UPDATE_REQUEST_TYPE,
    CREATE_REQUEST_TYPE,
    GET_NOTE_URL,
)

NONE_DROPDOWN_INDICATOR = "None"


class ServiceDeskPlusManagerV3:
    def __init__(self, api_root, api_key, verify_ssl):
        """
        Initiate values
        :param api_key: technician key
        :param api_root: Api Root for the api
        :param verify_ssl: True is SSL should be verified
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.api_key = api_key
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.parser = ServiceDeskPlusV3Parser()
        self.session.headers = {"TECHNICIAN_KEY": self.api_key}

    def test_connectivity(self):
        """
        Test connectivity
        :return: {bool} True if connected, exception otherwise.
        """

        payload = {
            "input_data": {
                "list_info": {
                    "row_count": 0,
                    "start_index": 1,
                    "sort_field": "subject",
                    "sort_order": "asc",
                    "get_total_count": True,
                }
            }
        }

        request_url = f"{self.api_root}{REQUESTS_URL}"
        result = self.session.get(request_url, data=payload)
        # Verify result.
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
                raise ServiceDeskPlusV3Exception(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise ServiceDeskPlusV3Exception(
                f"{error_msg}: {response.json().get('name')} {json.dumps(response.json())}"
            )

    def add_note(
        self,
        request_id,
        add_to_linked_requests,
        mark_first_response,
        show_to_requester,
        notify_technician,
        note,
    ):
        """
        Function that adds note to a request
        :param add_to_linked_requests {bool} The note should be linked to requests
        :param request_id {str} ID of the request in ServiceDesk
        :param show_to_requester {bool} The note should be shown to the requester
        :param notify_technician {bool} The technician should be notified
        :param mark_first_response {bool} First response should be marked
        :param note {str} Note to add to the ticket
        :return: {APIResponse} APIResponse Object
        """
        try:
            # Key with note works for ServiceDeskV3 new versions up to 12
            input_data_payload = {
                "note": {
                    "description": note,
                    "show_to_requester": show_to_requester,
                    "notify_technician": notify_technician,
                    "mark_first_response": mark_first_response,
                    "add_to_linked_requests": add_to_linked_requests,
                }
            }

            payload = {"input_data": str(input_data_payload)}

            request_url = f"{self.api_root}{ADD_NOTE_URL.format(request_id)}"
            result = self.session.post(request_url, data=payload)
            # Verify result.
            self.validate_response(result)
        except:
            # Key with request_note works for ServiceDeskV3 old versions
            input_data_payload = {
                "request_note": {
                    "description": note,
                    "show_to_requester": show_to_requester,
                    "notify_technician": notify_technician,
                    "mark_first_response": mark_first_response,
                    "add_to_linked_requests": add_to_linked_requests,
                }
            }

            payload = {"input_data": str(input_data_payload)}

            request_url = f"{self.api_root}{ADD_NOTE_URL.format(request_id)}"
            result = self.session.post(request_url, data=payload)
            # Verify result.
            self.validate_response(result)

        return self.parser.build_universal_object(result.json())

    def get_notes(self, request_id):
        """
        Function that gets notes for a request
        :param request_id {str} ID of the request in ServiceDesk
        :return: {APIResponse} APIResponse Object
        """

        request_url = f"{self.api_root}{ADD_NOTE_URL.format(request_id)}"
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_note_object(result.json())

    def get_note_with_id(self, request_id, note_id):
        """
        Function that gets single note for a request
        :param request_id {str} ID of the request in ServiceDesk
        :param note_id {str} ID of the requested not
        :return: {bool} True if successful, exception otherwise.
        """

        request_url = f"{self.api_root}{GET_NOTE_URL.format(request_id, note_id)}"
        result = self.session.get(request_url)
        # Verify result.
        try:
            self.validate_response(result)
        except Exception as e:
            if result.status_code == 404:
                raise NoteNotFoundException()
            raise Exception(e)

    def close_request(self, request_id, resolution_ack, comment):
        """
        Function that closes the request
        :param request_id {str} ID of the request in ServiceDesk
        :param resolution_ack {bool} Resolution Acknowledgement
        :param comment {str} Reason/Comment to close the ticket
        :return: {APIResponse} APIResponse Object
        """

        input_data_payload = {
            "request": {
                "closure_info": {
                    "requester_ack_resolution": resolution_ack,
                    "closure_comments": comment,
                    "closure_code": {"name": "success"},
                }
            }
        }

        payload = {"input_data": str(input_data_payload)}

        request_url = f"{self.api_root}{CLOSE_REQUEST_URL.format(request_id)}"
        result = self.session.put(request_url, data=payload)
        # Verify result.
        self.validate_response(result)

        return self.parser.build_universal_object(result.json())

    def update_request_status(self, request_id, status):
        """
        Function that updates the request status
        :param request_id {str} ID of the request in ServiceDesk
        :param status {str} Status to update
        """

        input_data_payload = {"request": {"status": {"name": status}}}

        payload = {"input_data": str(input_data_payload)}

        request_url = f"{self.api_root}{SPECIFIC_REQUEST_URL.format(request_id)}"
        result = self.session.put(request_url, data=payload)
        # Verify result.
        if result.status_code == 404:
            raise NoteNotFoundException()
        self.validate_response(result)

    def get_request(self, request_id):
        """
        Function that closes the request
        :param request_id {str} ID of the request in ServiceDesk
        :return: {APIResponse} APIResponse Object
        """

        request_url = f"{self.api_root}{SPECIFIC_REQUEST_URL.format(request_id)}"
        result = self.session.get(request_url)
        # Verify result.
        if result.status_code == 404:
            raise NoteNotFoundException()
        self.validate_response(result)

        return self.parser.build_request_object(result.json())

    def request(
        self,
        request_id,
        action_type,
        description,
        subject,
        requester,
        status,
        technician,
        priority,
        urgency,
        category,
        request_template,
        request_type,
        due_by_time,
        mode,
        level,
        site,
        group,
        impact,
        assets,
    ):
        """
        Function that closes the request
        :param action_type {str} Action Type  - Create from create request actions, update from update request actions
        :param request_id {str} ID of the request in ServiceDesk
        :param description {str} description of the request
        :param subject {str} Subject of the request
        :param requester {str} Requester of the request
        :param status {str} Status of the request
        :param technician {str} Technician assigned to the request
        :param priority {str} Priority  of the request
        :param urgency {str} Urgency of the request
        :param category {str} Category of the request
        :param request_template {str} Request Template of the request
        :param request_type {str} Request Type of the request
        :param due_by_time {str} Request due date in ms
        :param mode {str} Mode of the request
        :param level {str} Level of the request
        :param site {str} Site of the request
        :param group {str} Group of the request
        :param impact {str} Impact of the request
        :param assets {str} Assets of the request
        :return: {APIResponse} APIResponse Object
        """
        input_data_payload = {"request": {}}

        if request_template and request_template != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["template"] = {"name": request_template}

        if subject:
            input_data_payload["request"]["subject"] = subject

        if requester:
            input_data_payload["request"]["requester"] = {"name": requester}

        if impact and impact != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["impact"] = {"name": impact}

        if description:
            input_data_payload["request"]["description"] = description

        if request_type and request_type != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["request_type"] = {"name": request_type}

        if assets:
            assets_list = []
            for asset in assets:
                if asset:
                    assets_list.append({"name": asset})

            input_data_payload["request"]["assets"] = assets_list

        if urgency and urgency != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["urgency"] = {"name": urgency}

        if level and level != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["level"] = {"name": level}

        if priority and priority != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["priority"] = {"name": priority}

        if technician:
            input_data_payload["request"]["technician"] = {"name": technician}

        if mode and mode != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["mode"] = {"name": mode}

        if site:
            input_data_payload["request"]["site"] = {"name": site}

        if group:
            input_data_payload["request"]["group"] = {"name": group}

        if category and category != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["category"] = {"name": category}

        if due_by_time:
            input_data_payload["request"]["due_by_time"] = {"value": due_by_time}

        if status and status != NONE_DROPDOWN_INDICATOR:
            input_data_payload["request"]["status"] = {"name": status}
        payload = {"input_data": str(input_data_payload)}

        if action_type == CREATE_REQUEST_TYPE:
            request_url = f"{self.api_root}{REQUESTS_URL}"
            result = self.session.post(request_url, data=payload)

        if action_type == UPDATE_REQUEST_TYPE:
            request_url = f"{self.api_root}{SPECIFIC_REQUEST_URL.format(request_id)}"
            result = self.session.put(request_url, data=payload)

        # Verify result.
        self.validate_response(result)

        return self.parser.build_universal_object(result.json())
