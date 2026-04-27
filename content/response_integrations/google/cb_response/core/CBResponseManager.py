# ============================================================================#
# title           :CarbonBlackResponseManager.py
# description     :This Module contain all Carbon Black Response operations functionality
# author          :avital@siemplify.co
# date            :08-02-2018
# python_version  :2.7
# libreries       :requests, cbapi
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================ IMPORTS ====================================== #

from __future__ import annotations
import base64
import requests
import copy
import time
from .CBResponseParser import CBResponseParser
from io import StringIO
from zipfile import ZipFile


# List Types
BLACKLIST_STRING = "blacklist"
WHITELIST_STRING = "whitelist"
# Operators
EXACT_STRING = "exact"
STARTS_WITH_STRING = "start with"
ENDS_WITH_STRING = "ends with"
CONTAINS_STRING = "contains"
# =====================================
#             CONSTANTS               #
# =====================================
API_ENDPOINTS = {
    "binary_free_query": "{}/api/v1/binary",
    "process_filemod_list": "{}/api/v1/process/{}/{}/event",
    "process_tree_data": "{}/api/v1/process/{}/{}",
    "process_free_query": "{}/api/v1/process",
    "segment_id_by_process_id": "{}/api/v1/process?q=process_id:{}",
    "create_alert_for_watchlist": "{}/api/v1/watchlist/{}/action",
    "sensor_by_parameter": "{}/api/v1/sensor?{}={}",
    "sensor_by_id": "{}/api/v1/sensor/{}",
    "download_binary_by_md5": "{}/api/v1/binary/{}",
    "banning_blacklist": "{}/api/v1/banning/blacklist",
    "banning_blacklist_md5": "{}/api/v1/banning/blacklist/{}",
    "process_by_process_name": "{}/api/v1/process?q=process_name:{}&rows=100",
    "license": "{}/api/v1/license",
    "get_binary_summary": "{}/api/v1/binary/{}/summary",
    "get_alert": "{}/api/v2/alert",
    "update_alert": "{}/api/v1/alert/{}",
    "watchlist": "{}/api/v1/watchlist",
    "lr_session": "{}/api/v1/cblr/session",
    "lr_session_id": "{}/api/v1/cblr/session/{}",
    "lr_session_command": "{}/api/v1/cblr/session/{}/command",
    "lr_session_command_id": "{}/api/v1/cblr/session/{}/command/{}",
}

BANNED_HASH_TEXT = "Banned by Siemplify"
UNBAN_HASH_TEXT = "Unbanned by Siemplify"
RESULTS_PER_PAGE = 100
LR_ACTIVE_STATUS = "active"
LR_COMPLETE_STATUS = "complete"
GLOBAL_API_LIMIT = 300
# Payloads
HEADERS = {"X-Auth-Token": ""}

# statuses
ALERT_STATUS_RESOLVED = "Resolved"
CA_CERTIFICATE_FILE_PATH = "cacert.pem"


# ============================== CLASSES ==================================== #
class CBResponseManagerException(Exception):
    pass


class CBResponseManager:

    def __init__(
        self, api_root, api_key, logger, verify_ssl=False, ca_certificate_file=None
    ):
        self.api_root = api_root
        self.session = requests.session()
        self.set_session_verify(verify_ssl, ca_certificate_file)
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["X-Auth-Token"] = api_key
        self.parser = CBResponseParser()
        self.logger = logger

    def set_session_verify(self, verify_ssl, ca_certificate_file):
        if verify_ssl and ca_certificate_file is not None:
            self.session.verify = self._save_certificate_file(ca_certificate_file)
        else:
            self.session.verify = verify_ssl

    @staticmethod
    def _save_certificate_file(ca_certificate_file):
        try:
            file_content = base64.b64decode(ca_certificate_file).decode()
            with open(CA_CERTIFICATE_FILE_PATH, "w") as f:
                f.write(file_content)
            return CA_CERTIFICATE_FILE_PATH
        except Exception as e:
            raise CBResponseManagerException(f"Certificate Error: {e}")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise CBResponseManagerException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise CBResponseManagerException(
                f"{error_msg}: {response.json().get('name')} {response.json().get('message')}"
            )

        return True

    def get_sensor_by(self, identifier, identifier_type):
        """
        Get sensor data identifier
        :param identifier: {str} The identifier
        :param identifier_type: {str} The identifier type. [ip, hostname]
        :return: {SensorDocument} Sensor document data
        """
        url = API_ENDPOINTS["sensor_by_parameter"].format(
            self.api_root, identifier_type, identifier
        )
        response = self.session.request("GET", url)
        self.validate_response(response)
        response_json = response.json()
        if response_json and response_json[0]:
            return self.parser.build_siemplify_sensor_document_obj(response_json[0])

    def get_sensor_by_ip(self, ip_address):
        """
        Get sensor data by ip address
        :param ip_address: {str} The ip address
        :return: {SensorDocument} Sensor document data
        """
        return self.get_sensor_by(ip_address, "ip")

    def get_sensor_by_hostname(self, hostname):
        """
        Get sensor data by hostname
        :param hostname: {str} The hostname
        :return: {SensorDocument} Sensor document data
        """
        return self.get_sensor_by(hostname, "hostname")

    def get_processes(self, sensor_id):
        """
        Get processes of a sensor by given id
        :param sensor_id: {str} The sensor id
        :return: {list} List of the processes' data
        """
        url = API_ENDPOINTS["process_free_query"].format(self.api_root)

        processes_json = self._paginate_results(
            "GET", url, params={"sensor_id": sensor_id}
        )

        return [
            self.parser.build_siemplify_process_obj(process_json)
            for process_json in processes_json
        ]

    def get_process_by_name(self, process_name):
        """
        Get process data by process name
        :param process_name: {str} The process name
        :return: {list} The data of the found processes
        """
        url = API_ENDPOINTS["process_free_query"].format(self.api_root)

        processes_json = self._paginate_results("GET", url, params={"q": process_name})

        return [
            self.parser.build_siemplify_process_obj(process_json)
            for process_json in processes_json
        ]

    def host_isolation(self, sensor_id, isolate):
        """
        Isolate / unisolate a host by sensor id
        :param sensor_id:  {str} The sensor id
        :param isolate: {bool} True to isolate False to unisolate
        :return: {bool} True if successful
        """
        url = API_ENDPOINTS["sensor_by_id"].format(self.api_root, sensor_id)
        data = {}
        data["network_isolation_enabled"] = isolate
        response = self.session.request("PUT", url, json=data)
        self.validate_response(response)
        return True

    def isolate_host(self, sensor_id):
        """
        Isolate a sensor
        :param sensor_id: {str} The sensor id
        :return: {bool} True if successful
        """
        return self.host_isolation(sensor_id, True)

    def unisolate_host(self, sensor_id):
        """
        Unisolate a sensor
        :param sensor_id: {str} The sensor id
        :return: {bool} True if successful
        """
        return self.host_isolation(sensor_id, False)

    def download_binary(self, md5):
        """
        Download a binary by md5
        :param md5: {str} The md5
        :return: {str} The content of the downloaded file
        """
        url = API_ENDPOINTS["download_binary_by_md5"].format(self.api_root, md5)
        response = self.session.request("GET", url)
        self.validate_response(response)

        # response content is a zip file data
        # creating StringIO object and passing object to ZipFile to imitate file reading process
        z = StringIO(response.content)
        zf = ZipFile(z)
        fp = zf.open("filedata")
        return fp.read()

    def ban_hash(self, md5):
        """
        Ban a file by md5
        :param md5: {Str} The md5
        """
        url = API_ENDPOINTS["banning_blacklist"].format(self.api_root)
        data = {}
        data["md5hash"] = md5
        data["enabled"] = True
        data["text"] = BANNED_HASH_TEXT
        response = self.session.request("POST", url, json=data)
        self.validate_response(response)

    def unban_hash(self, md5):
        """
        Unban a file by md5
        :param md5: {Str} The md5
        """
        url = API_ENDPOINTS["banning_blacklist_md5"].format(self.api_root, md5)
        data = {}
        data["enabled"] = False
        data["text"] = UNBAN_HASH_TEXT
        response = self.session.request("DELETE", url, json=data)
        self.validate_response(response)

    def get_sensors_by_process(self, process_name):
        """
        Get sensors by process
        :param process_name: {Str} The process name
        :return: {list} The sensors data
        """
        url = API_ENDPOINTS["process_by_process_name"].format(
            self.api_root, process_name
        )
        response = self.session.request("GET", url)
        self.validate_response(response)
        processes = [process_json for process_json in response.json()["results"]]

        sensor_ids = set()
        for p in processes:
            sensor_id = p.get("sensor_id")
            if sensor_id:
                sensor_ids.add(sensor_id)

        sensors = []
        for sensor_id in sensor_ids:
            try:
                sensor_obj = self._get_sensor_by_id(sensor_id)
                sensors.append(sensor_obj)
            except Exception as e:
                self.logger.error(f"Unable to get a sensor object, {e}")
                self.logger.exception(e)

        return sensors

    def _get_sensor_by_id(self, sensor_id):
        """
        Getting sensor object with sensor ID
        :param sensor_id: The sensor ID
        :return: sensor object if successful or throws exception if error
        """
        url = API_ENDPOINTS["sensor_by_id"].format(self.api_root, sensor_id)
        response = self.session.request("GET", url)
        self.validate_response(response)
        return self.parser.build_siemplify_sensor_document_obj(response.json())

    def get_license(self):
        """
        Get the license from CB Response
        :return: {str} The license
        """
        url = API_ENDPOINTS["license"].format(self.api_root)
        response = self.session.request("GET", url)
        self.validate_response(response)
        return response.json().get("license_request_block")

    def get_binary(self, md5):
        """
        Get binary info by md5
        :param md5: {str} The md5
        :return: {Binary} Binary info
        """
        url = API_ENDPOINTS["get_binary_summary"].format(self.api_root, md5)
        response = self.session.request("GET", url)
        self.validate_response(response)
        return self.parser.build_siemplify_binary_obj(response.json())

    def process_free_query(self, query):
        """
        Run free query on processes
        :param query: {str} The query
        :return: {JSON} The info of processes that matched the query
        """
        url = API_ENDPOINTS["process_free_query"].format(self.api_root)

        processes_json = self._paginate_results("GET", url, params={"q": query})

        return [
            self.parser.build_siemplify_process_obj(process_json)
            for process_json in processes_json
        ]

    def binary_free_query(self, query):
        """
        Run free query on binaries
        :param query: {str} The query
        :return: {JSON} The info of binaries that matched the query
        """
        url = API_ENDPOINTS["binary_free_query"].format(self.api_root)

        params = {"q": query}

        binaries_json = self._paginate_results("GET", url, params=params)

        return [
            self.parser.build_siemplify_binary_obj(binary_json)
            for binary_json in binaries_json
        ]

    def _paginate_results(
        self, method, url, params=None, body=None, err_msg="Unable to get results"
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if body is None:
            body = {}

        params.update({"start": 0, "rows": RESULTS_PER_PAGE})

        response = self.session.request(method, url, params=params, json=body)

        self.validate_response(response, err_msg)
        results = response.json().get("results", [])
        total_results = response.json().get("total_results", 0)

        while True:
            if len(results) >= min(total_results, GLOBAL_API_LIMIT):
                break

            body.update({"start": len(results)})

            response = self.session.request(method, url, params=params, json=body)

            self.validate_response(response, err_msg)
            results.extend(response.json().get("results", []))

        return results

    def get_alerts(self, query):
        """
        Get all alerts from CB Response
        :param query: {str} The query to filter te alerts by
        :return: {list} List of the alerts info (Alert)
        """
        url = API_ENDPOINTS["get_alert"].format(self.api_root)
        params = {"q": query}
        alerts = self._paginate_results("GET", url, params=params)
        return [
            self.parser.build_siemplify_alert_obj(alert_json) for alert_json in alerts
        ]

    def clear_alert_fields(self, alert, list_type, list_operator, list_fields):
        """
        Clear alert from blacklisted values or leave the whitelisted.
        :param alert: {Alert} an alert to filter.
        :param list_type: {string} has to be one of those: 'blacklist' or 'whitelist'.
        :param list_operator: {string} has to be one of those: 'exact', 'start with', 'ends with' or 'contains'.
        :param list_fields: {list} fields to compare with.
        :return: {Alert} filtered alert.
        """
        result_alert = copy.deepcopy(alert.raw_data)
        for key in alert.raw_data:
            matched_flag = False
            if key:
                if list_operator == EXACT_STRING:
                    if (key in list_fields and list_type == BLACKLIST_STRING) or (
                        key not in list_fields and list_type == WHITELIST_STRING
                    ):
                        result_alert.pop(key)
                else:
                    for field in list_fields:
                        if (
                            (list_operator == CONTAINS_STRING and field in key)
                            or (
                                list_operator == STARTS_WITH_STRING
                                and key.startswith(field)
                            )
                            or (
                                list_operator == ENDS_WITH_STRING
                                and key.endswith(field)
                            )
                        ):
                            matched_flag = True
                            break

                    if (
                        matched_flag
                        and list_type == BLACKLIST_STRING
                        or not matched_flag
                        and list_type == WHITELIST_STRING
                    ):
                        result_alert.pop(key)

        return self.parser.build_siemplify_alert_obj(result_alert)

    def resolve_alert(self, alert_id):
        """
        Resolve an alert
        :param alert_id: {str} The id of the alert to resolve
        :return: {bool} True if successful
        """
        url = API_ENDPOINTS["update_alert"].format(self.api_root, alert_id)
        data = {}
        data["unique_id"] = alert_id
        data["status"] = ALERT_STATUS_RESOLVED
        response = self.session.request("POST", url, json=data)
        self.validate_response(response)
        return True

    def create_watchlist(self, name, search_query, watchlist_type="events"):
        """
        Create a new watchlist.
        :param name: {str} Name of this watchlist
        :param search_query: {str} The raw Carbon Black query that this watchlist matches
        :param watchlist_type: {str} The type of watchlist. Valid values are "modules"
            and "events" for binary and process watchlists, respectively.
        :return: {bool} True if successful, exception otherwise.
        """
        if search_query[:2] != "q=":
            search_query = "q=" + search_query
        url = API_ENDPOINTS["watchlist"].format(self.api_root)
        data = {}
        data["search_query"] = search_query
        data["index_type"] = watchlist_type
        data["name"] = name
        response = self.session.request("POST", url, json=data)
        self.validate_response(response)
        return self.create_alert_action_for_watchlist(response.json().get("id"))

    def kill_process(self, sensor_id, process_name):
        """
        Kill a process on a sensor using Live Response
        :param sensor_id: {int} The sensor id
        :param process_name: {str} The name of the process ro kill
        :return: {bool} True if successful, exception otherwise
        """
        live_response_session_id = self._get_or_create_lr_session(sensor_id)

        command_to_run = {}
        command_to_run["session_id"] = live_response_session_id
        command_to_run["name"] = "process list"
        response_json = self._run_lr_command(live_response_session_id, command_to_run)

        processes = response_json.get("processes", [])
        pids_to_kill = []
        for process in processes:
            if process_name.lower() in process.get("path", "").lower():
                pids_to_kill.append(process.get("pid"))

        for pid_to_kill in pids_to_kill:
            command_to_run = {}
            command_to_run["session_id"] = live_response_session_id
            command_to_run["name"] = "kill"
            command_to_run["object"] = pid_to_kill
            try:
                self._run_lr_command(live_response_session_id, command_to_run)
            except Exception as e:
                self.logger.error(f"Couldn't kill the process {process_name}")
                self.logger.exception(e)
        self._close_lr_session(live_response_session_id)
        return True

    def get_process_with_tree(self, process_id, segment_id):
        """
        Get process with tree -> Process data with parent, siblings and children.
        :param process_id: process unique id {string}
        :param segment_id: segment  unique id {string}
        :return: process  {process}
        """
        url = API_ENDPOINTS["process_tree_data"].format(
            self.api_root, process_id, segment_id
        )
        response = self.session.get(url)
        self.validate_response(response)
        return self.parser.build_siemplify_process_with_tree_data(response.json())

    def get_process_filemod_list(self, process_id, segment_id):
        """
        Get process summery -> Process data, siblings and children.
        :param process_id: process unique id {string}
        :param segment_id: segment unique id {string}
        :return: process  {ElapsedProcess}
        """
        url = API_ENDPOINTS["process_filemod_list"].format(
            self.api_root, process_id, segment_id
        )
        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_elapsed_process(response.json())

    def get_segment_id_by_process_id(self, process_id):
        """
        Get segment id of specific process
        :param process_id: {string}
        :return: {string} The segment id
        """
        url = API_ENDPOINTS["segment_id_by_process_id"].format(
            self.api_root, process_id
        )
        response = self.session.get(url)
        self.validate_response(response)
        processes = [
            self.parser.build_siemplify_process_obj(process_json)
            for process_json in response.json()["results"]
        ]
        if processes:
            return processes[0].segment_id
        raise CBResponseManagerException("Error Fetching segment id for process.")

    def create_alert_action_for_watchlist(self, watchlist_id):
        """
        Create an alert action for watchlist
        :param watchlist_id: {int} watchlist ID
        :return:
        """
        url = API_ENDPOINTS["create_alert_for_watchlist"].format(
            self.api_root, watchlist_id
        )
        body = {"action_type": 3, "watchlist_id": watchlist_id}  # 3 for alert action
        response = self.session.request("POST", url, json=body)
        return self.validate_response(response)

    def _get_or_create_lr_session(self, sensor_id):
        """
        Create Live Response Session
        :param sensor_id: the sensor ID
        :return: Live response session ID
        """
        # check if live response already exists
        url = API_ENDPOINTS["lr_session"].format(self.api_root)
        response = self.session.request("GET", url)
        self.validate_response(response, "couldn't get live responses")
        live_response_session_id = None
        for cblr in response.json():
            if (
                cblr.get("sensor_id") == sensor_id
                and cblr.get("status") == LR_ACTIVE_STATUS
            ):
                live_response_session_id = cblr.get("id")
                break

        if live_response_session_id is None:
            live_response_session_id = self._create_lr_session(sensor_id)
        return self._wait_for_session(live_response_session_id)

    def _create_lr_session(self, sensor_id):
        """
        Create Live Response Session for a given sensor_id
        :param sensor_id: The Senosr ID
        :return: Live Response session id or throws exception
        """
        url = API_ENDPOINTS["lr_session"].format(self.api_root)
        data = {}
        data["sensor_id"] = sensor_id
        response = self.session.request("POST", url, json=data)
        self.validate_response(
            response, error_msg="couldn't create live response session"
        )
        return response.json().get("id")

    def _wait_for_session(self, live_response_session_id):
        """
        Waits for LRsession to become active
        after creating session, the session status is 'pending'
        The method waits until status becomes 'active' and returns the lr_session ID
        :param live_response_session_id: The Live Response ID
        :return: lr_session_id or throws exception
        """
        url = API_ENDPOINTS["lr_session_id"].format(
            self.api_root, live_response_session_id
        )
        response = self.session.request("GET", url)
        self.validate_response(response, error_msg="couldn't get session via id")
        # waiting until Live Response session activates
        while response.json().get("status", "pending") != LR_ACTIVE_STATUS:
            time.sleep(1)
            response = self.session.request("GET", url)
            self.validate_response(response, error_msg="couldn't get session via id")
        return live_response_session_id

    def _close_lr_session(self, live_response_session_id):
        """
        close the Live Response
        :param live_response_session_id: Live Response Session id
        :return: True if successful, else throws exception
        """
        url = API_ENDPOINTS["lr_session_id"].format(
            self.api_root, live_response_session_id
        )
        data = {}
        data["status"] = "close"
        response = self.session.request("PUT", url, json=data)
        return self.validate_response(response, "Couldn't close the lr session")

    def _run_lr_command(self, live_response_session_id, command_dict):
        """
        Runs command in Live Response
        :param live_response_session_id: Live response session id
        :param command_dict: command dict to run in a session
        :return: run result in json format
        """
        url = API_ENDPOINTS["lr_session_command"].format(
            self.api_root, live_response_session_id
        )
        response = self.session.request("POST", url, json=command_dict)

        self.validate_response(
            response, error_msg=f"couldn't run {command_dict} command"
        )

        command_id = response.json().get("id")
        return self._get_lr_command_result(live_response_session_id, command_id)

    def _get_lr_command_result(self, live_response_session_id, command_id):
        """
        gets result of run command via run command id
        :param live_response_session_id: The Live Response Session ID
        :param command_id: The Command ID
        :return:
        """
        url = API_ENDPOINTS["lr_session_command_id"].format(
            self.api_root, live_response_session_id, command_id
        )
        response = self.session.request("GET", url)

        self.validate_response(
            response,
            error_msg=f"couldn't get result for command, command_id {command_id}",
        )
        return response.json()
