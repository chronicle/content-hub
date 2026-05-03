# ==============================================================================
# title           :SentinelOneManager.py
# description     :SentinelOne integration logic.
# author          :victor@siemplify.co
# date            :21-3-18
# python_version  :2.7
# ==============================================================================

# ==============================================================================
# Remarks:

#  'get_events_for_endpoint_by_date' return 404 from API.
#  'get_hash_reputation' return 404 from API.
#  'fetch_files_for_agent' return 409 from API -> Version does not support feature.

# ==============================================================================


# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import urllib.parse
import copy

# =====================================
#               CONSTS                #
# =====================================
# Time Formats.
FETCH_EVENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
# URLs.
LOGIN_URL = "web/api/v1.6/users/login"
GET_SYSTEM_INFORMATION_URL = "web/api/v1.6/status"
GET_SYSTEM_VERSION_URL = "web/api/v1.6/info"
GET_AGENTS_URL = "web/api/v1.6/agents"
RESTART_MACHINE_URL = "web/api/v1.6/agents/restart-machine"
UPDATE_AGENT_SOFTWARE_URL = "web/api/v1.6/agents/update-software"
INITIATE_SCAN_URL = "web/api/v1.6/agents/initiate-scan"
GET_AGENT_PROCESSES_LIST_URL = "web/api/v1.6/agents/{0}/processes"  # {0} - Agent ID.
GET_EVENTS_FOR_ENDPOINT_URL = "web/api/v1.6/events/process/{0}"  # {0} - Agent UUID.
GET_HASH_REPUTATION_URL = "web/api/v1.6/hashes/{0}/reputation"  # {0} - File Hash(SHA1).
GET_HASH_DATA_URL = "web/api/v1.6/hashes/{0}"  # {0} - File Hash(SHA1).
GET_ENDPOINT_SYSTEM_INFO_URL = "web/api/v1.6/agents/{0}"  # {0} - Agent ID.
GET_SYSTEM_SETTINGS_INFO_URL = "web/api/v1.6/server-settings"
GET_THREATS_BY_ENDPOINT_URL = "web/api/v1.6/threats"
GET_REPORTS_URL = "web/api/v1.6/reports"
GET_APPLICATIONS_URL = "web/api/v1.6/agents/{0}/applications"  # {0} - Agent ID.
GET_EXCLUSION_LISTS_URLS = "web/api/v1.6/exclusion-lists"
CREATE_PATH_IN_LIST_URL = (
    "web/api/v1.6/exclusion-lists/{0}/folders"  # {0} - Exclusion List ID.
)
RECONNECT_AGENT_NETWORK_URL = "web/api/v1.6/agents/{0}/connect"  # {0} - Agent ID.
DISCONNECT_AGENT_FROM_NETWORK_URL = (
    "web/api/v1.6/agents/{0}/disconnect"  # {0} - Agent ID.
)
FETCH_FILES_URL = "web/api/v1.6/agents/{0}/fetch-files"  # {0} - Agent ID.
GET_AGENT_INFORMATION_URL = "web/api/v1.6/agents/{0}"  # {0} - Agent ID.

# Parameters.
REQUEST_ON_AGENT_PARAMS = {"id__in": []}

GET_EVENTS_BY_DATE_PARAMS = {
    "query": "",
    "fromDate": "2017-11-06T19:11:00.000Z",
    "toDate": "2017-11-07T19:11:00.000Z",
    "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "limit": 10,
}

GET_THREATS_BY_ENDPOINT_PARAMS = {"agent_id": ""}

# Headers.
HEADERS = {"Authorization": "Token {0}", "Content-Type": "application/json"}

# Payloads.
LOGIN_PAYLOAD = {"username": "", "password": ""}

UPGRADE_SOFTWARE_PAYLOAD = {"use_recent": False, "os_type": "WINDOWS"}

CREATE_PATH_IN_LIST_PAYLOAD = {
    "folder_path": "C:/path/to/folder",
    "description": "Folder add by Siemplify through SentinelOne API",
    "os_family": "windows",
    "inject": True,
    "exclusion_type": "file",
    "list_id": "12839f02948fe20948de3ca4",
}

FETCH_FILES_PAYLOAD = {"files": [], "password": ""}


# Enums
OPERATION_SYSTEM_ENUM = {1: "osx", 2: "windows", 3: "android", 4: "linux"}


# =====================================
#              CLASSES                #
# =====================================
class SentinelOneManagerError(Exception):
    """
    Custom Error.
    """

    pass


class SentinelOneAgentNotFoundError(Exception):
    """
    Custom error for not finding agent issue.
    """

    pass


class SentinelOneManager:
    def __init__(self, api_root, username, password):
        """
        :param api_root: API root URL.
        :param username: SentinelOne Username
        :param password: SentinelOne Password
        """
        self.api_root = api_root

        self.session = requests.session()
        self.token = self.get_token(username, password)
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Authorization"] = self.session.headers[
            "Authorization"
        ].format(self.token)

    def get_token(self, username, password):
        """
        Fetches and returns the connection token.
        :return: Token {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, LOGIN_URL)

        payload = copy.deepcopy(LOGIN_PAYLOAD)
        payload["username"] = username
        payload["password"] = password

        response = self.session.post(request_url, json=payload)
        self.validate_response(response)

        # Extract token.
        token = response.json()["token"]
        return token

    # Inner functions.
    @staticmethod
    def validate_response(response):
        """
        Validate HTTP response and raise informative Exception.
        :param response: HTTP response object.
        :return: {void}
        """
        try:
            response.raise_for_status()
        except Exception as er:
            raise SentinelOneManagerError(f"Error:{er}, Content:{response.content}")

    @staticmethod
    def list_of_dicts_to_csv(list_of_dicts):
        """
        Gets a list of dictionaries and return a list of strings in CSV format.
        :param list_of_dicts: llst of dictionary objects.
        :return: list of strings in a CSV format {string}]
        """
        csv_result = []
        csv_row = []
        if list_of_dicts:
            headers_list = list(list_of_dicts[0].keys())
            headers_string = ",".join(headers_list).replace(".", " ")
            # Append headers row to result.
            csv_result.append(headers_string)
            for event_dict in list_of_dicts:
                for header in headers_list:
                    # Add value to row.
                    if header in event_dict:
                        csv_row.append(str(event_dict[header]).replace(",", " "))
                    else:
                        csv_row.append("None")
                # Appand new row to result.
                csv_result.append(",".join(csv_row))
                # Reset CSV row parameter.
                csv_row = []
        return csv_result

    def find_endpoint_agent_id(self, identifier, by_ip_address=False, get_uuid=False):
        """
        Returns agent ID by identifier(computer name/IP address) by running over all agents.
        :param identifier: endpoint identifier,can be host name or ip address {string}
        :param by_ip_address: get ID by IP address or by host {bool}
        :param get_uuid: if uuid is needed for certain requests {bool}
        :return: agent id/uuid {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_AGENTS_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        agents_data = response.json()

        # Run over agents data.
        for agent in agents_data:
            # Get agent id by host name.
            if not by_ip_address:
                if agent["network_information"]["computer_name"] == identifier:
                    # There are two types of requests when one takes uuid of the agent as an argument and the second Takes the id
                    if not get_uuid:
                        return agent["id"]
                    else:
                        return agent["uuid"]
            # Get agent id by ip address.
            else:
                for interface in agent["network_information"]["interfaces"]:
                    if interface["inet"][0] == identifier:
                        if not get_uuid:
                            return agent["id"]
                        else:
                            return agent["uuid"]

        # raise exception if agent not found.
        raise SentinelOneAgentNotFoundError(
            f"Not found agent id for endpoint: {identifier}"
        )

    def get_agent_operation_system(self, agent_id):
        """
        Get operation system name by agent id(host name or ip address)
        :param agent_id: endpoint agent id  {string}
        :return: operation system name {string}
        """

        request_url = urllib.parse.urljoin(
            self.api_root, GET_AGENT_INFORMATION_URL.format(agent_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        agent_data = response.json()
        # Fetch agent's operation system type.
        agent_os_type = agent_data["software_information"]["os_type"]
        # Convert type to OS name.
        os_name = OPERATION_SYSTEM_ENUM[agent_os_type]
        return os_name

    def get_exclusion_list_id_by_name(self, list_name):
        """
        :param list_name: exclusions list name {string}
        :return: list id {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_EXCLUSION_LISTS_URLS)
        response = self.session.get(request_url)
        self.validate_response(response)
        exclusion_lists_list = response.json()

        # Return ID.
        for exclusion_list in exclusion_lists_list:
            if exclusion_list["name"] == list_name:
                return exclusion_list["id"]
        # Return none if do not exist.
        return None

    # Main functions
    def get_system_status(self):
        """
        Returns current system health status.
        :return: system health status  {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SYSTEM_INFORMATION_URL)
        response = self.session.get(request_url)
        self.validate_response(response)

        return response.json()["health"]

    # CR: This action should return boolean.
    def get_agent_status(self, agent_id):
        """
        Get agent work status.
        :param agent_id: endpoint agent id {string}
        :return: {boolean} weather agent is alive or not
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_AGENT_INFORMATION_URL.format(agent_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        # Return agent status.
        return response.json()["is_active"]

    def get_system_version(self):
        """
        Returns current system version.
        :return: system version {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SYSTEM_VERSION_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()["version"]

    def restart_agents_machine(self, agent_id):
        """
        Restart endpoint machine by ip address or hostname.
        :param agent_id: endpoint agent id {string}
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, RESTART_MACHINE_URL)

        # Set Parameters.
        params = copy.deepcopy(REQUEST_ON_AGENT_PARAMS)
        params["id__in"].append(agent_id)

        response = self.session.post(request_url, params=params)
        self.validate_response(response)

        return True

    def upgrade_agents_software(self, agent_id):
        """
        Upgrade agent software by endpoint agent id.
        :param agent_id: endpoint agent id {string}
        :return: is success {bool}
        """
        # Get agent operation system.
        endpoint_operation_system = self.get_agent_operation_system(agent_id)

        request_url = urllib.parse.urljoin(self.api_root, UPDATE_AGENT_SOFTWARE_URL)

        # Set Parameters.
        params = copy.deepcopy(REQUEST_ON_AGENT_PARAMS)
        params["id__in"].append(agent_id)

        # Organize payload.
        payload = copy.deepcopy(UPGRADE_SOFTWARE_PAYLOAD)
        payload["os_type"] = endpoint_operation_system

        response = self.session.post(request_url, params=params, json=payload)
        self.validate_response(response)
        return True

    def initiate_agents_full_disk_scan(self, agent_id):
        """
        Initiate agent full disk scan.
        :param agent_id: endpoint agent id {string}
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, INITIATE_SCAN_URL)

        # Set Parameters.
        params = copy.deepcopy(REQUEST_ON_AGENT_PARAMS)
        params["id__in"].append(agent_id)

        response = self.session.post(request_url, params=params)
        self.validate_response(response)
        return True

    def get_agent_processes_list(self, agent_id, csv_output=False):
        """
        :param agent_id: endpoint agent id {string}
        :param csv_output: output returned as csv {bool}
        :return: list of dicts when each dict is a data about a process on the endpoint {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_AGENT_PROCESSES_LIST_URL.format(agent_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)

        if csv_output:
            return self.list_of_dicts_to_csv(response.json())
        return response.json()

    def get_events_for_endpoint_by_date(
        self, agent_uuid, from_date, to_date, limit=100, csv_output=False
    ):
        """
        get events for endpoint by date.
        :param agent_uuid: endpoint agent uuid {string}
        :param from_date: {datetime}
        :param to_date: {datetime}
        :param limit: events amount limit {integer}
        :param csv_output: output returned as csv {bool}
        :return: events for an endpoint {dict}
        """
        # Convert times to string.
        from_date_str = from_date.strftime(FETCH_EVENT_TIME_FORMAT)
        to_date_str = to_date.strftime(FETCH_EVENT_TIME_FORMAT)

        # Organize parameters.
        params = copy.deepcopy(GET_EVENTS_BY_DATE_PARAMS)
        params["fromDate"] = from_date_str
        params["toDate"] = to_date_str
        params["token"] = self.token
        params["limit"] = limit

        request_url = urllib.parse.urljoin(
            self.api_root, GET_EVENTS_FOR_ENDPOINT_URL.format(agent_uuid)
        )
        response = self.session.post(request_url, params=params)
        self.validate_response(response)

        if csv_output:
            return self.list_of_dicts_to_csv(response.json())
        return response.json()

    def get_hash_reputation(self, file_hash):
        """
        Get file hash reputation.
        :param file_hash: file hash {string}
        :return: file hash reputation data {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_HASH_REPUTATION_URL.format(file_hash)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_hash_data(self, file_hash):
        """
        Get file hash data.
        :param file_hash: file hash {string}
        :return: file hash data {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_HASH_DATA_URL.format(file_hash)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_endpoint_system_information(self, agent_id):
        """
        Get information about the endpoint's system.
        :param agent_id: endpoint agent id {string}
        :return: endpoint system information {dict}
        """

        request_url = urllib.parse.urljoin(
            self.api_root, GET_ENDPOINT_SYSTEM_INFO_URL.format(agent_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_server_settings(self):
        """
        Get system configuration server settings.
        :return: server setting information {dict}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SYSTEM_SETTINGS_INFO_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_threats_for_endpoint(self, agent_id, csv_output=False):
        """
        Get threats,suspicious activities for an endpoint.
        :param agent_id: endpoint agent id {string}
        :param csv_output: output returned as csv {bool}
        :return: endpoint system information {dict}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_THREATS_BY_ENDPOINT_URL)

        # Organize request parameters.
        params = copy.deepcopy(GET_THREATS_BY_ENDPOINT_PARAMS)
        params["agent_id"] = agent_id

        response = self.session.get(request_url, params=params)
        self.validate_response(response)

        if csv_output:
            return self.list_of_dicts_to_csv(response.json())
        return response.json()

    def get_reports_list(self):
        """
        Get list of reports data.
        :return: list of dicts when each dict is a report data {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_REPORTS_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_applications_from_endpoint(self, agent_id, csv_output=False):
        """
        Get list of applications for an endpoint.
        :param agent_id: endpoint agent id {string}
        :param csv_output: output returned as csv {bool}
        :return: endpoint system information {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_APPLICATIONS_URL.format(agent_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)

        if csv_output:
            return self.list_of_dicts_to_csv(response.json())
        return response.json()

    def create_path_in_exclusion_list(self, list_name, file_path, operation_system):
        """
        Create a new path in exclusion list.
        :param list_name: exclusion list name {string}
        :param file_path: path to add to the list {string}
        :param operation_system: operation system, can be: windows, osx, linux or android {string}
        :return: {void}
        """
        # Get list id.
        list_id = self.get_exclusion_list_id_by_name(list_name)

        if list_id:
            request_url = urllib.parse.urljoin(
                self.api_root, CREATE_PATH_IN_LIST_URL.format(list_id)
            )

            # Organize payload.
            payload = copy.deepcopy(CREATE_PATH_IN_LIST_PAYLOAD)
            payload["folder_path"] = file_path
            payload["list_id"] = list_id
            payload["os_family"] = operation_system

            response = self.session.post(request_url, json=payload)
            self.validate_response(response)
        else:
            raise SentinelOneManagerError(f"List with name:{list_name} does not exist.")

    def reconnect_agent_to_network(self, agent_id):
        """
        Reconnect endpoint to the network.
        :param agent_id: endpoint agent id {string}
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, RECONNECT_AGENT_NETWORK_URL.format(agent_id)
        )
        response = self.session.post(request_url)
        self.validate_response(response)
        return True

    def disconnect_agent_from_network(self, agent_id):
        """
        Disconnect endpoint from network.
        :param agent_id: endpoint agent id {string}
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, DISCONNECT_AGENT_FROM_NETWORK_URL.format(agent_id)
        )
        response = self.session.post(request_url)
        self.validate_response(response)
        return True

    # Still not complete for API problem reasons.
    def fetch_files_for_agent(self, agent_id, zip_password, files=[]):
        """
        Fetch files from endpoint machines and allows to download the files through the Siemplify client.
        :param agent_id: endpoint agent id {string}
        :param zip_password: a password for the zip archive with the fetch files {string}
        :param files: list of strings which are the file names to fetch {list}
        :return:
        """
        request_url = urllib.parse.urljoin(
            self.api_root, FETCH_FILES_URL.format(agent_id)
        )

        # Organize payload.
        payload = copy.deepcopy(FETCH_FILES_PAYLOAD)
        payload["files"] = files
        payload["password"] = zip_password

        response = self.session.post(request_url, json=payload)
        self.validate_response(response)


#
