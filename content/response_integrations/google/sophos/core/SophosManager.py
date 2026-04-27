from __future__ import annotations
from typing import Any
import json
import urllib.parse
import requests
from .constants import (
    ISOLATED,
    ISOLATION_IN_PROGRESS,
    LIMIT_PER_REQUEST,
    LIMIT_PER_REQUEST_LATEST,
    UNISOLATED,
)
from .SophosExceptions import SophosManagerError, HashAlreadyOnBlocklist
from .SophosParser import SophosParser
from .utils import validate_api_response

# Consult with Roi - Python 2
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import SiemplifySession  # TIP The Package
from TIPCommon import filter_old_alerts  # TIP The Module

# ============================== CONSTS ===================================== #

API_ROOT = "https://id.sophos.com"
MULTI_AUTH_INDICATOR_KEY = "mfa_required"
LIMIT = 10000
EVENTS_LIMIT = 1000
KNOWN_SERVICES_STATUSES = {"2": "Missing", "0": "OK"}

# ============================= CLASSES ===================================== #


ENDPOINTS = {
    "get_alerts": "/gateway/siem/v1/alerts",
    "get_alerts_latest": "/siem/v1/alerts",
    "get_api_root": "/whoami/v1",
    "test_connectivity": "/endpoint/v1/endpoints",
    "test_siem_connectivity": "/gateway/siem/v1/events",
    "initiate_scan": "/endpoint/v1/endpoints/{scan_id}/scans",
    "find_entities": "/endpoint/v1/endpoints",
    "check_isolation_status": "/endpoint/v1/endpoints/{endpoint_id}/isolation",
    "isolate_endpoint": "/endpoint/v1/endpoints/isolation",
    "get_alert_actions": "/common/v1/alerts/{alert_id}",
    "execute_alert_action": "/common/v1/alerts/{alert_id}/actions",
    "get_blocked_items": "/endpoint/v1/settings/blocked-items",
    "add_to_blocklist": "/endpoint/v1/settings/blocked-items",
    "add_to_allowlist": "/endpoint/v1/settings/allowed-items",
}

FILTER_ENTITY_TYPES = {
    EntityTypes.HOSTNAME: "hostnameContains",
    EntityTypes.ADDRESS: "ipAddresses",
}


class EndpointTypes:
    SERVER = "server"
    COMPUTER = "computer"


class SophosManager:
    def __init__(
        self,
        api_root=None,
        client_id=None,
        client_secret=None,
        verify_ssl=False,
        siem_api_root=None,
        api_key=None,
        api_token=None,
        siemplify=None,
        test_connectivity=False,
    ):
        """
        Connect to Sophos
        """
        self.api_root = self._get_adjusted_root_url(api_root)
        self.verify_ssl = verify_ssl
        self.sensitive_data = [
            sd for sd in [client_id, client_secret, api_key, api_token] if sd
        ]
        self.session = SiemplifySession(sensitive_data_arr=self.sensitive_data)
        self.session.verify = self.verify_ssl
        self.parser = SophosParser()
        self.siemplify = siemplify
        self.login(client_id, client_secret, verify_ssl)
        if test_connectivity:
            self.test_connectivity()
        if siem_api_root or api_key or api_token:
            self.api_key = api_key
            self.api_token = api_token
            self.siem_api_root = self._get_adjusted_root_url(siem_api_root)
            if test_connectivity:
                self.test_siem_connectivity()

    @staticmethod
    def _get_adjusted_root_url(api_root):
        if api_root:
            return api_root[:-1] if api_root.endswith("/") else api_root
        raise SophosManagerError(
            '"SIEM API Root" parameter is required when "API Key" or "Base 64 Auth Payload" provided'
        )

    def login(self, client_id, client_secret, verify_ssl):
        """
        Set session headers, get API root and fetch cookies.
        :param client_id: {string} Client id
        :param client_secret: {string} Client Secret
        :param verify_ssl: {bool} Use SSL on HTTP request
        :return: {void}
        """
        url = f"{API_ROOT}/api/v2/oauth2/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "token",
        }

        response = requests.post(url=url, data=data, verify=verify_ssl)

        self.validate_response(response, "Unable to login. Check your credentials.")

        if MULTI_AUTH_INDICATOR_KEY in list(response.json().keys()):
            raise SophosManagerError(
                "Multi-factor Authentication(MFA) is enabled. Disable it or login "
                "with different user."
            )

        # Set Sophos headers for authentication
        token = self.parser.get_acces_token(response.json())
        self.session.headers = {"Authorization": f"Bearer {token}"}
        self.session.cookies = response.cookies
        url = f"{self.api_root}/whoami/v1"
        response = self.session.get(url)
        self.validate_response(
            response,
            "Unable to login. Check your credentials.",
            test_response_json=True,
        )
        # Get new API ROOT (region based)
        api_root_details = self.parser.build_api_root_details_obj(response.json())
        self.session.headers.update({"X-Tenant-ID": api_root_details.id})
        self.api_root = api_root_details.api_root

    def test_connectivity(self):
        params = {"pageSize": 1}
        response = self.session.get(
            url=self._get_full_url("test_connectivity"), params=params
        )
        self.validate_response(
            response, error_msg="Unable to connect to Sophos", test_response_json=True
        )

        return True

    def test_siem_connectivity(self):
        session = SiemplifySession(sensitive_data_arr=self.sensitive_data)
        session.verify = self.verify_ssl
        self._update_session_headers(session.headers)
        params = {"limit": LIMIT_PER_REQUEST_LATEST}

        url = f"{self.siem_api_root}/siem/v1/events"
        response = session.get(url=url, params=params)
        self.validate_response(
            response, error_msg="Unable to connect to Sophos", test_response_json=True
        )

        return True

    def _update_session_headers(
        self,
        session_headers: dict[str, Any],
    ) -> None:
        if self.api_key and self.api_token:
            session_headers.update(
                {"Authorization": f"Basic {self.api_token}", "x-api-key": self.api_key}
            )

        elif "Bearer" in self.session.headers.get("Authorization", ""):
            session_headers.update(
                {
                    "Authorization": self.session.headers["Authorization"],
                    "X-Tenant-ID": self.session.headers["X-Tenant-ID"],
                }
            )

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urllib.parse.urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a request
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

        params.update({"limit": max(limit, LIMIT_PER_REQUEST)})

        response = self.session.request(method, url, params=params, json=body)

        validate_api_response(response, err_msg)
        results = response.json().get("items", [])
        has_more = response.json().get("has_more", False)
        next_cursor = response.json().get("next_cursor", "")

        while has_more:
            params.update({"cursor": next_cursor})

            response = self.session.request(method, url, params=params, json=body)
            validate_api_response(response, err_msg)
            has_more = response.json().get("has_more", False)
            next_cursor = response.json().get("next_cursor", "")
            results.extend(response.json().get("items", []))

        return results

    def get_alerts(self, existing_ids, limit, start_time):
        """
        Get alerts
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_time: {int} The start timestamp from where to fetch
        :return: {list} The list of filtered Alert objects
        """
        request_url = self._get_full_url("get_alerts")
        params = {"from_date": str(start_time)[:-3]}
        alerts = self.parser.build_alerts_list(
            self._paginate_results(
                method="GET", url=request_url, params=params, limit=limit
            )
        )

        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key="id",
        )
        return sorted(filtered_alerts, key=lambda alert: alert.when)[:limit]

    def get_all_computers(self):
        """
        Get all endpoints
        :return: {list} List of endpoints (dicts)
        """
        return self.get_all_endpoints_by_type(EndpointTypes.COMPUTER)

    def get_all_endpoints_by_type(self, endpoint_type):
        """
        Get all endpoints by a given type (Computer / Server)
        :param endpoint_type: {str} The type of the endpoints to fetch
        :return: {list} The found endpoints
        """
        url = f"{self.api_root}/user-devices/v1/bulk-endpoints"

        response = self.session.get(
            url=url,
            params={
                "endpoint_type": endpoint_type,
                "limit": LIMIT,
                "get_health_status": True,
            },
        )

        self.validate_response(
            response, f"Unable to list endpoints of type {endpoint_type}"
        )
        endpoints_info = response.json().get("endpoints", [])
        columns = response.json().get("columns", [])

        endpoints = []

        # Match endpoint values with endpoint columns
        for endpoint in endpoints_info:
            endpoints.append(
                {
                    full_key: endpoint[columns[full_key]]
                    for full_key, key in list(columns.items())
                }
            )

        for endpoint in endpoints:
            endpoint["endpoint_type"] = endpoint_type

        return endpoints

    def get_all_endpoints(self):
        return self.get_all_servers() + self.get_all_computers()

    def get_all_servers(self):
        """
        Get all endpoints
        :return: {list} List of endpoints (dicts)
        """
        return self.get_all_endpoints_by_type(EndpointTypes.SERVER)

    def get_server(self, server_id):
        """
        Get a server by ID
        :param server_id: {str} The id of the server
        :return: {dict} The server info
        """
        url = f"{self.api_root}/servers/{server_id}"

        response = self.session.get(url=url)

        self.validate_response(response, f"Unable to get server {server_id}")
        return response.json()

    def get_computer(self, computer_id):
        """
        Get a computer by its ID
        :param computer_id: {str} The computer id
        :return: {dict} The found computer info
        """
        url = f"{self.api_root}/user-devices/{computer_id}"

        response = self.session.get(url=url)

        self.validate_response(
            response,
            f"Unable to get computer {computer_id}"
        )
        return response.json()

    def get_endpoint_by_ip(self, ip):
        """
        Get endpoint by ip
        :param ip: {str} The ip to filter by
        :return: {dict} The found endpoint
        """
        # Retrieve all endpoints and filter them (no filtering available in api)
        endpoints = self.get_all_endpoints()

        for endpoint in endpoints:
            if ip in endpoint.get("INFO_IP_V4", []):
                return endpoint

    def get_endpoint_by_name(self, name):
        """
        Get endpoint by name
        :param name: {str} The name to filter by
        :return: {dict} The found endpoint
        """
        # Retrieve all endpoints and filter them (no filtering available in api)
        endpoints = self.get_all_endpoints()

        for endpoint in endpoints:
            if endpoint.get("LABEL", "").lower() == name.lower():
                return endpoint

    def get_endpoint_by_hostname(self, hostname):
        """
        Get endpoint by hostname
        :param hostname: {str} The hostname to filter by
        :return: {dict} The found endpoint
        """
        # Retrieve all endpoints and filter them (no filtering available in api)
        endpoints = self.get_all_endpoints()

        for endpoint in endpoints:
            if endpoint.get("COMPUTER_NAME", "").lower() == hostname.lower():
                return endpoint

    def get_events_by_endpoint(self, endpoint_id, since=None, limit=None):
        """
        Get events log of an endpoint
        :param endpoint_id: {str} The endpoint's id
        :return: {list} List of events (dicts)
        """
        session = self._get_siem_session()
        limit = max(limit, LIMIT_PER_REQUEST_LATEST)
        api_root = getattr(self, "siem_api_root", None) or self.api_root
        url = f"{api_root}/siem/v1/events"

        params = {"endpoint": endpoint_id, "from_date": since, "limit": limit}

        params = {
            key: value for key, value in list(params.items()) if value is not None
        }
        results, cursor, response = [], None, None

        while True:
            if response:
                if not cursor or (limit and len(results) > limit):
                    break
                params.update({"cursor": cursor})

            response = session.get(url=url, params=params)
            self.validate_response(
                response, f"Unable to get events of endpoint {endpoint_id}"
            )

            results.extend(
                self.parser.build_results(
                    raw_json=response.json(), method="build_event_obj", data_key="items"
                )
            )
            if not self.parser.has_endpoint_more_events(response.json()):
                break
            cursor = self.parser.get_next_cursor(response.json())

        return results[:limit] if limit else results

    def _get_siem_session(self) -> requests.Session:
        if not hasattr(self, "siem_api_root"):
            return self.session

        session = SiemplifySession(sensitive_data_arr=self.sensitive_data)
        session.verify = self.verify_ssl
        self._update_session_headers(session.headers)

        return session

    def get_computer_services(self, computer_id):
        """
        Get services statuses of an computer
        :param computer_id: {str} The computer_id's id
        :return: {dict} The services statuses
        """
        url = f"{self.api_root}/user-devices/{computer_id}"

        response = self.session.get(url=url, params={"get_health_status": True})

        self.validate_response(
            response, f"Unable to list services of computer {computer_id}"
        )
        services = response.json().get("status", {}).get(r"shs/service/detail", {})

        # Replace numeric statuses with human readable statuses
        for key, value in list(services.items()):
            if value in list(KNOWN_SERVICES_STATUSES.keys()):
                services[key] = KNOWN_SERVICES_STATUSES[value]

        return services

    def get_server_services(self, server_id):
        """
        Get services statuses of an server
        :param server_id: {str} The server's id
        :return: {dict} The services statuses
        """
        url = f"{self.api_root}/servers/{server_id}"

        response = self.session.get(url=url, params={"get_health_status": True})

        self.validate_response(
            response, f"Unable to list services of server {server_id}"
        )
        services = response.json().get("status", {}).get(r"shs/service/detail", {})

        # Replace numeric statuses with human readable statuses
        for key, value in list(services.items()):
            if value in list(KNOWN_SERVICES_STATUSES.keys()):
                services[key] = KNOWN_SERVICES_STATUSES[value]

        return services

    def validate_response(
        self, response, error_msg="An error occurred", test_response_json=False
    ):
        try:
            if response.status_code == 409:
                raise HashAlreadyOnBlocklist("Resource already exists.")

            response.raise_for_status()

        except HashAlreadyOnBlocklist:
            raise
        except requests.HTTPError as error:
            raise SophosManagerError(
                self.session.encode_sensitive_data(
                    f"{error_msg}: {error} - {response.content}"
                )
            )
        if test_response_json:
            try:
                response.json()
            except Exception as error:
                raise SophosManagerError(
                    error_msg, self.session.encode_sensitive_data(error)
                )

    def find_entities(self, entity_identifier, entity_type):
        """
        Get endpoint by entity_identifier
        :param entity_identifier: {str} The entity identifier to filter by
        :param entity_type: {str} The entity type to filter by
        :return: {dict} The found endpoint
        """
        params = {FILTER_ENTITY_TYPES[entity_type]: entity_identifier}
        response = self.session.get(
            self._get_full_url("test_connectivity"), params=params
        )
        self.validate_response(
            response, f"Unable to find endpoint for entity {entity_identifier}"
        )

        endpoints = self.parser.build_results(
            raw_json=response.json(), method="build_endpoint_obj", data_key="items"
        )
        return self.get_filtered_endpoint(endpoints, entity_type, entity_identifier)

    def add_hash_to_blocklist(self, hash_entity, comment):
        """
        Function that adds hashes to the blocklist
        :param hash_entity: {str} The hash entity that should be added to a blocklist
        :param comment: {str} Comment to add
        """
        payload = json.dumps(
            {
                "type": "sha256",
                "properties": {"sha256": hash_entity},
                "comment": comment,
            }
        )
        response = self.session.post(
            self._get_full_url("add_to_blocklist"), data=payload
        )
        self.validate_response(
            response, f"Unable to add hash {hash_entity} to blocklist."
        )

    def add_hash_to_allowlist(self, hash_entity, comment):
        """
        Function that adds hashes to the allowlist
        :param hash_entity: {str} The hash entity that should be added to a allowlist
        :param comment: {str} Comment to add
        """
        payload = json.dumps(
            {
                "type": "sha256",
                "properties": {"sha256": hash_entity},
                "comment": comment,
            }
        )
        response = self.session.post(
            self._get_full_url("add_to_allowlist"), data=payload
        )
        self.validate_response(
            response, f"Unable to add hash {hash_entity} to allowlist."
        )

    def get_filtered_endpoint(self, endpoints, entity_type, entity_identifier):
        """
        Filter endpoint by entity_identifier
        :param endpoints: {str} The endpoints for given entity identifier
        :param entity_identifier: {str} The entity identifier to filter by
        :param entity_type: {str} The entity type to filter by
        :return: {dict} The found endpoint
        """
        for endpoint in endpoints:
            if (
                entity_type == EntityTypes.HOSTNAME
                and endpoint.hostname.lower() == entity_identifier.lower()
            ):
                return endpoint
            elif (
                entity_type == EntityTypes.ADDRESS
                and entity_identifier in endpoint.ip_address
            ):
                return endpoint

        return None

    def scan_endpoint(self, scan_id):
        """
        Initiate scan on an endpoint
        :param scan_id: The endpoint to scan
        :return {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("initiate_scan", scan_id=scan_id)
        payload = {}

        response = self.session.post(request_url, json=payload)
        self.validate_response(response, f"Unable to scan endpoint {scan_id}")

        return True

    def check_isolation_status(self, endpoint_id):
        """
        Check isolation status on an endpoint
        :param endpoint_id: The endpoint id
        :return {str} Isolation status
        """
        request_url = self._get_full_url(
            "check_isolation_status", endpoint_id=endpoint_id
        )
        response = self.session.get(request_url)
        self.validate_response(response)

        response_json = response.json()

        enabled: bool = response_json.get("enabled")
        if enabled is True:
            return ISOLATED

        if enabled is False:
            return UNISOLATED

        return ISOLATION_IN_PROGRESS

    def isolate_or_unisolate_endpoint(self, isolate, endpoint_id, comment):
        """
        Isolate or Unisolate the endpoint
        :param isolate: {bool} If True, will isolate, otherwise unisolate
        :param endpoint_id: {str} The id of the endpoint to isolate/unisolate
        :param comment: {str} Comment explaining the need of isolation/unisolation.
        :return {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("isolate_endpoint")
        payload = {"enabled": isolate, "ids": [endpoint_id], "comment": comment}
        response = self.session.post(request_url, json=payload)
        self.validate_response(response)

    def get_alert_actions(self, alert_id):
        """
        Get alert actions
        :param alert_id: The alert id
        :return {list}
        """
        request_url = self._get_full_url("get_alert_actions", alert_id=alert_id)
        response = self.session.get(request_url)

        if response.status_code == 400:
            raise Exception(response.json().get("message"))
        elif response.status_code == 404:
            raise Exception(f"alert with ID {alert_id} was not found in Sophos")
        self.validate_response(response)

        return response.json().get("allowedActions", [])

    def execute_alert_action(self, alert_id, action, message):
        """
        Execute alert action
        :param alert_id: {str} The alert id
        :param action: {str} Action to execute
        :param message: {str} Message explaining the reason
        :return {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("execute_alert_action", alert_id=alert_id)
        payload = {"action": action, "message": message}
        response = self.session.post(request_url, json=payload)

        if response.status_code == 400:
            raise Exception(
                "Invalid action was provided for the alert. Please check what actions are available for "
                'the provided alert with action "List Alert Actions".'
            )
        elif response.status_code == 404:
            raise Exception(f"alert with ID {alert_id} was not found in Sophos")
        self.validate_response(response)

    def get_blocked_items(self, entity_identifier):
        """
        Get alert actions
        :param entity_identifier: The entity identifier
        :return {FileHash}
        """
        request_url = self._get_full_url("get_blocked_items")
        response = self.session.get(request_url)
        self.validate_response(response)

        hashes = self.parser.build_results(
            raw_json=self._paginate_results_for_different_api(
                method="GET", url=request_url
            ),
            method="build_hash_obj",
            pure_data=True,
        )
        return self.get_filtered_hash(hashes, entity_identifier)

    def get_filtered_hash(self, hashes, entity_identifier):
        """
        Filter hash by entity_identifier
        :param hashes: {list} The hashes for given entity identifier
        :param entity_identifier: {str} The entity identifier to filter by
        :return: {FileHash} The found Hash object
        """
        for filehash in hashes:
            if filehash.hash_value.lower() == entity_identifier.lower():
                return filehash

    def _paginate_results_for_different_api(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a request
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

        page_number = 1
        params.update(
            {"pageSize": LIMIT_PER_REQUEST, "pageTotal": True, "page": page_number}
        )

        response = self.session.request(method, url, params=params, json=body)

        self.validate_response(response, err_msg)
        results = response.json().get("items", [])
        total_items = response.json().get("pages", {}).get("items")

        while total_items > len(results):
            page_number += 1
            params.update({"page": page_number})

            response = self.session.request(method, url, params=params, json=body)
            self.validate_response(response, err_msg)
            total_items = response.json().get("pages", {}).get("items")
            results.extend(response.json().get("items", []))

        return results


class SophosManagerForConnector(SophosManager):
    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        verify_ssl: bool = False,
        api_root: str = "",
        api_key: str = "",
        api_token: str = "",
        siemplify: SiemplifySession = None,
    ) -> None:
        """
        Connect to Sophos
        """
        self.api_root = self._get_adjusted_root_url(api_root)
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.parser = SophosParser()
        self.siemplify = siemplify
        self.endpoints = ENDPOINTS.copy()
        self.use_client_auth = client_id and client_secret
        if self.use_client_auth:
            self.login(client_id, client_secret, verify_ssl)
            self.endpoints["get_alerts"] = self.endpoints["get_alerts_latest"]

        if not self.use_client_auth and api_key and api_token:
            self.api_root = api_root
            self.session.headers.update(
                {"Authorization": f"Basic {api_token}", "x-api-key": api_key}
            )

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urllib.parse.urljoin(
            self.api_root, self.endpoints[url_id].format(**kwargs)
        )

    def get_alerts(self, existing_ids, limit, start_time):
        """
        Get alerts
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_time: {int} The start timestamp from where to fetch
        :return: {list} The list of filtered Alert objects
        """
        request_url = self._get_full_url("get_alerts")
        params = {"from_date": str(start_time)[:-3]}
        alerts = self.parser.build_alerts_list(
            self._paginate_results(
                method="GET", url=request_url, params=params, limit=limit
            )
        )

        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key="id",
        )
        return sorted(filtered_alerts, key=lambda alert: alert.when)[:limit]

    def validate_response(
        self,
        response: requests.Response,
        error_msg: str = "An error occurred",
        test_response_json: bool = False,
    ) -> None:
        """Validate the response.

        Args:
            response (requests.Response): Response from API
            error_msg (str): Error message. Defaults to "An error occurred".
            test_response_json (bool): Checks for test response. Defaults to False.

        Raises:
            SophosManagerError: Raises in case of exception.
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            # Not a JSON - return content
            raise SophosManagerError(f"{error_msg}: {error} - {response.content}")

        if test_response_json:
            try:
                response.json()
            except Exception as error:
                raise SophosManagerError(
                    error_msg, self.session.encode_sensitive_data(error)
                ) from error

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a request
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
        default_limit: int = (
            LIMIT_PER_REQUEST if not self.use_client_auth else LIMIT_PER_REQUEST_LATEST
        )
        params.update({"limit": max(limit, default_limit)})

        response = self.session.request(method, url, params=params, json=body)

        validate_api_response(response, err_msg)
        results = response.json().get("items", [])
        has_more = response.json().get("has_more", False)
        next_cursor = response.json().get("next_cursor", "")

        while has_more:
            params.update({"cursor": next_cursor})

            response = self.session.request(method, url, params=params, json=body)
            validate_api_response(response, err_msg)
            has_more = response.json().get("has_more", False)
            next_cursor = response.json().get("next_cursor", "")
            results.extend(response.json().get("items", []))

        return results
