# coding=utf-8
# ==============================================================================
# title      :SymantecATPManager.py
# description   :This Module contain all Slack remote operations functionality
# author     :victor@siemplify.co
# date      :21-11-18
# python_version :2.7
# Product Version: 3.2
# ==============================================================================
# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import urllib.parse
import copy
import arrow
import base64

from .SymantecATPParser import SymantecATPParser
from .SymantectATPDataModelTransformationLayer import build_siemplify_comment_object
from .constants import (
    MIN_INCIDENTS_TO_FETCH,
    MAX_INCIDENTS_TO_FETCH,
    LATEST_EVENTS_FOR_INCIDENT,
    ATP_QUERIES_TIME_FORMAT,
)


# =====================================
#             CONSTANTS               #
# =====================================
# URLs
LOGIN_URL = "atpapi/oauth2/tokens"
GET_ENTITIES_URL = "atpapi/v2/entities/endpoints"
COMMANDS_URL = "atpapi/v2/commands"
COMMANDS_STATUS_URL = "atpapi/v2/commands/{0}"  # {0} - Command ID.
GET_EVENTS_URL = "atpapi/v2/events"
GET_FILE_DETAILS_URL = "atpapi/v2/entities/files/{0}"  # {0} - File Hash.
GET_INCIDENTS_URL = "atpapi/v2/incidents"
GET_INCIDENTEVENTS_URL = "atpapi/v2/incidentevents"
BLACKLISTS_URL = "atpapi/v2/policies/blacklist"
BLACKLIST_DELETE_URL = "atpapi/v2/policies/blacklist/{0}"  # {0} - Blacklist ID.
WHITELIST_URL = "atpapi/v2/policies/whitelist"
WHITELIST_POLICY_DELETE_URL = (
    "atpapi/v2/policies/whitelist/{0}"  # {0} - Whitelist Policy ID.
)
INCIDENT_URL = "atpapi/v2/incidents"
SANDBOX_COMMANDS_URL = "atpapi/v2/sandbox/commands"
SANDBOX_COMMANDS_STATUS_URL = "atpapi/v2/sandbox/commands/{0}"  # {0} - Command ID.
UPDATE_INCIDENT_RESOLUTION_URL = "atpapi/v2/incidents"
GET_INCIDENT_COMMENTS_URL = "atpapi/v2/incidents/{}/comments"

# Data
LOGIN_DATA = "grant_type=client_credentials&scope=customer"
ADDRESS_TARGET_TYPE = "ip"
HASH_TARGET_TYPE = "url"
URL_TARGET_TYPE = "url"
HOST_TARGET_TYPE = "domain"

SHA256_LENGTH = 64
# =====================================
#             PAYLOADS                #
# =====================================
LOGIN_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}
REQUEST_HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer {0}"}
QUERY_PAYLOAD = {"verb": "query"}
ISOLATE_ENDPOINT_PAYLOAD = {"action": "isolate_endpoint", "targets": []}

REJOIN_ENDPOINT_PAYLOAD = {"action": "rejoin_endpoint", "targets": []}

FREE_EVENTS_QUERY_PAYLOAD = {
    "verb": "query",
    "query": "<LUCENE QUERY STRING>",
    "limit": 100,
}

GET_INCIDENTS_SINCE_TIME_PAYLOAD = {
    "verb": "query",
    "start_time": "2016-06-08T15:39:55.616Z",
    "end_time": "2016-06-11T15:39:55.616Z",
}

GET_INCIDENTS_PAYLOAD = {
    "verb": "query",
    "query": "(priority_level:1 OR priority_level:2 OR priority_level:3) AND !state:4",
    "limit": MAX_INCIDENTS_TO_FETCH,
    "next": "",
}

GET_INCIDENTEVENTS_PAYLOAD = {
    "verb": "query",
    "query": "incident:{uuid}",
    "limit": 5000,
}

DELETE_FILE_PAYLOAD = {
    "action": "delete_endpoint_file",
    "targets": [
        {
            "hash": "8692251329fef60490be1c26281710b7e88250fd82b3f679f87d6785db854ed5",
            "device_uid": "cb46d251-151d-4583-a8fb-ebff7c42cfd8",
        }
    ],
}

GET_EVENTS_FOR_ENTITY_SINCE_PAYLOAD = {
    "verb": "query",
    "query": '{0}:"{1}"',
    "start_time": "2016-06-08T15:39:55.616Z",
    "end_time": "2016-06-11T15:39:55.616Z",
}

CREATE_BLACKLIST_POLICY_PAYLOAD = {
    "verb": "create",
    "policies": [
        {
            "target_type": "ip",
            "target_value": "1.1.1.201",
            "comment": "Blocked by Siemplify.",
        }
    ],
}


CREATE_WHITELIST_POLICY_PAYLOAD = {
    "verb": "create",
    "policies": [
        {
            "target_type": "ip",
            "target_value": "1.1.1.201",
            "comment": "Whiltelisted by Siemplify.",
        }
    ],
}


CLOSE_INCIDENT_PAYLOAD = {"op": "replace", "path": "/{0}/state", "value": 4}

ADD_INCIDENT_COMMENT_PAYLOAD = {"op": "add", "path": "/{0}/comments", "value": ""}

DETONATE_HASH_PAYLOAD = {"action": "analyze", "targets": []}

# Value 4 is fixed value that closes the incident
UPDATE_INCIDENT_RESOLUTION_PAYLOAD = [
    {"op": "replace", "path": "/{}/state", "value": 4},
    {"op": "replace", "path": "/{}/resolution", "value": 0},
]

# Limit of 20 is the default one
GET_INCIDENT_COMMENTS_PAYLOAD = {"verb": "query", "limit": 20}


# =====================================
#              CLASSES                #
# =====================================
class SymantecATPManagerError(Exception):
    pass


class SymantecATPTokenPermissionError(Exception):
    """
    General Exception for Symantec ATP token permissions denied (status code - 403)
    """

    pass


class SymantecATPIncidentNotFoundError(Exception):
    """
    General Exception for Symantec ATP incident was not found (status code - 404)
    """

    pass


class SymantecATPBlacklistPolicyNotFoundError(Exception):
    """
    General Exception for Symantec ATP blacklist policy was not found (status code - 404)
    """

    pass


class SymantecATPNoBlacklistPoliciesError(Exception):
    """
    General Exception for Symantec ATP in which ATP doesn't have any blacklist policies in place at all (status code - 404)
    """

    pass


class ATPEntityTypes:
    """
    Entity types for 'create_blacklist_policy' functions which sends the type of the entity at the payload.
    """

    SHA256 = "sha256"
    MD5 = "md5"
    ADDRESS = "ip"
    HOST = "domain"
    URL = "url"


class SymantecATPManager:
    def __init__(self, api_root, client_id, client_secret, verify_ssl=False):
        """
        :param api_root: api root url {string}
        :param client_id: client id {string}
        :param client_secret: client secret {string}
        """
        self.api_root = api_root
        self.parser = SymantecATPParser()

        # Setup session.
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = (client_id, client_secret)
        self.session.headers = copy.deepcopy(REQUEST_HEADERS)
        self.session.headers["Authorization"] = self.session.headers[
            "Authorization"
        ].format(self.get_access_token())

    @staticmethod
    def validate_api_root(api_root):
        """
        Validate API root string contains '/' at the end because 'urlparse' lib is used.
        :param api_root: api root url {string}
        :return: valid api root {string}
        """
        if api_root[-1] == "/":
            return api_root
        return api_root + "/"

    @staticmethod
    def validate_response(http_response):
        """
        Validated an HTTP response.
        :param http_response: HTTP response object.
        :return: {void}
        """
        try:
            http_response.raise_for_status()

        except requests.HTTPError as err:
            raise SymantecATPManagerError(
                f"Status Code: {http_response.status_code}, Content: {http_response.content}, Error: {err}"
            )

    @staticmethod
    def is_hash_sha256(file_hash):
        """
        Check if file hash is from sha256 type.
        :param file_hash: {string} File hash value.
        :return: {bool} True if hash is a sha256.
        """
        return len(file_hash) == SHA256_LENGTH

    def get_access_token(self):
        """
        Get session token.
        :return: access token {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, LOGIN_URL)
        login_headers = copy.deepcopy(LOGIN_HEADERS)
        response = self.session.post(
            request_url, headers=login_headers, data=LOGIN_DATA
        )
        self.validate_response(response)
        access_token = response.json().get("access_token")
        if access_token:
            # Basic auth is not needed anymore.
            self.session.auth = None
            # Return Token
            return access_token

        raise SymantecATPManagerError("Error: No access token received.")

    def get_endpoints(self):
        """
        Get list of entities objects.
        :return: list of entity objects {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_ENTITIES_URL)
        payload = {"verb": "query"}
        response = self.session.post(request_url, json=payload)
        return response.json().get("result")

    def get_endpoint_uuid_by_ip(self, ip_address):
        """
        Get endpoint uuid by ip address.
        :param ip_address: ip address {string}
        :return: endpoint uuid {string}
        """
        endpoints_obj_list = self.get_endpoints()

        for endpoint_obj in endpoints_obj_list:
            if ip_address == endpoint_obj.get("device_ip"):
                return endpoint_obj.get("device_uid")

        raise SymantecATPManagerError(
            f'Endpoint with address "{ip_address}" was not found.'
        )

    def get_endpoint_uuid_by_hostname(self, hostname):
        """
        Get endpoint uuid by hostname.
        :param hostname: ip address {string}
        :return: endpoint uuid {string}
        """
        endpoints_obj_list = self.get_endpoints()

        for endpoint_obj in endpoints_obj_list:
            if hostname.lower() == endpoint_obj.get("device_name", "").lower():
                return endpoint_obj.get("device_uid")

        raise SymantecATPManagerError(
            f'Endpoint for hostname "{hostname}" was not found.'
        )

    def isolate_endpoint_by_uid(self, endpoint_uid):
        """
        Isolate endpoint by it's uid.
        :param endpoint_uid: endpoint's uid {string}
        :return: command id {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, COMMANDS_URL)

        payload = copy.deepcopy(ISOLATE_ENDPOINT_PAYLOAD)
        payload["targets"].append(endpoint_uid)

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.json().get("command_id")

    def rejoin_endpoint_by_uid(self, endpoint_uid):
        """
        Rejoin endpoint by it's uid.
        :param endpoint_uid: endpoint's uid {string}
        :return: command id {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, COMMANDS_URL)

        payload = copy.deepcopy(REJOIN_ENDPOINT_PAYLOAD)
        payload["targets"].append(endpoint_uid)

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.json().get("command_id")

    def get_command_status_report_by_id(self, command_id):
        """
        Get command status by it's id.
        :param command_id: command id {string}
        :return: command status dict {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, COMMANDS_STATUS_URL.format(command_id)
        )
        payload = copy.deepcopy(QUERY_PAYLOAD)
        response = self.session.post(request_url, json=payload)
        self.validate_response(response)

        return response.json()

    def get_events_free_query(self, query, limit):
        """
        Free events query.
        :param query: query string {string}
        :param limit: result events amount limit {integers}
        :return: list of events {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_EVENTS_URL)

        payload = copy.deepcopy(FREE_EVENTS_QUERY_PAYLOAD)
        payload["query"] = query
        payload["limit"] = limit

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.json().get("result")

    def get_file_details_by_hash(self, file_hash):
        """
        Get file details by hash.
        :param file_hash: file hash {string}
        :return: file details {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_FILE_DETAILS_URL.format(file_hash)
        )
        response = self.session.get(request_url)
        self.validate_response(response)

        return response.json()

    def get_incidents_since(self, arrow_start_datetime, arrow_end_datetime):
        """
        Get incidents since time.
        :param arrow_start_datetime: {Arrow}
        :param arrow_end_datetime: {Arrow}
        :return: list of incidents objects {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_INCIDENTS_URL)

        payload = copy.deepcopy(GET_INCIDENTS_SINCE_TIME_PAYLOAD)
        payload["start_time"] = self._convert_to_api_time_format(arrow_start_datetime)
        payload["end_time"] = self._convert_to_api_time_format(arrow_end_datetime)

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.json().get("result")

    def get_incidents(self, priorities, last_event_seen, limit, asc=True):
        # type: (list, datetime.datetime, int, bool) -> [Incident]
        """
        Fetch all incidents with filtering
        @param priorities: List of priorities. Ex. ['Low', 'Medium', 'High']
        @param last_event_seen: Datetime from which to start fetching events. last_event_seen in Incident
        @param limit: To limit incidents
        @param asc: Fetch incidents by last_event_seen ASC, otherwise DESC
        @return: List of Incidents
        """
        url = urllib.parse.urljoin(self.api_root, INCIDENT_URL)
        payload = copy.deepcopy(GET_INCIDENTS_PAYLOAD)

        priorities = self.parser.convert_siem_priorities_to_symantec(priorities)
        limit = min(max(limit, MIN_INCIDENTS_TO_FETCH), MAX_INCIDENTS_TO_FETCH)

        payload["query"] = "({}) AND !state:4 AND last_event_seen:[{} TO now]".format(
            " OR ".join([f"priority_level:{priority}" for priority in priorities]),
            self._convert_to_api_time_format(last_event_seen),
        )
        payload["limit"] = limit

        if asc:
            total, next = self._get_total_and_next_incidents(payload["query"])
            payload["next"] = self._build_next_offset(total, limit, next)

        response = self.session.post(url, json=payload)
        self.validate_response(response)

        incidents_data = response.json().get("result", [])

        return [
            self.parser.build_incident(incident_data)
            for incident_data in incidents_data
        ]

    @staticmethod
    def _build_next_offset(total, limit, next):
        # type: (int, int, str or unicode) -> str or unicode or None
        """
        Decode current next to extract offset and paste calculated with limit and total.
        @param total: Total incidents
        @param limit: Limit which indicates how many incidents do we need.
        @param next: Next to request pagination
        @return: New next parameter
        """
        if not next:
            return next

        offset = max(total - limit, 0)
        fetch_time = base64.b64decode(next).split(",")[-1]
        return base64.b64encode(f"{offset},{fetch_time}")

    def _get_total_and_next_incidents(self, query, limit=1):
        # type: (str or unicode, int) -> (int, str or unicode or None) or Exception
        """
        First request to count how many incident we have to be able to create offset.
        @param query: Query for Symantec ATP
        @param limit: Limit which indicates how many incidents do we need.
        By default 1, because we need only total and next params
        @return: Total and next
        """
        url = urllib.parse.urljoin(self.api_root, INCIDENT_URL)
        payload = copy.deepcopy(GET_INCIDENTS_PAYLOAD)

        payload["query"] = query
        payload["limit"] = limit

        response = self.session.post(url, json=payload)
        self.validate_response(response)

        response_data = response.json()

        return response_data.get("total", 0), response_data.get("next")

    def fetch_events_for_incident(self, incident, latest=LATEST_EVENTS_FOR_INCIDENT):
        # type: (Incident, int) -> Incident
        """
        Fetch and fill incident with his events
        @param incident: Incident from API
        @param latest: How many events to take from response
        @return: Incident filled with events
        """
        url = urllib.parse.urljoin(self.api_root, GET_INCIDENTEVENTS_URL)
        payload = copy.deepcopy(GET_INCIDENTEVENTS_PAYLOAD)
        payload["query"] = payload["query"].format(uuid=incident.uuid)

        response = self.session.post(url, json=payload)
        self.validate_response(response)

        # Take only the latest 100
        events_data = response.json().get("result", [])[-latest:]
        incident.events = events_data

        return incident

    def delete_endpoint_file(self, endpoint_uuid, file_hash):
        """
        Delete file from endpoint.
        :param endpoint_uuid: {string}
        :param file_hash: {string}
        :return: command_id {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, COMMANDS_URL)

        payload = copy.deepcopy(DELETE_FILE_PAYLOAD)
        payload["targets"][0]["device_uid"] = endpoint_uuid
        payload["targets"][0]["hash"] = file_hash

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.json().get("command_id")

    def get_event_for_entity_since(
        self,
        search_field,
        entity_identifier,
        arrow_since_time,
        arrow_till_time=arrow.now(),
    ):
        """
        Get events which contains specific entities.
        :param search_field: field based on which search is done {string}
        :param entity_identifier: entity's ip address or host name {string}
        :param arrow_since_time: time object {arrow}
        :param arrow_till_time: time object {arrow}
        :return: list of events object {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_EVENTS_URL)

        payload = copy.deepcopy(GET_EVENTS_FOR_ENTITY_SINCE_PAYLOAD)
        payload["query"] = payload["query"].format(search_field, entity_identifier)

        # times.
        start_time = self._convert_to_api_time_format(arrow_since_time)
        end_time = self._convert_to_api_time_format(arrow_till_time)

        payload["start_time"] = start_time
        payload["end_time"] = end_time

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.json().get("result")

    def get_incident_related_events_since_time(
        self, arrow_since_time, arrow_till_time=arrow.now()
    ):
        """
        Get incident related events since time.
        :param arrow_since_time: time object {arrow}
        :param arrow_till_time: time object {arrow}
        :return: list of events object {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_INCIDENTEVENTS_URL)

        # Times.
        start_time = self._convert_to_api_time_format(arrow_since_time)
        end_time = self._convert_to_api_time_format(arrow_till_time)

        # Payload.
        payload = copy.deepcopy(GET_INCIDENTS_SINCE_TIME_PAYLOAD)
        payload["start_time"] = start_time
        payload["end_time"] = end_time

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.json().get("result")

    def create_blacklist_policy(self, entity_identifier, entity_type):
        """
        Create a blacklist policy for a hash.
        :param entity_identifier: unique entity identifier(hash, host or address) {string}
        :param entity_type: the type of the target entity has to be property of the "ATPEntityTypes" class {string}
        :return: list of block policies ids {list}
        """
        requset_url = urllib.parse.urljoin(self.api_root, BLACKLISTS_URL)

        payload = copy.deepcopy(CREATE_BLACKLIST_POLICY_PAYLOAD)
        payload["policies"][0]["target_type"] = entity_type
        payload["policies"][0]["target_value"] = entity_identifier

        response = self.session.post(requset_url, json=payload)

        self.validate_response(response)

        return response.json().get("ids")

    def get_whitelist_policy_id_by_identifier(self, entity_identifier):
        """
        Get the blacklist policy id for an entity identifier(hash, host or address).
        :param entity_identifier: unique entity identifier(hash, host or address) {string}
        :return: policy id {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, WHITELIST_URL)

        response = self.session.get(request_url)

        self.validate_response(response)

        if response.json().get("result"):
            for policy in response.json().get("result"):
                if policy.get("target_value", "").lower() == entity_identifier:
                    return policy.get("id")
            raise SymantecATPManagerError(
                f"No found whitelist policy for {entity_identifier}"
            )
        else:
            raise SymantecATPManagerError("No whitelist policies found.")

    def create_whitelist_policy(self, entity_identifier, entity_type):
        """
        :param entity_identifier: {string} Target entity identifier.
        :param entity_type: {string} Thr type of the entity, can be: "ip", "domain", "url" or "sha256".
        :return: {bool} True if succeed.
        """
        requset_url = urllib.parse.urljoin(self.api_root, WHITELIST_URL)
        payload = copy.deepcopy(CREATE_WHITELIST_POLICY_PAYLOAD)
        payload["policies"][0]["target_type"] = entity_type
        payload["policies"][0]["target_value"] = entity_identifier
        response = self.session.post(requset_url, json=payload)
        self.validate_response(response)
        return response.json().get("ids")

    def delete_whitelist_policy_by_identifier(self, entity_identifier):
        """
        Delete whitelist policy by entity identifier.
        :param entity_identifier: {stirng} Target entity identifier.
        :return: {bool} True if success.
        """
        policy_id = self.get_whitelist_policy_id_by_identifier(entity_identifier)
        request_url = urllib.parse.urljoin(
            self.api_root, WHITELIST_POLICY_DELETE_URL.format(policy_id)
        )
        response = self.session.delete(request_url)
        self.validate_response(response)
        return True

    def close_incident(self, incident_uuid):
        """
        Change incident's status to closed.
        :param incident_uuid: {string}
        :return: {bool} True if succeed.
        """
        payload = copy.deepcopy(CLOSE_INCIDENT_PAYLOAD)
        payload["path"] = payload["path"].format(incident_uuid)
        request_url = urllib.parse.urljoin(self.api_root, INCIDENT_URL)
        response = self.session.patch(request_url, json=[payload])
        self.validate_response(response)
        return True

    def add_incident_comment(self, incident_uuid, comment):
        """
        Add a comment to an incident.
        :param incident_uuid: {string} Incident uuid.
        :param comment: {string} Comment content.
        :return: {bool} True if succeed.
        """
        payload = copy.deepcopy(ADD_INCIDENT_COMMENT_PAYLOAD)
        payload["path"] = payload["path"].format(incident_uuid)
        payload["value"] = comment
        request_url = urllib.parse.urljoin(self.api_root, INCIDENT_URL)
        response = self.session.patch(request_url, json=[payload])
        self.validate_response(response)
        return True

    def submit_file_to_sandbox(self, file_hash):
        """
        Analyze file hash by sending to sandbox.
        :param file_hash: {string} sha-256 file hash.
        :return: {string} Command ID.
        """
        payload = copy.deepcopy(DETONATE_HASH_PAYLOAD)
        payload["targets"].append(file_hash)
        request_url = urllib.parse.urljoin(self.api_root, SANDBOX_COMMANDS_URL)
        response = self.session.post(request_url, json=payload)
        self.validate_response(response)
        return response.json().get("command_id")

    def get_command_status(self, command_id):
        """
        Get command status.
        :param command_id: {string} Target command ID.
        :return: {dict} Status results
        """
        request_url = urllib.parse.urljoin(
            self.api_root, SANDBOX_COMMANDS_STATUS_URL.format(command_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    @staticmethod
    def _convert_to_api_time_format(time):
        # type: (datetime.datetime) -> str or unicode
        """
        Method to convert time to ATP time format (including only milliseconds)
        @param time: Datetime
        @return: String in presented time format
        """
        return time.strftime(ATP_QUERIES_TIME_FORMAT)[:-4] + "Z"

    @staticmethod
    def validate_response_customized(http_response):
        """
        Validated an HTTP response.
        :param http_response: HTTP response object.
        :return: {None}
        """

        try:
            if http_response.status_code == 403:
                raise SymantecATPTokenPermissionError(
                    f"Status Code: {http_response.status_code}, Content: {http_response.content}"
                )

            if http_response.status_code == 404 and http_response.content:
                if "Specified uuid could not be found" in http_response.content:
                    raise SymantecATPIncidentNotFoundError(
                        f"Status Code: {http_response.status_code}, Content: {http_response.content}"
                    )

            http_response.raise_for_status()

        except requests.HTTPError as err:
            raise SymantecATPManagerError(
                f"Status Code: {http_response.status_code}, Content: {http_response.content}, Error: {err}"
            )

    def update_incident_resolution(self, incident_uuid, resolution_status):
        """
        Update Incident Resolution.
        :param incident_uuid: {string} Incident uuid.
        :param resolution_status: {int} Resolution Status.
        """
        payload = copy.deepcopy(UPDATE_INCIDENT_RESOLUTION_PAYLOAD)
        payload[0]["path"] = payload[0]["path"].format(incident_uuid)
        payload[1]["path"] = payload[1]["path"].format(incident_uuid)
        payload[1]["value"] = resolution_status

        request_url = urllib.parse.urljoin(
            self.api_root, UPDATE_INCIDENT_RESOLUTION_URL
        )
        response = self.session.patch(request_url, json=payload)
        self.validate_response_customized(response)

    def get_blacklist_policy_id_by_identifier(
        self, entity_identifier, action_name=None
    ):
        """
        Get the blacklist policy id for an entity identifier(hash, host or address).
        :param entity_identifier: unique entity identifier(hash, host or address) {string}
        :param action_name: param defining which action is running this function {string}
        :return: policy id {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, BLACKLISTS_URL)

        response = self.session.get(request_url)

        self.validate_response(response)

        if response.json().get("result"):
            for policy in response.json().get("result"):
                if policy.get("target_value").lower() == entity_identifier.lower():
                    return policy.get("id")

            if action_name == "SymantecATP_Delete Blacklist Policy":
                raise SymantecATPBlacklistPolicyNotFoundError(
                    f"Blacklist policy for {entity_identifier} not found"
                )
            raise SymantecATPManagerError(
                f"No found blacklist policy for {entity_identifier}"
            )
        else:
            if action_name == "SymantecATP_Delete Blacklist Policy":
                raise SymantecATPBlacklistPolicyNotFoundError(
                    "No blacklist policies found."
                )
            else:
                raise SymantecATPManagerError("No blacklist policies found.")

    def delete_blacklist_policy_by_identifier(
        self, entity_identifier, action_name=None
    ):
        """
        Delete black list policy by entity identifier.
        :param entity_identifier: unique entity identifier(hash, host or address) {string}
        :param action_name: param defining which action is running this function {string}
        :return: is success {bool}
        """

        if action_name == "SymantecATP_Delete Blacklist Policy":
            policy_id = self.get_blacklist_policy_id_by_identifier(
                entity_identifier, action_name
            )
        else:
            policy_id = self.get_blacklist_policy_id_by_identifier(entity_identifier)
        request_url = urllib.parse.urljoin(
            self.api_root, BLACKLIST_DELETE_URL.format(policy_id)
        )

        response = self.session.delete(request_url)

        self.validate_response(response)

        return True

    def get_comments_for_incident(self, incident_uuid, limit):
        """
        Get Comments for incident.
        :param incident_uuid: {string} Incident uuid.
        :param limit: Specifies how many comments to return. {int}
        :return: List Of Comments {List}
        """

        request_url = urllib.parse.urljoin(
            self.api_root, GET_INCIDENT_COMMENTS_URL.format(incident_uuid)
        )
        payload = copy.deepcopy(GET_INCIDENT_COMMENTS_PAYLOAD)
        payload["limit"] = limit
        response = self.session.post(request_url, json=payload)
        self.validate_response_customized(response)
        comments = response.json().get("result", [])
        return [
            build_siemplify_comment_object(comments_json) for comments_json in comments
        ]
