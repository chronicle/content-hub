# ============================================================================#
# title           :TrendMicroApexCentralManager.py
# description     :This Module contain all Trend Micro Apex Central operations functionality
# author          :gabriel.munits@siemplify.co
# date            :21-03-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#
from __future__ import annotations
import base64
import copy
import hashlib
import json
from typing import Optional
from urllib.parse import urljoin

import jwt
import requests

from soar_sdk.SiemplifyUtils import unix_now
from .TrendMicroApexCentralParser import TrendMicroApexCentralParser
from .consts import (
    INTEGRATION_DISPLAY_NAME,
    CHECKSUM_ALGORITHM,
    JWT_TOKEN_VERSION,
    AUTHORIZATION_ERROR_STATUS_CODE,
    DEFAULT_LIMIT,
    ENDPOINT_SENSOR_TASK_TYPE,
)
from .exceptions import (
    TrendMicroApexCentralManagerError,
    TrendMicroApexCentralValidationError,
    TrendMicroApexCentralAuthorizationError,
)
from .utils import get_params_to_url


ENDPOINTS = {
    "ping_query": "/WebApp/API/ServerResource/ProductServers",
    "list_udso_entries": "/WebApp/api/SuspiciousObjects/UserDefinedSO",
    "add_udso_entry": "/WebApp/api/SuspiciousObjects/UserDefinedSO",
    "add_udso_file": "/WebApp/API/SuspiciousObjectResource/FileUDSO",
    "list_security_agents": "/WebApp/API/AgentResource/ProductAgents",
    "endpoint_sensor_to_query": "V1/Task/ShowAgentList",
    "list_all_security_agents_with_enabled_endpoint": "/WebApp/OSCE_iES/OsceIes/ApiEntry",
    "isolate_endpoint": "/WebApp/API/AgentResource/ProductAgents",
    "unisolate_endpoint": "/WebApp/API/AgentResource/ProductAgents",
}

HEADERS = {"Content-Type": "application/json"}


class TrendMicroApexCentralManager:
    """
    Trend Micro Apex Central Manager
    """

    def __init__(
        self,
        api_root,
        application_id,
        api_key,
        verify_ssl: Optional[bool] = False,
        siemplify_logger=None,
    ):
        """
        The method is used to instantiate an object of Manager class
        :param api_root: {str} API root of the Trend Micro Apex Central instance
        :param application_id: {str} Application ID of the Trend Micro Central instance
        :param api_key: {str} API Key of the Trend Micro Apex Central instance
        :param verify_ssl: {bool} True if to verify SSL connection, otherwise False
        :param siemplify_logger: Siemplify Logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.application_id = application_id
        self.api_key = api_key
        self.siemplify_logger = siemplify_logger

        self.verify_ssl = verify_ssl
        self.parser = TrendMicroApexCentralParser()

    def _get_full_url(self, request_api_endpoint, **kwargs):
        """
        Get full url from url identifier.
        :param request_api_endpoint: {str} Request API endpoint
        :param kwargs: {dict} Variables passed for string formatting in url
        :return: {str} The full url
        """
        return urljoin(self.api_root, request_api_endpoint.format(**kwargs))

    @staticmethod
    def _create_checksum(
        http_method,
        request_api_endpoint,
        canonical_request_headers=None,
        params=None,
        request_body=None,
    ):
        """
        Create checksum as part of encoded jwt token
        :param http_method: {str} http method - 'GET', 'POST', 'PUT' and 'DELETE'
        :param params: {dict} request params
        :param request_api_endpoint: {str} request api endpoint
        :param canonical_request_headers: {str} List of all request headers that start with "API". If no headers start with API,
            should be empty
        :param request_body: {dict} request body
        :return: {str} base 64 encoded checksum
        """
        query_params = get_params_to_url(params) if params else ""
        request_body = json.dumps(request_body) if request_body else ""
        string_to_hash = (
            f'{http_method.upper()}|{request_api_endpoint.lower() + query_params.lower()}|{canonical_request_headers or ""}|'
            f"{request_body}"
        )
        base64_string = base64.b64encode(
            hashlib.sha256(str.encode(string_to_hash)).digest()
        ).decode("utf-8")
        return base64_string

    def _get_jwt_token(
        self,
        http_method,
        request_api_endpoint,
        headers=None,
        params=None,
        request_body=None,
    ):
        """
        Get base 64 encoded jwt token for each request
        :param http_method: {str} 'GET', 'POST', 'PUT' and 'DELETE'
        :param request_api_endpoint: {str} request api endpoint
        :param headers: {dict} request headers
        :param request_body: {dict} request body payload
        :return: {str} jwt encoded token
        """
        payload = {
            "appid": self.application_id,
            "iat": int(unix_now() / 1000),
            "version": JWT_TOKEN_VERSION,
            "checksum": self._create_checksum(
                http_method, request_api_endpoint, headers, params, request_body
            ),
        }
        token = jwt.encode(payload, self.api_key, algorithm=CHECKSUM_ALGORITHM)
        return token

    def _make_request(
        self, http_method, request_api_endpoint, params=None, body=None, headers=None
    ):
        """
        Make a request to Trend Micro Apex Central
        :return: {requests.Response} requests Response object
        """
        jwt_token = self._get_jwt_token(
            http_method, request_api_endpoint, headers, params, body
        )
        request_url = self._get_full_url(request_api_endpoint)

        headers = HEADERS
        headers.update({"Authorization": f"Bearer {jwt_token}"})
        return requests.request(
            method=http_method,
            url=request_url,
            params=params,
            data=json.dumps(body) if body else None,
            headers=headers,
            verify=self.verify_ssl,
        )

    def test_connectivity(self):
        """
        Test connectivity to the Trend Micro Apex Central instance
        :return: {bool} True if successful, exception otherwise
        """
        response = self._make_request(
            http_method="GET",
            request_api_endpoint=ENDPOINTS["ping_query"],
            params={"host_name": "x"},
        )
        self.validate_response(
            response, f"Unable to connect to {INTEGRATION_DISPLAY_NAME}"
        )

    def list_udso_entries(self, udso_type=None, content_filter=None):
        """
        Retrieves a list of User-Defined Suspicious Objects from the Apex Central server
        :param udso_type: {str} The suspicious object type to query: ip, url, file_sha1, domain, file
        :param content_filter: {str} Filters the list to suspicious objects that match the specified string
        :return: [[UDSOEntry]} List of UDSO entries
        """
        params = {}
        if udso_type:
            params["type"] = udso_type
        if content_filter:
            params["contentFilter"] = content_filter

        response = self._make_request(
            http_method="GET",
            request_api_endpoint=ENDPOINTS["list_udso_entries"],
            params=params,
        )
        self.validate_response(response, "Failed to list of UDSO entries")
        return self.parser.build_list_udso_entries(response.json())

    def add_udso_to_list(
        self, entity_type, entity_value, expiration_utc_date, scan_option, notes=None
    ):
        """
        Adds the specified object information tot he User-Defined Suspicious Objects list
        :param entity_type: {str} Entity suspicious object type. Possible values of ip, url, file_sha1, domain
        :param entity_value: {str} Entity value. Ip is of IPV4 type. URL starting with http:// or https:// (maximum length of 2047
        character). File Hash (SHA-1 only and maximum length of 40 characters).
        :param expiration_utc_date: {str} The expiration date (UTC) of the suspicious object.
        :param scan_option: {str} The scan action to perform on the suspicious object. Can be log or block
        :param notes: {str} Description of the object
        :return: throw an Exception in case of error
        """
        payload = {
            "param": {
                "content": entity_value,
                "type": entity_type,
                "scan_action": scan_option,
            }
        }
        if expiration_utc_date:
            payload["param"]["expiration_utc_date"] = expiration_utc_date
        if notes:
            payload["param"]["notes"] = notes

        response = self._make_request(
            http_method="PUT",
            request_api_endpoint=ENDPOINTS["add_udso_entry"],
            body=payload,
        )
        self.validate_response(
            response, f"Failed to add UDSO of {entity_value} to list"
        )

    def add_udso_file_to_list(
        self, file_name, file_content_base64_string, file_scan_option, note=None
    ):
        """
        Adds the uploaded file information to the User-Defined Suspicious Objects list
        :param file_name: {str} The name of the file
        :param file_content_base64_string: {str} The binary content of the file, converted to a base64 string
        :param file_scan_option: {str} The scan action to perform. Can be LOG, BLOCK or QUARANTINE
        :param note: {str} Additional information
        :return:
        """
        payload = {
            "file_name": file_name,
            "file_content_base64_string": file_content_base64_string,
            "file_scan_action": file_scan_option,
            "note": note or "",
        }

        response = self._make_request(
            http_method="PUT",
            request_api_endpoint=ENDPOINTS["add_udso_file"],
            body=payload,
        )
        self.validate_response(
            response, f"Failed to add UDSO based file: {file_name} to list"
        )

    def get_udso_entry(self, udso_type, udso_entity):
        """
        Retrieve a User-Defined Suspicious Object from the Apex Central server if exists
        :param udso_type: {str} The suspicious object type to query: ip, url, file_sha1, domain, file
        :param udso_entity: {str} Filters the list to suspicious objects that match the specified string
        :return: {UDSOEntry} List of UDSO entries
        """
        params = {"type": udso_type, "contentFilter": udso_entity}
        response = self._make_request(
            http_method="GET",
            request_api_endpoint=ENDPOINTS["list_udso_entries"],
            params=params,
        )
        self.validate_response(response, f"Failed to get UDSO entry for {udso_entity}")
        listed_udso_entries = self.parser.build_list_udso_entries(response.json())
        return listed_udso_entries[0] if listed_udso_entries else None

    def list_security_agents(
        self,
        entity_id=None,
        ip_address=None,
        mac_address=None,
        host_name=None,
        product=None,
        managing_server_id=None,
    ):
        """
        Retrieves a list of Security Agents
        :param entity_id: {str} The GUID of the Security Agent
        :param ip_address: {str} The IP address of the endpoint
        :param mac_address: {str} The MAC address of the endpoint
        :param host_name: {str} The name of the endpoint
        :param product: {str} The Trend Micro product name
        :param managing_server_id: {str} The GUID of the product server that manages the Security Agent
        :return: {[SecurityAgent]} List of security agents matching the filters provided
        """
        params = {}
        if entity_id:
            params["entity_id"] = entity_id
        if ip_address:
            params["ip_address"] = ip_address
        if mac_address:
            params["mac_address"] = mac_address
        if host_name:
            params["host_name"] = host_name
        if product:
            params["product"] = product
        if managing_server_id:
            params["managing_server_id"] = managing_server_id

        response = self._make_request(
            http_method="GET",
            request_api_endpoint=ENDPOINTS["list_security_agents"],
            params=params,
        )
        self.validate_response(response, "Failed to list security agents")
        return self.parser.build_list_security_agents(response.json())

    def get_security_agent(
        self,
        entity_id=None,
        ip_address=None,
        mac_address=None,
        host_name=None,
        product=None,
        managing_server_id=None,
    ):
        """
        Get a single Security Agent of matching filtered criteria
        :param entity_id: {str} The GUID of the Security Agent
        :param ip_address: {str} The IP address of the endpoint
        :param mac_address: {str} The MAC address of the endpoint
        :param host_name: {str} The name of the endpoint
        :param product: {str} The Trend Micro product name
        :param managing_server_id: {str} The GUID of the product server that manages the Security Agent
        :return: {SecurityAgent} Security Agent matching the filters provided if exists. Otherwise, None will be returned
        """
        listed_security_agents = self.list_security_agents(
            entity_id, ip_address, mac_address, host_name, product, managing_server_id
        )
        return listed_security_agents[0] if listed_security_agents else None

    def list_security_agents_with_sensor_enabled(
        self, endpoint_task_type=ENDPOINT_SENSOR_TASK_TYPE, limit=None, filters=None
    ):
        """
        Retrieves a list of all Security Agents with the Endpoint Sensor feature enabled
        :param endpoint_task_type: {str} Type of API request. For Endpoint Sensor, the value is always 4.
            1 - UNKNOWN
            2 - INTERNAL
            3 - CM
            4 - CMEF
            5 - OSF_COMMAND
            6 - OSF_QUERY
            7 - OSF_NOTIFY
            8 - OSF_LOG
            9 - MDR_ATTACK_DISCOVERY
            10 - OSF_SYS_CALL
        :param limit: {int} Max number of results to return. If limit is not provided, all results will be returned
        :param filters: {[{}]} List of filters to apply when listing security agents.
            Each filter consists of 2 keys - "type" and "value".
            "type" - Type of filter to use
                1 Endpoint name (partial string match)
                2 Endpoint type
                4 Endpoint IP address
                5 Endpoint operating system
                6 Endpoint user name (partial string match)
                7 Endpoint type (partial string match)
                8 Endpoint IP address (partial string match)
                9 Endpoint operation system (partial string match)
            "value" - Value of the filter type
                2 : Endpoint type
                    1 : Desktop
                    2 : Server
                4 : Endpoint IP range
                    [<Starting_IP_Address>, <Ending_IP_Address>]
                5 : Endpoint operation system
                    WIN_XP - Windows XP
                    WIN_VISTA - Windows Vista
                    WIN_7 - Windows 7
                    WIN_8 - Windows 8
                    WIN_10 - Windows 10
                    WIN_2000 - Windows 2000
                    WIN_2003 - Windows 2003
                    WIN_2008 - Windows 2008
                    WIN_2012 - Windows 2012
                    WIN_2016 - Windows 2016
                    IOS - iOS
                    MAC_OS - Mac OS
                    ANDROID - Android
                    SYMBIAN - Symbian
                    WIN_MOBILE - Windows Mobile
        :return: {[EnabledEndpointSecurityAgent]} List of security agents with enabled endpoint
        """
        payload = {
            "Payload": {
                "pagination": {"limit": DEFAULT_LIMIT, "offset": 0},
                "filter": filters or [],
            },
            "TaskType": endpoint_task_type,
            "Url": ENDPOINTS["endpoint_sensor_to_query"],
        }
        response = self._make_request(
            http_method="PUT",
            request_api_endpoint=ENDPOINTS[
                "list_all_security_agents_with_enabled_endpoint"
            ],
            body=copy.deepcopy(payload),
        )
        self.validate_response(
            response, error_msg="Failed to list enabled security agents"
        )
        results = self.parser.build_list_of_security_agents_with_enabled_endpoint(
            response.json()
        )

        while True:
            if limit and len(results) >= limit:
                break
            has_more_results = self.parser.extract_if_more_results_available_to_retrieve_all_security_agents_with_enabled_endpoint(
                response.json()
            )
            if not has_more_results:
                break
            payload["Payload"]["pagination"]["offset"] = len(results)
            response = self._make_request(
                http_method="PUT",
                request_api_endpoint=ENDPOINTS[
                    "list_all_security_agents_with_enabled_endpoint"
                ],
                body=copy.deepcopy(payload),
            )
            self.validate_response(
                response, "Failed to list more of enabled security agents"
            )
            results.extend(
                self.parser.build_list_of_security_agents_with_enabled_endpoint(
                    response.json()
                )
            )

        return results[:limit] if limit else results

    def isolate_endpoint(
        self,
        ip_address: Optional[str] = None,
        host_name: Optional[str] = None,
        mac_address: Optional[str] = None,
    ):
        """
        Isolate an endpoint. Prevents the endpoint from connecting to the network
        :param ip_address: {str} The IP address of the managed product agent. Use to identify the agent(s) on which the action is performed.
        :param host_name: {str} The endpoint name of the managed product agent. Use to identify the agent(s) on which the action is performed.
        :param mac_address: {str} The MAC address of the managed product agent. Use to identify the agent(s) on which the action is performed.
        :return:
        """
        payload = {"act": "cmd_isolate_agent", "allow_multiple_match": True}
        if not any([ip_address, host_name, mac_address]):
            raise TrendMicroApexCentralValidationError(
                "Endpoint isolation requires IP address, Hostname or Mac address to be provided"
            )

        if ip_address:
            payload["ip_address"] = ip_address
        if host_name:
            payload["host_name"] = host_name
        if mac_address:
            payload["mac_address"] = mac_address
        response = self._make_request(
            http_method="POST",
            request_api_endpoint=ENDPOINTS["isolate_endpoint"],
            body=payload,
        )
        self.validate_response(
            response,
            error_msg=f"Failed to request isolation of endpoint {ip_address or host_name or mac_address}",
        )

    def unisolate_endpoint(
        self,
        ip_address: Optional[str] = None,
        host_name: Optional[str] = None,
        mac_address: Optional[str] = None,
    ):
        """
        Restore connection: Restores network connectivity to an isolated endpoint
        :param ip_address: {str} The IP address of the managed product agent. Use to identify the agent(s) on which the action is performed.
        :param host_name: {str} The endpoint name of the managed product agent. Use to identify the agent(s) on which the action is performed.
        :param mac_address: {str} The MAC address of the managed product agent. Use to identify the agent(s) on which the action is performed.
        """
        payload = {"act": "cmd_restore_isolated_agent", "allow_multiple_match": True}
        if not any([ip_address, host_name, mac_address]):
            raise TrendMicroApexCentralValidationError(
                "Endpoint unisolation requires IP address, Hostname or Mac address to be provided"
            )

        if ip_address:
            payload["ip_address"] = ip_address
        if host_name:
            payload["host_name"] = host_name
        if mac_address:
            payload["mac_address"] = mac_address
        response = self._make_request(
            http_method="POST",
            request_api_endpoint=ENDPOINTS["unisolate_endpoint"],
            body=payload,
        )
        self.validate_response(
            response,
            error_msg=f"Failed to request unisolation of endpoint {ip_address or host_name or mac_address}",
        )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response for status code
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()
                if response.status_code == AUTHORIZATION_ERROR_STATUS_CODE:
                    raise TrendMicroApexCentralAuthorizationError(
                        f"{error_msg}: {TrendMicroApexCentralParser.extract_api_error_message(response.json())}"
                    )

                raise TrendMicroApexCentralManagerError(
                    f"{error_msg}: {error} {TrendMicroApexCentralParser.extract_api_error_message(response.json())}"
                )

            except (
                TrendMicroApexCentralManagerError,
                TrendMicroApexCentralAuthorizationError,
            ):
                raise

            except:
                raise TrendMicroApexCentralManagerError(
                    f"{error_msg}: {error} - {response.text}"
                )
