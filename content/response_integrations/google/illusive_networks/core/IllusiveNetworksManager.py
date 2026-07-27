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

from __future__ import annotations
import requests
import urllib.parse
from .IllusiveNetworksExceptions import (
    IllusiveNetworksException,
    IncidentNotReadyException,
    RateLimitException,
    ManagerNotFoundException,
)
from .IllusiveNetworksParser import IllusiveNetworksParser
import base64
from .constants import (
    CA_CERTIFICATE_FILE_PATH,
    PING_QUERY,
    FORENSIC_SCAN_QUERY,
    GET_INCIDENT_ID_QUERY,
    GET_FORENSIC_DATA_QUERY,
    ENRICH_ENTITIES_QUERY,
    FORENSIC_DATA_TYPES,
    GET_DECEPTIVE_USERS_QUERY,
    GET_DECEPTIVE_SERVERS_QUERY,
)

API_ENDPOINTS = {
    "get_incidents": "/api/v1/incidents",
    "timeline": "/api/v1/forensics/timeline",
    "deceptive_server": "api/v1/deceptive-entities/server",
    "deceptive_servers": "api/v1/deceptive-entities/servers",
    "deceptive_user": "api/v1/deceptive-entities/user",
    "deceptive_users": "api/v1/deceptive-entities/users",
}


class IllusiveNetworksManager:
    def __init__(
        self,
        api_root=None,
        api_key=None,
        ca_certificate=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the Illusive Networks
        :param api_key: API Key of the Illusive Networks instance.
        :param ca_certificate: CA Certificate as base64
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to
        the Illusive Networks server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        ca_certs = False if not verify_ssl else None

        # ca_certificate is base64 string which needs to be decoded and a temp file
        # for the cacert is created
        if ca_certificate:
            try:
                file_content = base64.b64decode(ca_certificate)
                with open(CA_CERTIFICATE_FILE_PATH, "w+") as f:
                    f.write(file_content.decode("utf-8"))

            except Exception as e:
                raise IllusiveNetworksException(e)

        if verify_ssl and ca_certificate:
            verify = CA_CERTIFICATE_FILE_PATH

        elif verify_ssl and not ca_certificate:
            verify = True
        else:
            verify = False

        self.session = requests.session()
        self.session.verify = verify

        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.siemplify_logger = siemplify_logger
        self.session.headers.update({"Authorization": f"Basic {self.api_key}"})
        self.parser = IllusiveNetworksParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            if response.status_code == 202:
                raise IncidentNotReadyException("Incident Not Ready")

            if response.status_code == 429:
                raise RateLimitException(
                    "Rate limit error. Please refer to the documentation on how to "
                    "increase the rate limit"
                )
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response_json = response.json()
            except:
                # Not a JSON - return content
                raise IllusiveNetworksException(
                    f"{error_msg}: {error} - {error.response.content}"
                )
            raise IllusiveNetworksException(
                f"{error_msg}: {response_json.get('message', '')} "
                f"{response_json.get('errorMessage', '')}"
            )

    def test_connectivity(self):
        """
        Test integration connectivity.
        """

        result = self.session.get(PING_QUERY.format(self.api_root))
        # Verify result.
        self.validate_response(result)

    def create_forensic_scan_request(self, entity_name):
        """
        Function that initiates the forensic scan
        :param entity_name: {str} Entity for which the scan should be initiated
        """
        result = self.session.post(
            FORENSIC_SCAN_QUERY.format(self.api_root, entity_name)
        )
        # Verify result.
        self.validate_response(result)

        return result.json().get("eventId")

    def get_incident_id(self, event_id):
        """
        Function that checks if the incident for given event_id is ready to be fetched
        :param event_id: {str} Event ID that needs to be checked
        """

        result = self.session.get(GET_INCIDENT_ID_QUERY.format(self.api_root, event_id))
        # Verify result.
        self.validate_response(result)

    def get_forensic_data(
        self,
        event_id,
        include_sys_info,
        include_prefetch_files_info,
        include_add_remove,
        include_startup_info,
        include_running_info,
        include_user_assist_info,
        include_powershell_info,
    ):
        """
        Function that fetches the forensic scan information
        :param include_sys_info: True if System Info should be included in results
        :param include_prefetch_files_info: True if Prefetch Files Info should be
        included in results
        :param include_add_remove: True if Add Remove Processes should be included
        in results
        :param include_startup_info: True if Startup Processes should be included
        in results
        :param include_running_info: True if Running Processes should be included
        in results
        :param include_user_assist_info: True if User Assist should be included
        in results
        :param include_powershell_info: True if Powershell Info should be included
        in results
        :return object_data: {dict} Dictionary of requested parameters
        """

        object_data = {}
        if include_sys_info:
            result = self.session.get(
                GET_FORENSIC_DATA_QUERY.format(
                    self.api_root, event_id, FORENSIC_DATA_TYPES.get("include_sys_info")
                )
            )
            # Verify result.
            self.validate_response(result)

            host_info = self.parser.build_siemplify_forensic_host_info_object(
                result.json()
            )
            object_data["host_info"] = host_info

        if include_prefetch_files_info:
            result = self.session.get(
                GET_FORENSIC_DATA_QUERY.format(
                    self.api_root,
                    event_id,
                    FORENSIC_DATA_TYPES.get("include_prefetch_files_info"),
                )
            )
            # Verify result.
            self.validate_response(result)

            prefetch_files_info = (
                self.parser.build_siemplify_forensic_prefetch_info_object(result.json())
            )
            object_data["prefetch_info"] = prefetch_files_info

        if include_add_remove:
            result = self.session.get(
                GET_FORENSIC_DATA_QUERY.format(
                    self.api_root,
                    event_id,
                    FORENSIC_DATA_TYPES.get("include_add_remove"),
                )
            )
            # Verify result.
            self.validate_response(result)

            add_remove_info = self.parser.build_siemplify_forensic_add_remove_object(
                result.json()
            )
            object_data["include_add_remove"] = add_remove_info

        if include_startup_info:
            result = self.session.get(
                GET_FORENSIC_DATA_QUERY.format(
                    self.api_root,
                    event_id,
                    FORENSIC_DATA_TYPES.get("include_startup_info"),
                )
            )
            # Verify result.
            self.validate_response(result)

            include_startup_info = self.parser.build_siemplify_forensic_startup_object(
                result.json()
            )
            object_data["include_startup_info"] = include_startup_info

        if include_running_info:
            result = self.session.get(
                GET_FORENSIC_DATA_QUERY.format(
                    self.api_root,
                    event_id,
                    FORENSIC_DATA_TYPES.get("include_running_info"),
                )
            )
            # Verify result.
            self.validate_response(result)

            include_running_info = (
                self.parser.build_siemplify_forensic_runningprocesses_object(
                    result.json()
                )
            )
            object_data["include_running_info"] = include_running_info

        if include_user_assist_info:
            result = self.session.get(
                GET_FORENSIC_DATA_QUERY.format(
                    self.api_root,
                    event_id,
                    FORENSIC_DATA_TYPES.get("include_user_assist_info"),
                )
            )
            # Verify result.
            self.validate_response(result)

            include_user_assist_info = (
                self.parser.build_siemplify_forensic_userassist_object(result.json())
            )
            object_data["user_assist_info"] = include_user_assist_info

        if include_powershell_info:
            result = self.session.get(
                GET_FORENSIC_DATA_QUERY.format(
                    self.api_root,
                    event_id,
                    FORENSIC_DATA_TYPES.get("include_powershell_info"),
                )
            )
            # Verify result.
            self.validate_response(result)

            include_powershell_info = (
                self.parser.build_siemplify_forensic_powershell_object(result.json())
            )
            object_data["powershell_history"] = include_powershell_info

        return object_data

    def enrich_entity(self, host_entity_name):
        """
        Function that gets details about a host
        :param host_entity_name: {str} Name of the host to enrich
        :return: {HostObject} Siemplify HostObject
        """

        result = self.session.get(
            ENRICH_ENTITIES_QUERY.format(self.api_root, host_entity_name)
        )
        # Verify result.
        self.validate_response(result)

        return self.parser.build_siemplify_host_object(result.json())

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urllib.parse.urljoin(
            self.api_root, API_ENDPOINTS[url_id].format(**kwargs)
        )

    def get_incidents(self, start_date):
        """
        Get incidents
        :param start_date: {str} Start time to fetch incidents
        :return: {list} List of Incident
        """
        return sorted(
            self._paginate_results(
                method="GET",
                url=self._get_full_url("get_incidents"),
                parser_method="build_siemplify_incident_object",
                params={"start_date": start_date},
            ),
            key=lambda x: x.timestamp,
        )

    def _paginate_results(
        self,
        method,
        url,
        parser_method,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        page_size=100,
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param parser_method: {str} The name of parser method to build the result
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :param page_size: {int} Items per page
        :return: {list} List of results
        """

        params = params or {}
        offset = 0
        params["limit"] = page_size
        params.update({"offset": offset})

        response = None
        results = []

        while True:
            if response:
                if limit and len(results) >= limit:
                    break

                params.update({"offset": params["offset"] + page_size})

            response = self.session.request(method, url, params=params, json=body)

            self.validate_response(response, err_msg)
            current_items = [
                getattr(self.parser, parser_method)(item_json)
                for item_json in response.json()
            ]
            results.extend(current_items)
            if len(current_items) < page_size:
                break
        return results[:limit] if limit else results

    def get_incident_timeline(self, incident_id):
        """
        Get incident timeline
        :param incident_id: {str} Incident if to load timeline
        :return: {list} List of BaseModel
        """
        response = self.session.get(
            self._get_full_url("timeline"), params={"incident_id": incident_id}
        )
        self.validate_response(
            response, f"Unable to load timeline for incident {incident_id}"
        )
        return self.parser.build_incident_events(response.json())

    def get_deceptive_users(self, deceptive_state, limit=None):
        """
        Get deceptive users list
        :param deceptive_state: {str} deceptive state
        :param limit: {int} Items to return
        :return: {list} List of DeceptiveUser
        """
        response = self.session.get(
            GET_DECEPTIVE_USERS_QUERY.format(self.api_root, deceptive_state)
        )
        self.validate_response(response)

        return self.parser.build_siemplify_deceptive_user_obj_list(
            response.json(), limit
        )

    def get_deceptive_servers(self, deceptive_state, limit=None):
        """
        Get deceptive servers list
        :param deceptive_state: {str} deceptive state
        :param limit: {int} Items to return
        :return: {list} List of DeceptiveServer
        """
        response = self.session.get(
            GET_DECEPTIVE_SERVERS_QUERY.format(self.api_root, deceptive_state)
        )
        self.validate_response(response)

        return self.parser.build_siemplify_deceptive_server_obj_list(
            response.json(), limit
        )

    def get_deceptive_server(self, host_name):
        """
        Get deceptive server by host name
        :param host_name: {str}
        :return: {DeceptiveServer or None}
        """
        response = self.session.get(
            self._get_full_url("deceptive_server"), params={"hostName": host_name}
        )
        self.validate_response(response)

        return (
            self.parser.build_siemplify_deceptive_server_obj(response.json())
            if response.content
            else None
        )

    def remove_deceptive_server(self, hosts):
        """
        Remove deceptive server by hosts names
        :param hosts: {list} List of host names
        :return: {bool}
        """
        response = self.session.delete(
            self._get_full_url("deceptive_servers"), params={"deceptive_hosts": hosts}
        )
        self.validate_response(response)

        return True

    def add_deceptive_server(self, host, server_types, policy_names):
        """
        Add deceptive server or raise if host already exist
        :param host: {str}
        :param server_types: {list}
        :param policy_names: {list}
        :return: {bool}
        """
        payload = [
            {"host": host, "policyNames": policy_names, "serviceTypes": server_types}
        ]
        response = self.session.post(
            self._get_full_url("deceptive_servers"), json=payload
        )
        self.validate_response(response)

        return True

    def get_deceptive_server_or_raise(self, host_name):
        """
        Get deceptive server by host name or raise
        :param host_name: {str}
        :return: {DeceptiveServer}
        """
        deceptive_server = self.get_deceptive_server(host_name)

        if deceptive_server is not None:
            return deceptive_server

        raise ManagerNotFoundException(
            f'Deceptive server "{host_name}" doesn\'t exist.'
        )

    def get_deceptive_user(self, username):
        """
        Get deceptive user by username
        :param username: {str}
        :return: {DeceptiveUser or None}
        """
        response = self.session.get(
            self._get_full_url("deceptive_user"), params={"userName": username}
        )
        self.validate_response(response)

        return (
            self.parser.build_siemplify_deceptive_user_obj(response.json())
            if response.content
            else None
        )

    def add_deceptive_user(self, dns_domain, username, password, policy_names):
        """
        Add deceptive user or raise if user already exist
        :param dns_domain: {str}
        :param username: {str}
        :param password: {str}
        :param policy_names: {list}
        :return: {bool}
        """
        payload = [
            {
                "domainName": dns_domain,
                "username": username,
                "password": password,
                "policyNames": policy_names,
            }
        ]
        response = self.session.post(
            self._get_full_url("deceptive_users"), json=payload
        )
        self.validate_response(response)

        return True

    def get_deceptive_user_or_raise(self, username):
        """
        Get deceptive user by username or raise
        :param username: {str}
        :return: {DeceptiveUser}
        """
        deceptive_user = self.get_deceptive_user(username)

        if deceptive_user is not None:
            return deceptive_user

        raise ManagerNotFoundException(f'Deceptive user "{username}" doesn\'t exist.')

    def remove_deceptive_user(self, usernames):
        """
        Remove deceptive users by usernames
        :param usernames: {list} List of usernames
        :return: {bool}
        """
        response = self.session.delete(
            self._get_full_url("deceptive_users"), params={"deceptive_users": usernames}
        )
        self.validate_response(response)

        return True
