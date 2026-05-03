# ==============================================================================
# title           :ServiceDeskPlusManager.py
# description     :This Module contain all Service Desk Plus operations
#                  functionality using REST API
# author          :avital@siemplify.co
# date            :23-4-19
# python_version  :2.7
# ==============================================================================

# BASED ON: https://github.com/MrSimonC/Manage-Engine-Rest-API/blob/master/sdplus_api_rest.py

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import json
import requests
import xmltodict
from xml.etree.ElementTree import Element, SubElement
import defusedxml.ElementTree as ET
import urllib.parse

# =====================================
#             CONSTANTS               #
# =====================================

PAGE_SIZE = 1000
DUE_DATE_FORMAT = "%d %b %Y, %H:%M:%S"

# =====================================
#              CLASSES                #
# =====================================


class ServiceDeskPlusManagerError(Exception):
    pass


class ServiceDeskPlusManager:
    def __init__(self, api_url_base, api_key):
        """
        Initiate values
        :param api_key: technician key
        :param api_url_base: should be base of sdplus api e.g. http://sdplus/sdpapi/
        """
        self.api_key = api_key
        self.api_url_base = api_url_base

    def test_connectivity(self):
        """
        Test connectivity
        :return: {bool} True if connected, exception otherwise.
        """
        try:
            self.list_requests(1)
            return True
        except Exception as e:
            raise ServiceDeskPlusManagerError(
                f"Unable to connect to ServiceDesk Plus. {str(e)}"
            )

    def send(
        self,
        url_append,
        operation,
        input_fields=None,
        attachment="",
        sub_elements=None,
        bypass=False,
    ):
        """
        Send through details into API
        :param url_append: string to append to end of base API url e.g. 21 but not /21
        :param operation: operation name param as specified in ManageEngine API spec
        :param input_fields: dictionary of fields e.g. {'subject': 'EDITED ...' }
        :param attachment: file path to attachment
        :param sub_elements: list of elements to put in xml between the default <Details> and <parameter>
        :param bypass: True/False as to whether to bypass manual processing and use xmltodict module
        :return: {'response_key': 'response value', ...}
        """
        sub_elements = [] if sub_elements is None else sub_elements
        params = {"TECHNICIAN_KEY": self.api_key, "OPERATION_NAME": operation}
        if input_fields:
            xml_input = self._create_xml(input_fields, sub_elements)
            params.update({"INPUT_DATA": xml_input})
        if attachment:
            file = {"file": open(attachment, "rb")}
            response_text = requests.post(
                urllib.parse.urljoin(self.api_url_base, url_append),
                params=params,
                files=file,
            ).text
        else:
            response_text = requests.get(
                urllib.parse.urljoin(self.api_url_base, url_append), params
            ).text
        if bypass:  # needed when xml response is more complex
            return json.loads(json.dumps(xmltodict.parse(response_text)))
        response = ET.fromstring(response_text)
        result = {}
        for status_item in response.iter("result"):
            result = {
                "response_status": status_item.find("status").text,
                "response_message": status_item.find("message").text,
                "response_content": {},
            }

        if result["response_status"] == "Success":
            for param_tags in response.iter("Details"):
                # Assumes xml: parameter, name & value
                if param_tags.findall(r".//parameter"):
                    result["response_content"].update(
                        dict(
                            [
                                (
                                    details_params.find("name").text.lower(),
                                    details_params.find("value").text,
                                )
                                for details_params in param_tags.findall(".//parameter")
                                if details_params is not None
                            ]
                        )
                    )
        return result

    def add_request(
        self,
        subject,
        requester=None,
        technician=None,
        status=None,
        priority=None,
        urgency=None,
        category=None,
        request_template=None,
        due_by_time=None,
        request_type=None,
        description=None,
        mode=None,
        level=None,
        country=None,
        area=None,
        city=None,
        site=None,
        group=None,
        impact=None,
    ):
        """
        Create a new request (incident / service request)
        :param subject: {str} The subject of the request
        :param requester: {str} The name of the requester of the request
        :param technician: {str} The name of the assigned technician
        :param status: {str} The status of the request. Example values:
            Open, Approval Pending, Closed, In Progress, Assigned, Cancelled,
            Asset Provisioning, On Hold, PO Raised, Resolved, etc...
        :param priority: {str} The priority of the request. Example values:
            Low, Medium, High, Normal.
        :param urgency: {str} The urgency of the request. Example values:
            Low. Normal, High, Urgent.
        :param category: {str} The category of the request.
        :param request_template: {str} The template of the request
        :param due_by_time: {str} The due time of the request in the following
            format: "%d %b %Y, %H:%M:%S"
        :param request_type: {str} The type of the request. Example values:
            Incident, Service Request, Convert the Incident to Change,
            Request For Information, etc.
        :param description: {str} The description of the request
        :param mode: {str} The mode of the request. Example  values:
            SMS, Web Form, Phone Call, etc.
        :param level: {str} The tier level of the request. Example values:
            Tier 1, Tier 2, etc.
        :param country: {str} The country of the request
        :param area: {str} The area of the request
        :param city: {str} The city of the request
        :param site: {str} The site of the request
        :param group: {str} The group of the request
        :param impact: {str} The impact of the request. Example values:
            Affects User, Affects Department, Affects Business, Low, etc.
        :return: {str} The id of the new request.
        """
        fields = {
            "requester": requester,
            "subject": subject,
            "technician": technician,
            "status": status,
            "requesttemplate": request_template,
            "duebytime": due_by_time,
            "requesttype": request_type,
            "description": description,
            "category": category,
            "priority": priority,
            "urgency": urgency,
            "mode": mode,
            "level": level,
            "country": country,
            "city": city,
            "area": area,
            "site": site,
            "group": group,
            "impact": impact,
        }

        fields = {k: v for k, v in list(fields.items()) if v is not None}
        response = self.send("request/", "ADD_REQUEST", fields)
        self.validate_response(response, "Unable to create request")
        return response["response_content"].get("workorderid")

    def update_request(
        self,
        request_id,
        requester=None,
        technician=None,
        status=None,
        priority=None,
        urgency=None,
        category=None,
        request_template=None,
        due_by_time=None,
        request_type=None,
        description=None,
        mode=None,
        level=None,
        country=None,
        area=None,
        city=None,
        site=None,
        group=None,
        impact=None,
    ):
        """
        Update a request
        :param request_id: {str} The id of the request to update
        :param requester: {str} The name of the requester of the request
        :param technician: {str} The name of the assigned technician
        :param status: {str} The status of the request. Example values:
            Open, Approval Pending, Closed, In Progress, Assigned, Cancelled,
            Asset Provisioning, On Hold, PO Raised, Resolved, etc...
        :param priority: {str} The priority of the request. Example values:
            Low, Medium, High, Normal.
        :param urgency: {str} The urgency of the request. Example values:
            Low. Normal, High, Urgent.
        :param category: {str} The category of the request.
        :param request_template: {str} The template of the request
        :param due_by_time: {str} The due time of the request in the following
            format: "%d %b %Y, %H:%M:%S"
        :param request_type: {str} The type of the request. Example values:
            Incident, Service Request, Convert the Incident to Change,
            Request For Information, etc.
        :param description: {str} The description of the request
        :param mode: {str} The mode of the request. Example  values:
            SMS, Web Form, Phone Call, etc.
        :param level: {str} The tier level of the request. Example values:
            Tier 1, Tier 2, etc.
        :param country: {str} The country of the request
        :param area: {str} The area of the request
        :param city: {str} The city of the request
        :param site: {str} The site of the request
        :param group: {str} The group of the request
        :param impact: {str} The impact of the request. Example values:
            Affects User, Affects Department, Affects Business, Low, etc.
        :return: {bool} True if successful, exception otherwise.
        """
        fields = {
            "requester": requester,
            "technician": technician,
            "status": status,
            "requesttemplate": request_template,
            "duebytime": due_by_time,
            "requesttype": request_type,
            "description": description,
            "category": category,
            "priority": priority,
            "urgency": urgency,
            "mode": mode,
            "level": level,
            "country": country,
            "city": city,
            "area": area,
            "site": site,
            "group": group,
            "impact": impact,
        }

        fields = {k: v for k, v in list(fields.items()) if v is not None}
        response = self.send(f"request/{request_id}", "EDIT_REQUEST", fields)
        self.validate_response(response, f"Unable to update request {request_id}")
        return True

    def get_request(self, request_id):
        """
        Get a request by id
        :param request_id: {str} The id of the request
        :return: {dict} The info of the request
        """
        return self.send(f"request/{request_id}", "GET_REQUEST")["response_content"]

    def delete_request(self, request_id):
        """
        Delete a request
        :param request_id: {str} The id of the request to delete
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.send(f"request/{request_id}", "DELETE_REQUEST")
        self.validate_response(response, f"Unable to delete request {request_id}")
        return True

    def close_request(self, request_id, accepted=False, comment=""):
        """
        Close a request.
        :param request_id: {str} The id of the request
        :param accepted: {bool} Whether the request is accepted or not
        :param comment: {str} Comment to put in the closure comments box
        :return: {bool} True if successful, exception otherwise.
        """
        if accepted:
            accepted_text = "Accepted"
        else:
            accepted_text = ""

        fields = {"closeAccepted": accepted_text, "closeComment": comment}

        response = self.send(f"request/{request_id}", "CLOSE_REQUEST", fields)
        self.validate_response(response, f"Unable to close request {request_id}")
        return True

    def get_request_conversations(self, request_id):
        """
        Get conversions of a request
        :param request_id: {str} The id of the request
        :return: {list} The conversations of the request
        """
        result = self.send(
            f"request/{request_id}/conversation", "GET_CONVERSATIONS", bypass=True
        )
        conversations = self.output_params_to_list(result)

        for conversation in conversations:
            conversation.update(
                self.get_request_conversation_by_id(
                    request_id, conversation.get("conversationid")
                )
            )

        return conversations

    def get_request_conversation_by_id(self, request_id, conversation_id):
        """
        Get the details of a conversation of a request by id
        :param request_id: {str} The request id
        :param conversation_id: {str} The converstion id
        :return: {dict} The conversation details
        """
        result = self.send(
            f"request/{request_id}/conversation/{conversation_id}",
            "GET_CONVERSATION",
            bypass=True,
        )

        conversation = self.output_params_to_list(result)

        if conversation:
            return conversation[0]

        return {}

    def add_request_attachment(self, request_id, attachment_path):
        """
        Add an attachment to a request
        :param request_id: {str} The id of the request
        :param attachment_path: {str} The path of the file to attach
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.send(
            f"request/{request_id}/attachment",
            "ADD_ATTACHMENT",
            attachment=attachment_path,
        )
        self.validate_response(
            response, f"Unable to add attachment to request {request_id}"
        )
        return True

    def add_request_resolution(self, request_id, text):
        """
        Add resolution to a request
        :param request_id: {str} The id of the request
        :param text: {str} The resolution text
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.send(
            url_append=f"request/{request_id}/resolution",
            operation="ADD_RESOLUTION",
            input_fields={"resolutiontext": text},
            sub_elements=["resolution"],
        )
        self.validate_response(
            response, f"Unable to add resolution to request {request_id}"
        )
        return True

    def edit_request_resolution(self, request_id, text):
        """
        Edit the resolution of a request
        :param request_id: {str} The id of the request
        :param text: {str} The text of the resolution
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.send(
            url_append=f"request/{request_id}/resolution",
            operation="EDIT_RESOLUTION",
            input_fields={"resolutiontext": text},
            sub_elements=["resolution"],
        )
        self.validate_response(
            response, f"Unable to edit the resolution of request {request_id}"
        )
        return True

    def assign_request_by_id(self, request_id, technician_id):
        """
        Assign a technician to a request by id
        :param request_id: {str} The id of the request
        :param technician_id: {str} The id of the technician
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.send(
            f"request/{request_id}", "ASSIGN_REQUEST", {"technicianid": technician_id}
        )

        self.validate_response(
            response,
            f"Unable to assign technician {technician_id} to request {request_id}",
        )

        return True

    def list_requests(self, limit=None):
        """
        List requests (descending order)
        :param limit: {int} The max amount of requests to fetch
        :return: {list} The found requests
        """
        found_requests = []
        start_from = 0

        fields = {
            "from": str(start_from),
            "limit": str(PAGE_SIZE),
            "filterby": "All_Requests",
        }

        results = self.send("request/", "GET_REQUESTS", fields, bypass=True)
        results = self.output_params_to_list(results)

        while results:
            if limit and len(found_requests) >= limit:
                break

            found_requests.extend(results)
            start_from += PAGE_SIZE

            fields = {
                "from": str(start_from),
                "limit": str(PAGE_SIZE),
                "filterby": "All_Requests",
            }

            results = self.send("request/", "GET_REQUESTS", fields, bypass=True)
            results = self.output_params_to_list(results)

        return found_requests[:limit] if limit else found_requests

    def get_request_notification_by_id(self, request_id, notification_id):
        """
        Get notification details by id
        :param request_id: {str} The request id
        :param notification_id: {str} The id of the notification
        :return: {dict} The notification details
        """
        notification = self.send(
            f"request/{request_id}/notification/{notification_id}",
            "GET_NOTIFICATION",
            bypass=True,
        )
        return self.output_params_to_list(notification)

    def get_request_notifications(self, request_id):
        """
        Get the notifications of a request
        :param request_id: {str} The id of the request
        :return: {list} The notifications of the request
        """
        notifications = self.send(
            f"request/{request_id}/notification/", "GET_NOTIFICATIONS", bypass=True
        )
        notifications = self.output_params_to_list(notifications)

        for notification in notifications:
            notification.update(
                self.get_request_notification_by_id(
                    request_id, notification.get("notifyid")
                )
            )

        return notifications

    def get_request_notes(self, request_id):
        """
        Get the notifications of a request
        :param request_id: {str} The id of the request
        :return: {list} The notifications of the request
        """
        notes = self.send(f"request/{request_id}/notes/", "GET_NOTES", bypass=True)
        return self.output_params_to_list(notes)

    def add_note(self, request_id, is_public=False, text=""):
        """
        Add a note to a request
        :param request_id: {str} The ID of the request
        :param is_public: {bool} Whether the note is public or not
        :param text: {str} The message of the note
        :return: {bool} True if successful, exception otherwise
        """
        fields = {"isPublic": str(is_public), "notesText": text}

        response = self.send(
            f"request/{request_id}/notes",
            "ADD_NOTE",
            fields,
            sub_elements=["Notes", "Note"],
        )

        self.validate_response(response, f"Unable to add note to request {request_id}")

        return True

    def list_technicians(self):
        """
        List the available technicians
        :return: {list} The technicians details
        """
        technicians = self.send(
            "technician/", "GET_ALL", {"siteName": "", "groupid": ""}, bypass=True
        )
        return self.output_params_to_list(technicians)

    def assign_request(self, full_name, request_id):
        """
        Assign a technician to a request
        :param full_name: {str} The name of the technicians to assign
        :param request_id: {str} The id of the request
        :return: {bool} True if successful, exception otherwise.
        """
        technicians = self.list_technicians()

        for technician in technicians:
            if technician.get("technicianname") == full_name:
                self.assign_request_by_id(request_id, technician.get("technicianid"))
                return True

        raise ServiceDeskPlusManagerError(f"Technician {full_name} was not found.")

    @staticmethod
    def _create_xml(fields, sub_elements=None):
        """
        Makes xml out of parameters
        :param fields: dict of main values e.g.  {'isPublic': 'false', 'notesText': 'Simon Crouch'...}
        :param starting_element: string
        :param sub_elements: list of elements to put in xml between the default <Details> and <parameter>
        :return:
        """
        sub_elements = [] if sub_elements is None else sub_elements
        xml_string = Element("Operation")  # Standard as part of the API
        details = SubElement(xml_string, "Details")  # Standard as part of the API
        current_parent = details
        for sub in sub_elements:
            current_parent = SubElement(current_parent, sub)
        for key, value in list(fields.items()):
            param = SubElement(current_parent, "parameter")
            SubElement(param, "name").text = key
            SubElement(param, "value").text = value
        return ET.tostring(xml_string)

    @staticmethod
    def output_params_to_list(response):
        """
        Outputs a list of parameters in a list of dict values
        :param response: output response from API in json
        :return: list: [{'key': 'value'}, {'key': 'value'}, ...
        """
        all_params = []
        try:
            records = response["API"]["response"]["operation"]["Details"]["record"]
        except KeyError:
            try:
                records = response["API"]["response"]["operation"]["Details"]["Notes"][
                    "Note"
                ]
            except KeyError:
                return []
        if isinstance(records, dict):  # 1 record
            parameters_dict = {}
            for param in records["parameter"]:
                parameters_dict[param["name"].lower()] = param["value"]
            all_params.append(parameters_dict)
        elif isinstance(records, list):  # > 1 record
            for record in records:
                parameters_dict = {}
                for param in record["parameter"]:
                    parameters_dict[param["name"].lower()] = param["value"]
                all_params.append(parameters_dict)
        return all_params

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Check if response is valid and operation is successful
        """
        if response.get("response_status") != "Success":
            raise ServiceDeskPlusManagerError(
                f"{error_msg}: {response.get('response_message')}."
            )
