# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ==============================================================================
# title           :EndgameManager.py
# description     :This Module contain all Endgame functionality
# author          :zivh@siemplify.co
# date            :1-6-19
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .EndgameTransformationLayer import EndgameTransformationLayer


# =====================================
#               CONFIG                #
# =====================================

SLEEP_TIME = 5
DEFAULT_PAGE_SIZE = 50

# =====================================
#               CONSTS                #
# =====================================
BASE_URL = "{0}/api/v1"

# Headers
HEADERS = {"Content-Type": "application/json", "Authorization": "JWT {0}"}

IOC_FILE_SEARCH = "file_search"
IOC_PROCESS_SEARCH = "process_search"
IOC_USER_SEARCH = "username_search"
IOC_REGISTRY_SEARCH = "registry_search"
IOC_ADDRESS_SEARCH = "network_search"

ALERT_MAPPING = {
    "contextManipulation": "Thread Context Manipulation",
    "controlFlowIntegrity": "Hardware Assisted (HA-CFI)",
    "creation": "Creation",
    "credentialTheftEventResponse": "Memory Access",
    "criticalApiFiltering": "Critical API",
    "deletion": "Deletion",
    "demand": "Scan",
    "dll": "DLL Injection",
    "execution": "Execution",
    "overwrite": "Overwrite",
    "exploitMitigationEventResponse": "Exploit",
    "fileClassificationEventResponse": "Malicious File",
    "fileBlacklistEventResponse": "Blacklisted File",
    "filePath": "File Path",
    "headerProtection": "Header Protection",
    "heapMemory": "Heap Memory",
    "keyAdded": "Key Added",
    "keyChanged": "Key Changed",
    "keyRemoved": "Key Removed",
    "macro": "Malicious Macro",
    "modification": "Modification",
    "modified": "Modified",
    "open": "Open",
    "peHeaderManipulation": "Process Memory Manipulation",
    "processDoppelganging": "Process Doppelganging",
    "ransomwareProtectionEventResponse": "Ransomware",
    "rename": "Rename",
    "registryMonitorEventResponse": "Registry Modification",
    "returnHeap": "Return Heap",
    "ropChain": "ROP Chain",
    "shellcode": "Shellcode Injection",
    "shellcodeThreads": "Shellcode Threads",
    "stackMemory": "Stack Memory",
    "stackPivot": "Stack Pivot",
    "tokenManipulationProtectionEventResponse": "Token Manipulation via DKOM",
    "tokenProtectionEventResponse": "Privileged Token Theft",
    "uncPath": "UNC Path",
    "unknown": "Unknown",
}

# Hunts that are available it does a mapping to know what the scope should be in the request the API.
COLLECTION_SCOPE = {
    "userSessionsSearchRequest": "user_sessions",  # IOC Search - User
    "userSessionsSurveyRequest": "user_sessions",  # Users
    "softwareSurveyRequest": "software",  # Applications
    "firewallSurveyRequest": "firewall_rules",  # Filewall Rules
    "registrySearchRequest": "values",  # IOC Search - Registry
    # "registryQueryRequest": "" #Registry - Requires Path
    "systemNetworkSearchRequest": "connections",  # IOC Search - Network
    "systemNetworkSurveyRequest": "connections",  # Network
    "processSearchRequest": "processes",  # IOC Search - Process
    "processSurveyRequest": "processes",
    # "dirwalkRequest": "test", #File System requires path
    "fileSearchRequest": "file_list",  # IOC Search - File
    "collectAutoRunsRequest": "autoruns_locations",  # Persistence
    "removableMediaSurveyRequest": "removable_media",  # Removable Media
    "kernelModulesSurveyRequest": "kernel_modules",  # Loaded Drivers
}

COLLECTION_MAPPING = {
    "userSessionsSearchRequest": "IoC Search - User",
    "userSessionsSurveyRequest": "Users",  # Users
    "softwareSurveyRequest": "Applications",  # Applications
    "firewallSurveyRequest": "Filewall Rules",  # Filewall Rules
    "registrySearchRequest": "IoC Search - Registry",  # IOC Search - Registry
    # "registryQueryRequest": "Registry - Requires Path" #Registry - Requires Path
    "systemNetworkSearchRequest": "IoC Search - Network",  # IOC Search - Network
    "systemNetworkSurveyRequest": "Network",  # Network
    "processSearchRequest": "IoC Search - Process",  # IOC Search - Process
    "processSurveyRequest": "processes",
    # "dirwalkRequest": "File System requires path", #File System requires path
    "fileSearchRequest": "IoC Search - File",  # IOC Search - File
    "collectAutoRunsRequest": "Persistence",  # Persistence
    "removableMediaSurveyRequest": "Removable Media",  # Removable Media
    "kernelModulesSurveyRequest": "Loaded Drivers",  # Loaded Drivers
}

# Available tasks that require an emtpy JSON
WINDOWS_TASK_LIST = {
    "firewallSurveyRequest",
    "kernelModulesSurveyRequest",
    "removableMediaSurveyRequest",
    "softwareSurveyRequest",
    "shutdownRequest",
    "systemSurveyRequest",
    "userSessionsSurveyRequest",
}

UNSUPPORTED_TASK_LIST = {
    "alertDiagnostics",
    "bootRecordSurvey",
    "bundledTasks",
    "cancelTasks",
    "cpuInfoSurvey",
    "deleteRootCertificate",
    "dirwalk",
    "heartbeat",
    "listTasks",
    "loadDriver",
    "loadPlugin",
    "logMessage",
    "memorySurvey",
    "registryDelete",
    "rootCertificatesSurvey",
    "suspendThread",
    "tcpConnectScan",
    "timedDelay",
}

ISOLATION_REQUESTED = "isolation_requested"
RELEASE_REQUESTED = "release_requested"


# =====================================
#              CLASSES                #
# =====================================


class EndgameError(Exception):
    """
    General Exception for Endgame manager
    """

    pass


class EndgameNotFoundError(Exception):
    """
    Not Founr Exception for Endgame manager
    """

    pass


class EndgameManager:
    """
    Responsible for all Endgame operations functionality
    """

    def __init__(self, api_root, username=None, password=None, use_ssl=False):
        """
        Connect to a Endgame instance
        """
        self.session = requests.session()
        self.api_root = BASE_URL.format(api_root)
        self.session.verify = use_ssl
        self.token = self.login(username, password)
        self.session.headers = HEADERS
        self.session.headers["Authorization"] = self.session.headers[
            "Authorization"
        ].format(self.token)
        self.transformation_layer = EndgameTransformationLayer()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {unicode} Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except Exception:
                raise EndgameError(f"{error_msg}: {error} {response.content}")

            raise EndgameError(
                f"{error_msg}: {error} {response.json().get('message') or response.content}"
            )

    def login(self, username, password):
        """
        Logs into the SMP server - provides session management and access tokens for use with the rest of the SMP APIs.
        :param username: {string} username
        :param password: {string} password
        :return: {string} token - expires after 8 Hours
        """
        payload = {"username": username, "password": password}
        results = self.session.post(f"{self.api_root}/auth/login", json=payload)
        self.validate_response(results)

        return results.json().get("metadata", {}).get("token")

    def logout(self):
        """
        Logs out of the SMP Server
        :return: {string} status
        """
        results = self.session.get(f"{self.api_root}/auth/logout")
        self.validate_response(results)
        return results.json().get("data", {}).get("status")

    def get_license_status(self):
        """
        Retrieve SMP's license status
        :return: {dict} SMP license status
        """
        results = self.session.get(f"{self.api_root}/license/status")
        self.validate_response(results)
        return results.json()

    def get_version(self):
        """
        get Current SMP Version
        :return: {string} SMP version (e.g. "2.5.4-39")
        """
        results = self.session.get(f"{self.api_root}/version")
        self.validate_response(results)
        return results.json().get("version")

    def create_token(self, username):
        """
        Create an API token
        :param username: {string} Name to attach to the created token
        :return: {string} token
        """
        # Used to get long lasting Token
        results = self.session.post(
            f"{self.api_root}/users/api-token", json={"name": username}
        )
        self.validate_response(results)
        return results.json().get("data", {}).get("api_token")

    def list_users(self):
        """
        list users
        :return: {dict} users info
        """
        results = self.session.get(f"{self.api_root}/users")
        self.validate_response(results)
        return results.json().get("data", [])

    def get_userid(self, username):
        """
        get userID by username
        :param username: {string} username
        :return: {string} userID if found
        """
        users = self.list_users()
        for result in users:
            if result.get("username", "").lower() == username.lower():
                return str(result["id"])

    def get_endpoints(
        self,
        transaction_id=None,
        display_operating_system=None,
        name=None,
        ip_address=None,
        core_os=None,
        status=None,
        order_by=None,
        limit=None,
    ):
        """
        Get endpoints
        :param transaction_id: {str} Uuid of transaction to get endpoints
        :param display_operating_system: {str} Name of installed operating system
        :param name: {str} Name of endpoint
        :param ip_address: {str} IPv4 address of machine that the endpoint is installed on (contains, not exact)
        :param core_os: {str} Core operating system (linux | windows)
        :param status: {str} Monitoring status of the endpoint
        :param order_by: {str} Order the endpoint list by a particular field
        :param limit: {int} Max amount of results to fetch
        :return: {list} The found endpoints
        """
        payload = {
            "transaction_id": transaction_id,
            "display_operating_system": display_operating_system,
            "name": name,
            "ip_address": ip_address,
            "core_os": core_os,
            "status": status,
            "order_by": order_by,
        }
        # remove none items
        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        endpoints = self._paginate_results(
            method="GET",
            url=f"{self.api_root}/endpoints",
            params=url_params,
            limit=limit,
            err_msg="Unable to get endpoints",
        )
        return [
            self.transformation_layer.build_siemplify_endpoint_obj(endpoint)
            for endpoint in endpoints
        ]

    def get_endpoint_by_ip(self, ip_address):
        endpoints = self.get_endpoints(ip_address=ip_address)
        matching_endpoints = []

        for endpoint in endpoints:
            if endpoint.ip_address == ip_address:
                matching_endpoints.append(endpoint)

        if not matching_endpoints:
            raise EndgameNotFoundError(f"Endpoint with ip {ip_address} was not found")

        return matching_endpoints

    def get_endpoint_by_hostname(self, hostname):
        """
        Get an endpoint by hostname
        :param hostname: {unicode} The hostname of the endpoint to fetch
        :return: {[Endpoint]} The matching endpoints
        """
        endpoints = self._paginate_results(
            "GET", f"{self.api_root}/endpoints", err_msg="Unable to get endpoints"
        )
        endpoints = [
            self.transformation_layer.build_siemplify_endpoint_obj(endpoint)
            for endpoint in endpoints
        ]
        matching_endpoints = []

        for endpoint in endpoints:
            if endpoint.hostname == hostname:
                matching_endpoints.append(endpoint)

        if not matching_endpoints:
            raise EndgameNotFoundError(
                f"Endpoint with hostname {hostname} was not found"
            )

        return matching_endpoints

    def get_endpoint_by_id(self, endpoint_id):
        """
        Get an endpoint by ID
        :param endpoint_id: {unicode} The ID of the endpoint
        :return: {Endpoint} The found endpoint
        """
        response = self.session.get(url=f"{self.api_root}/endpoints/{endpoint_id}")
        self.validate_response(response, f"Endpoint {endpoint_id} was not found")
        return self.transformation_layer.build_siemplify_endpoint_obj(
            response.json()["data"]
        )

    def get_investigations(self, os_filters=None, created_from=None, limit=None):
        investigations = self._paginate_results(
            method="GET",
            url=f"{self.api_root}/investigations",
            err_msg="Unable to get investigations",
        )

        filtered_investigations = []
        if os_filters:
            for os_filter in os_filters:
                filtered_investigations.extend(
                    [
                        investigation
                        for investigation in investigations
                        if investigation.get("core_os", "").lower() == os_filter.lower()
                    ]
                )

        if created_from:
            filtered_investigations = [
                investigation
                for investigation in filtered_investigations
                if investigation.get("created_at")
                and convert_string_to_unix_time(investigation.get("created_at"))
                > created_from
            ]

        filtered_investigations = [
            self.transformation_layer.build_siemplify_investigation_obj(investigation)
            for investigation in filtered_investigations
        ]
        return filtered_investigations[:limit] if limit else filtered_investigations

    def get_investigation(self, investigation_id):
        """
        Get an investigation
        :param investigation_id: {unicode} investigation ID
        :return: {Investigation} The found investigation
        """
        results = self.session.get(f"{self.api_root}/investigations/{investigation_id}")
        self.validate_response(results)
        return self.transformation_layer.build_siemplify_investigation_obj(
            results.json().get("data")
        )

    def get_host_isolation_config(self):
        """
        Get host isolation config
        :return: {HostIsolationConfig} The found isolation config
        """
        host_isolation_config = self._paginate_results(
            method="GET",
            url=f"{self.api_root}/host-isolation-whitelist/ipv4",
            err_msg="Failed to get host isolation config",
        )
        return self.transformation_layer.build_siemplify_host_isolation_config_obj(
            host_isolation_config
        )

    def add_ip_subnet_to_isolation_config(self, subnet, comment):
        """
        Add a subnet to the isolation config
        :param subnet: {unicode} The subnet to add
        :param comment: {unicode} Comment to the subnet isolation
        :return: {bool} True if successful, exception otherwise
        """
        current_config = self.get_host_isolation_config()

        for rule in current_config.isolation_rules:
            if rule.addr == subnet:
                # Subnet already in the config - nothing to do
                return True

        url = f"{self.api_root}/host-isolation-whitelist/ipv4/{subnet}"
        response = self.session.put(url, json={"comment": comment if comment else ""})
        self.validate_response(
            response, f"Failed to add subnet {subnet} to the isolation config"
        )
        return True

    def remove_ip_subnet_from_isolation_config(self, subnet):
        """
        Remove a subnet from the isolation config
        :param subnet: {unicode} The subnet to remove
        :return: {bool} True if successful, exception otherwise
        """
        current_config = self.get_host_isolation_config()

        for rule in current_config.isolation_rules:
            if rule.addr == subnet:
                # Found the subnet - remove it
                url = f"{self.api_root}/host-isolation-whitelist/ipv4/{subnet}"
                response = self.session.delete(url)
                self.validate_response(
                    response,
                    f"Failed to remove subnet {subnet} from the isolation config",
                )
        else:
            # Didnt find the subnet in the current config rules - nothing to delete
            pass

        return True

    def get_task_descriptions(self):
        """
        Get all the task descriptions
        :return: {[]} List of all the tasks' descriptions
        """
        url = f"{self.api_root}/task-descriptions"
        response = self.session.get(url)
        self.validate_response(response, "Unable to get task descriptions")
        return response.json().get("data", [])

    def get_task_id(self, task_name, core_os=None):
        """
        Get the ID of a task
        :param task_name: {unicode} The name of the task
        :param core_os: {unicode} The sensor type (os) of the task
        :return: {unicode} The ID of the task
        """
        task_descriptions = self.get_task_descriptions()

        for task_description in task_descriptions:
            if task_description.get("name") == task_name:
                if core_os:
                    if (
                        task_description.get("sensor_type", "").lower()
                        == core_os.lower()
                    ):
                        return task_description.get("id")
                else:
                    return task_description.get("id")

        raise EndgameNotFoundError(f"Task {task_name} was not found")

    def retrieve_collection(self, collection_id, scope=None, limit=None):
        """
        Retrieve a Collection of events
        :param collection_id: {string} UUID of the collection
        :param scope: {string} user_sessions, firewall_rules, etc.
        :return: {dict} collection of events
        """
        return self._paginate_task_results(
            method="GET",
            url=f"{self.api_root}/collections/{collection_id}",
            params={"scope": scope},
            limit=limit,
        )

    def get_task(self, task_id):
        """
        Provides details on individual tasks
        :param task_id: {string} UUID of the task
        :return: {dict} task info
        """
        results = self.session.get(f"{self.api_root}/tasks/{task_id}")
        self.validate_response(results)
        return results.json().get("data", {}).get("tasks")

    def retrieve_investigation_results(self, investigation_id, scope=None, limit=None):
        """
        Get Investigation results
        :param investigation_id: {string} investigation ID
        :return: {dict} Investigation results
        """
        results_json = {}
        investigation = self.get_investigation(investigation_id)
        tasks = investigation.raw_data["tasks"]

        collection_scope = None

        for task_id in tasks:
            results_json[task_id] = {}
            results_json[task_id]["Name"] = None
            results_json[task_id]["Results"] = []

            task_results = self.get_task(task_id)

            for task_info in task_results:
                collection_id = task_info["metadata"]["collection_id"]
                plugin = task_info["metadata"]["key"]

                if plugin in COLLECTION_SCOPE:
                    collection_scope = COLLECTION_SCOPE[plugin]

                if plugin in COLLECTION_MAPPING:
                    collection_name = COLLECTION_MAPPING[plugin]
                else:
                    collection_name = plugin

                results_json[task_id]["Name"] = collection_name

                if scope:
                    results = self.retrieve_collection(
                        collection_id, scope, limit=limit
                    )

                else:
                    results = self.retrieve_collection(
                        collection_id, collection_scope, limit=limit
                    )

                for result in results:
                    results_json[task_id]["Results"].append(result)

        return results_json

    def retrieve_investigation_scope_results(self, investigation_id, scope, limit=None):
        results = []
        investigation_results = self.retrieve_investigation_results(
            investigation_id, scope=scope, limit=limit
        )

        for task_id, investigation_result in list(investigation_results.items()):
            for result in investigation_result.get("Results", []):
                results.append(result)

        return results

    def get_investigation_core_os(self, investigation_id):
        investigation = self.get_investigation(investigation_id)
        return investigation.core_os

    def retrieve_task_results(self, bulk_task_id, limit=None):
        """
        Get Task results
        :param bulk_task_id: {string} task ID
        :param limit: {int} Max num of results to return
        :return: {list} Task results
        """
        collection_id = self.get_collection_id_by_bulk_task_id(bulk_task_id)
        return self.retrieve_collection(collection_id, limit=limit)

    def create_investigation(
        self, investigation_name, assign_user, sensor_ids, tasks, core_os=None
    ):
        """
        Start an Investigation
        :param investigation_name: {string} The name of the investigation
        :param assign_user: {string} user to assign the investigation
        :param sensor_ids: {list} List of the sensors to run the investigation on
        :param tasks: The tasks to perform (schema depends on the task)
        :param core_os: {string} can create a single investigation for endpoints that run on the same os.
        :return: {string} investigation id
        """
        user_id = self.get_userid(assign_user)

        payload = {
            "sensor_ids": sensor_ids,
            "name": investigation_name,
            "tasks": tasks,
            "assign_to": user_id,
            "user_id": user_id,
            "core_os": core_os,
        }

        payload = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(f"{self.api_root}/investigations", json=payload)
        self.validate_response(
            response, f"Unable to create investigation {investigation_name}"
        )
        return response.json().get("data", {}).get("id")

    @staticmethod
    def create_ioc_file_search_task(
        regexes=None,
        with_md5_hash=None,
        with_sha1_hash=None,
        with_sha256_hash=None,
        directory=None,
    ):
        task = {
            "regexes": regexes,
            "with_md5_hash": with_md5_hash,
            "with_sha1_hash": with_sha1_hash,
            "with_sha256_hash": with_sha256_hash,
            "directory": directory,
        }

        return {"file_search": {k: v for k, v in list(task.items()) if v}}

    @staticmethod
    def create_ioc_network_search_task(
        with_state="ANY",
        protocol="ALL",
        find_remote_ip_addresses=None,
        find_local_ip_address=None,
        network_port=None,
        network_remote=None,
    ):
        task = {
            "with_state": with_state,
            "protocol": protocol,
            "find_remote_ip_address": find_remote_ip_addresses,
            "find_local_ip_address": find_local_ip_address,
        }

        if network_port:
            task["port"] = {
                "port": network_port,
                "key": "remote" if network_remote else "local",
            }

        return {"network_search": {k: v for k, v in list(task.items()) if v}}

    @staticmethod
    def create_ioc_process_search_task(
        with_md5_hash=None,
        with_sha1_hash=None,
        with_sha256_hash=None,
        find_process=None,
    ):
        task = {
            "with_md5_hash": with_md5_hash,
            "with_sha1_hash": with_sha1_hash,
            "with_sha256_hash": with_sha256_hash,
            "find_process": find_process,
        }

        return {"process_search": {k: v for k, v in list(task.items()) if v}}

    @staticmethod
    def create_ioc_registry_search_task(
        hive="ALL", key=None, min_size=None, max_size=None
    ):
        task = {"hive": hive, "key": key, "min_size": min_size, "max_size": max_size}

        return {"registry_search": {k: v for k, v in list(task.items()) if v}}

    @staticmethod
    def create_ioc_username_search_task(find_username=None, domain=None):
        task = {"find_username": find_username, "domain": domain}

        return {"username_search": {k: v for k, v in list(task.items()) if v}}

    @staticmethod
    def create_autorun_collection_task(
        category_all=True,
        category_network_provider=False,
        category_office=False,
        category_driver=False,
        category_app_init=False,
        category_winlogon=False,
        category_print_monitor=False,
        category_ease_of_access=False,
        category_wmi=False,
        category_lsa_provider=False,
        category_service=False,
        category_bits=False,
        category_known_dll=False,
        category_print_provider=False,
        category_image_hijack=False,
        category_startup_folder=False,
        category_internet_explorer=False,
        category_codec=False,
        category_logon=False,
        category_search_order_hijack=False,
        category_winsock_provider=False,
        category_boot_execute=False,
        category_phantom_dll=False,
        category_com_hijack=False,
        category_explorer=False,
        category_scheduled_task=False,
        include_all_metadata=True,
        include_malware_classification_metadata=False,
        include_authenticode_metadata=False,
        include_md5_hash=False,
        include_sha1_hash=False,
        include_sha256_hash=False,
    ):
        task = {
            "category_option": {
                "category_all": category_all,
                "category_network_provider": category_network_provider,
                "category_office": category_office,
                "category_driver": category_driver,
                "category_app_init": category_app_init,
                "category_winlogon": category_winlogon,
                "category_print_monitor": category_print_monitor,
                "category_ease_of_access": category_ease_of_access,
                "category_wmi": category_wmi,
                "category_lsa_provider": category_lsa_provider,
                "category_service": category_service,
                "category_bits": category_bits,
                "category_known_dll": category_known_dll,
                "category_print_provider": category_print_provider,
                "category_image_hijack": category_image_hijack,
                "category_startup_folder": category_startup_folder,
                "category_internet_explorer": category_internet_explorer,
                "category_codec": category_codec,
                "category_logon": category_logon,
                "category_search_order_hijack": category_search_order_hijack,
                "category_winsock_provider": category_winsock_provider,
                "category_boot_execute": category_boot_execute,
                "category_phantom_dll": category_phantom_dll,
                "category_com_hijack": category_com_hijack,
                "category_explorer": category_explorer,
                "category_scheduled_task": category_scheduled_task,
            },
            "metadata_option": {
                "metadata_all": include_all_metadata,
                "metadata_malware_classification": include_malware_classification_metadata,
                "metadata_sha1": include_sha1_hash,
                "metadata_sha256": include_sha256_hash,
                "metadata_authenticode": include_authenticode_metadata,
                "metadata_md5": include_md5_hash,
            },
        }

        task["category_option"] = {
            k: v for k, v in list(task["category_option"].items()) if v
        }
        task["metadata_option"] = {
            k: v for k, v in list(task["metadata_option"].items()) if v
        }
        return task

    @staticmethod
    def create_download_file_task(existing_path, expected_sha256=None, chunk_size=4096):
        task = {
            "chunk_size": chunk_size,
            "existing_path": existing_path,
            "expected_sha256": expected_sha256,
        }

        return {k: v for k, v in list(task.items()) if v}

    @staticmethod
    def create_delete_file_task(existing_path):
        return {"existing_path": existing_path}

    @staticmethod
    def create_kill_process_task(process_name, pid=None):
        task = {"kill_procname": process_name}

        if pid:
            task["pid"] = pid

        return task

    @staticmethod
    def create_process_survey_task(
        only_suspicious_processes=False,
        collect_process_threads=False,
        detect_malware=False,
        detect_fileless_attacks=False,
    ):
        task = {}

        if only_suspicious_processes:
            task["filter_list"] = [
                {"rwx_permissions": True},
                {"unbacked_executable": True},
            ]

        if collect_process_threads:
            task["gather_threads"] = True

        if detect_malware:
            task["gather_malware_score"] = True

        if detect_fileless_attacks:
            task["gather_defense_evasion"] = True

        return task

    @staticmethod
    def create_network_survey_task(extended_survey=False):
        return {"extended_survey": extended_survey}

    def is_investigation_complete(self, investigation_id):
        """
        Check if investigation has completed
        :param investigation_id: {unicode} investigation id
        :return: {bool} True if investigation has completed, otherwise False
        """
        investigation = self.get_investigation(investigation_id)
        return investigation.total_tasks == investigation.completed_tasks

    def is_task_complete(self, bulk_task_id):
        """
        Check whether a task has completed
        :param bulk_task_id: {unicode} The task's bulk id
        :return: {bool} True if completed, False otherwise
        """
        collection_id = self.get_collection_id_by_bulk_task_id(bulk_task_id)
        response = self.session.get(f"{self.api_root}/collections/{collection_id}")
        self.validate_response(
            response, f"Unable to get find collection {collection_id}"
        )
        return response.json().get("data", {}).get("status") in ["success", "failure"]

    def is_task_failed(self, bulk_task_id):
        """
        Check whether a task has failed
        :param bulk_task_id: {unicode} The task's bulk id
        :return: {bool} True if failed, False otherwise
        """
        collection_id = self.get_collection_id_by_bulk_task_id(bulk_task_id)
        response = self.session.get(f"{self.api_root}/collections/{collection_id}")
        self.validate_response(
            response, f"Unable to get find collection {collection_id}"
        )
        return response.json().get("data", {}).get("status") == "failure"

    def get_collection_by_id(self, collection_id):
        """
        Get a collection by its id
        :param collection_id: {unicode} The collection id
        :return: {dict} The collection
        """
        response = self.session.get(
            f"{self.api_root}/collections", params={"id": collection_id, "per_page": 1}
        )
        self.validate_response(
            response, f"Unable to get find collection {collection_id}"
        )
        collections = response.json().get("data", [])

        if not collections:
            raise EndgameNotFoundError(f"Unable to get find collection {collection_id}")

        return collections[0]

    def download_file(self, file_uuid):
        """
        Download a file
        :param file_uuid: {unicode} The uuid of the file to download
        :return: {unicode} The content of the file
        """
        response = self.session.get(
            f"{self.api_root}/files/{file_uuid}", params={"raw": True}
        )
        self.validate_response(response, f"Unable to get download file {file_uuid}")
        return response.content

    def get_alerts_by_query(self, query):
        """
        Get alerts by query
        :param query: {dict} query params
        :return: {tuple} result, payload
        """
        results = self.session.get(f"{self.api_root}/alerts", params=query)
        self.validate_response(results)
        return results.json(), query

    def get_alerts(
        self,
        end_timestamp=None,
        start_timestamp=None,
        endpoint_id=None,
        archived=False,
        assignee=None,
        severity=None,
        alert_type=None,
        viewed=False,
        updated_last_viewed=False,
        raw=False,
        csv=False,
        limit_per_page=None,
    ):
        """
        Gets Alert objects.
        :param end_timestamp: {string} datetime to fetch alerts from. All returned alerts will have been created after.
        :param start_timestamp: {string} datetime to fetch alerts up to. Returned alerts will have been created before
        :param endpoint_id: {string} UUID of endpoint to get alerts from
        :param archived: {bool} Whether or not to fetch only archived alerts
        :param assignee: {string} Name of assignee of alert
        :param severity: {string} Severity of alerts (low, medium, high)
        :param alert_type: {string} Type of alert (e.g. fileClassificationEventResponse)
        :param viewed: {bool} Whether or not to fetch alerts that have (or have not) been viewed by me.
        :param updated_last_viewed: {bool} When true, the last_viewed_alert timestamp is updated on the user if the indexed_at timestamp of any matched alerts is more recent than the previously set last_viewed_alert timestamp
        :param raw: {bool} Download a json version of the alerts when True
        :param raw: {bool} Download a json version of the alerts when True
        :param csv: {bool} Download a csv version of the alerts if true
        :return: {tuple} result, payload
        """
        payload = {}
        if endpoint_id:
            payload["endpoint.id"] = endpoint_id

        if assignee:
            payload["assignee"] = assignee

        if severity:
            payload["severity"] = severity

        if start_timestamp:
            payload["to"] = start_timestamp

        if end_timestamp:
            payload["from"] = end_timestamp

        if alert_type:
            payload["type"] = alert_type

        if viewed:
            payload["viewed"] = viewed

        if updated_last_viewed:
            payload["updated_last_viewed"] = updated_last_viewed

        payload["archived"] = archived
        payload["raw"] = raw
        payload["csv"] = csv

        # Order by alert creation time (Ascending - so the oldest will be the first)
        payload["order_by"] = "created_at"

        # Results are by default paginated with a page size of 50,
        # current page and page size can be adjusted using the page and per_page query parameters
        if limit_per_page:
            payload["per_page"] = limit_per_page

        results = self.session.get(f"{self.api_root}/alerts", params=payload)
        self.validate_response(results)
        return results.json(), payload

    def initialize_isolation_task(self, task_id, sensor_ids, isolate=True):
        """
        Isolate / release hosts
        :param task_id: {unicode} The task id of the isolation task
        :param sensor_ids: {list} The ids of the sensors to isolate
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.api_root}/tasks"
        response = self.session.post(
            url, json={"description_id": task_id, "sensor_ids": sensor_ids, "task": {}}
        )
        self.validate_response(
            response,
            f"Unable to initialize host {'isolation' if isolate else 'unisolation'} task",
        )

        if not response.json().get("data", {}).get("valid"):
            raise EndgameError(
                f"Host {'isolation' if isolate else 'unisolation'} task failed: {response.content}"
            )

        return True

    def initialize_task(self, task_id, sensor_ids, task, core_os):
        """
        Initiate a task
        :param task_id: {unicode} The task id of the isolation task
        :param sensor_ids: {list} The ids of the sensors to isolate
        :param task: {dict} The task payload
        :param core_os: {unicode} The core OS of the task
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.api_root}/tasks"
        response = self.session.post(
            url,
            json={
                "description_id": task_id,
                "sensor_ids": sensor_ids,
                "task": task,
                "core_os": core_os,
            },
        )
        self.validate_response(response, "Unable to initialize task")

        if not response.json().get("data", {}).get("valid"):
            raise EndgameError(f"Task initialization failed: {response.content}")

        return response.json().get("data", {}).get("bulk_task_id")

    def get_collection_id_by_bulk_task_id(self, bulk_task_id):
        url = f"{self.api_root}/tasks"
        response = self.session.get(url, params={"bulk_task_id": bulk_task_id})
        self.validate_response(response, f"Unable to get task {bulk_task_id}")

        if not response.json().get("data"):
            raise EndgameError(f"Task {bulk_task_id} was not found")

        return response.json().get("data")[0].get("metadata", {}).get("collection_id")

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        filter_key=None,
        filter_value=None,
        filter_exact=True,
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if params is None:
            params = {}

        params.update({"page": 1, "per_page": DEFAULT_PAGE_SIZE})

        response = self.session.request(method, url, params=params, json=body)

        self.validate_response(response, err_msg)
        results = response.json().get("data", [])

        while True:
            if filter_key:
                for result in results:
                    if filter_exact:
                        if result.get(filter_key) == filter_value:
                            break
                    else:
                        if filter_value in result.get(filter_key):
                            break

            if limit and len(results) >= limit:
                break

            if not response.json().get("next"):
                break

            params.update({"page": len(results)})

            response = self.session.request(method, url, params=params, json=body)

            self.validate_response(response, err_msg)
            results.extend(response.json().get("data", []))

        return results[:limit] if limit else results

    def _paginate_task_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a task
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if params is None:
            params = {}

        params.update({"page": 1, "per_page": min(DEFAULT_PAGE_SIZE, limit)})

        response = self.session.request(method, url, params=params, json=body)

        self.validate_response(response, err_msg)
        results = response.json().get("data", {}).get("data", {}).get("results", [])

        while True:
            if limit and len(results) >= limit:
                break

            if not response.json().get("metadata", {}).get("next"):
                break

            params.update({"page": len(results)})

            response = self.session.request(method, url, params=params, json=body)

            self.validate_response(response, err_msg)
            results.extend(
                response.json().get("data", {}).get("data", {}).get("results", [])
            )

        return results[:limit] if limit else results
