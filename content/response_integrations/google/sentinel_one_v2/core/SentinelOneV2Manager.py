from __future__ import annotations

from typing import TYPE_CHECKING

import copy
import datetime
import urllib.parse
import requests
from sentinel_one_v2.core.SentinelOneV2Parser import SentinelOneV2Parser
from TIPCommon.base.utils import CreateSession
from sentinel_one_v2.core.exceptions import (
    SentinelOneV2UnauthorizedError,
    SentinelOneV2HTTPError,
    SentinelOneV2ConnectivityError,
    SentinelOneV2PermissionError,
    SentinelOneV2NotFoundError,
    SentinelOneV2AlreadyExistsError,
    SentinelOneV2BadRequestError,
    SentinelOneV2TooManyRequestsError,
)
from sentinel_one_v2.core.utils import filter_items

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

    from sentinel_one_v2.core.datamodels import Agent

COMPLETED_QUERY_STATUSES = [
    "FAILED",
    "FINISHED",
    "ERROR",
    "QUERY_CANCELLED",
    "TIMED_OUT",
]
FAILED_QUERY_STATUSES = ["FAILED", "ERROR", "QUERY_CANCELLED", "TIMED_OUT"]

DEEP_VISIBILITY_QUERY_FINISHED = "FINISHED"
DEEP_VISIBILITY_QUERY_RUNNING = "RUNNING"
ALREADY_EXISTS_ERROR_CODE = 4000030
BAD_REQUEST_ERROR_CODE = 400
UNAUTHORIZED_ERROR_CODE = 401
NOT_FOUND_ERROR_CODE = 404
FORBIDDEN_ERROR_CODE = 403
TOO_MANY_REQUESTS_ERROR_CODE = 429
ALREADY_EXISTS_ERROR_TEXT = "already exists"
MAXIMUM_EVENTS_ALLOWED = 1000
DEFAULT_PAGE_SIZE = 25
HASH_TYPE_STRING = "white_hash"
CREATED_BY_SIEMPLIFY_STRING = "Created by Siemplify."
DEFAULT_THREATS_LIMIT = 10
BLACK_HASH_TYPE_STRING = "black_hash"
PATH_TYPE_STRING = "path"
# Time Formats.
FETCH_EVENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
FETCH_THREATS_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000000Z"

API_ENDPOINTS = {
    "ping": "/web/api/v{api_version}/agents/count",
    "system_status": "/web/api/v{api_version}/system/status",
    "db_system_status": "/web/api/v{api_version}/system/status/db",
    "cache_server_system_status": "/web/api/v{api_version}/system/status/cache",
    "system_info": "/web/api/v{api_version}/system/info",
    "create_hash_blacklist_url": "/web/api/v{api_version}/restrictions",
    "create_exclusions_url": "/web/api/v{api_version}/exclusions",
    "mitigate_threat": "/web/api/v{api_version}/threats/mitigate/{action}",
    "threats": "/web/api/v{api_version}/threats",
    "agents": "/web/api/v{api_version}/agents",
    "resolve_threats": "/web/api/v{api_version}/threats/mark-as-resolved",
    "deep_visibility_query_events": "/web/api/v{api_version}/dv/events",
    "deep_visibility_query_status": "/web/api/v{api_version}/dv/query-status",
    "initiate_full_scan_url": "/web/api/v{api_version}/agents/actions/initiate-scan",
    "init_query": "/web/api/v{api_version}/dv/init-query",
    "disconnect_agent_from_network": "/web/api/v{api_version}/agents/actions/disconnect",
    "blacklist": "/web/api/v{api_version}/restrictions",
    "connect_agent_to_the_network": "/web/api/v{api_version}/agents/actions/connect",
    "groups": "/web/api/v{api_version}/groups",
    "get_agent_applications_url": "/web/api/v{api_version}/agents/applications",
    "hash_reputation": "/web/api/v{api_version}/hashes/{hash}/reputation",
    "query_url": "/web/api/v{api_version}/dv/init-query",
    "query_status": "/web/api/v{api_version}/dv/query-status",
    "file_events": "/web/api/v{api_version}/dv/events/file",
    "indicator_events": "/web/api/v{api_version}/dv/events/indicators",
    "dns_events": "/web/api/v{api_version}/dv/events/dns",
    "network_actions_events": "/web/api/v{api_version}/dv/events/ip",
    "url_events": "/web/api/v{api_version}/dv/events/url",
    "registry_events": "/web/api/v{api_version}/dv/events/registry",
    "scheduled_task_events": "/web/api/v{api_version}/dv/events/scheduled_task",
    "process_events": "/web/api/v{api_version}/dv/events/process",
    "query_status_url": "/web/api/v{api_version}/dv/query-status",
    "delete_hash_blacklist_url": "/web/api/v{api_version}/restrictions",
    "sites": "/web/api/v{api_version}/sites",
    "threat_events": "/web/api/v2.1/threats/{threat_id}/explore/events",
}

# Payloads.
LOGIN_PAYLOAD = {"username": "", "rememberMe": "true", "password": ""}

INITIATE_FULL_SCAN_PAYLOAD = {"filter": {"uuid": ""}, "data": {}}

CREATE_PATH_EXCLUSION_PAYLOAD = {
    "filter": {},
    "data": {
        "value": "",
        "osType": "windows",  # Cam be:  windows, windows_legacy, macos or linux
        "type": "path",
        "description": "Created by Siemplify.",
    },
}

GET_AGENT_APPLICATIONS_PARAMS = GET_AGENT_PROCESSES_PARAMS = {"ids": ""}

GET_EVENTS_BY_DATE_PARAMS = {
    "query": "",
    "fromDate": "2017-11-06T19:11:00.000Z",
    "toDate": "2017-11-07T19:11:00.000Z",
    "limit": 10,
}

GET_THREATS_PARAMS = {
    "resolved": False,
    "createdAt__gt": "2018-02-27T04:49:26.257525Z",
    "sortOrder": "asc",
    "sortBy": "createdAt",
}

GET_SYSTEM_INFO_PARAMS = {"uuids": ""}

# Headers.
HEADERS = {"Content-Type": "application/json"}


class SentinelOneV2Manager:
    def __init__(
        self,
        api_root,
        api_token,
        api_version,
        verify_ssl=False,
        force_check_connectivity=False,
        logger=None,
    ):
        """
        :param api_root: API root URL.
        :param api_token: SentinelOne api token
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL certificate for the connection.
        :param force_check_connectivity: True or False. If True it will check connectivity initially.
        :param logger: Siemplify logger.
        """
        self.api_root = api_root
        self.session = CreateSession.create_session()
        self.session.verify = verify_ssl
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Authorization"] = f"ApiToken {api_token}"
        self.parser = SentinelOneV2Parser()
        self.logger = logger
        self.api_version = api_version
        self.api_endpoints = API_ENDPOINTS

        if force_check_connectivity:
            self.test_connectivity()

    def _get_full_url(self, url_id, with_api_version=True, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param api_version: {str or float}
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urllib.parse.urljoin(
            self.api_root,
            (
                self.api_endpoints[url_id].format(
                    api_version=self.api_version, **kwargs
                )
                if with_api_version
                else self.api_endpoints[url_id].format(**kwargs)
            ),
        )

    def test_connectivity(self):
        """
        Test connectivity to SentinelOne V2
        :return: {bool} True if successful, exception otherwise
        """
        try:
            response = self.session.get(self._get_full_url("ping"))
            self.validate_response(response)
            return True
        except Exception as e:
            raise SentinelOneV2ConnectivityError(
                f"Unable to connect to SentinelOne V2. Error: {e}"
            )

    @classmethod
    def get_api_error_message(cls, exception, for_threat_events=False):
        """
        Get API error message
        :param exception: {Exception} The api error
        :param for_threat_events: {bool} Special message for Threat Events
        :return: {str} error message
        """
        try:
            error = exception.response.json().get("errors")[0]
            if for_threat_events:
                return f"{error.get('title', '')}. {error.get('detail', '')}."
            return error.get("detail", "") or error.get("title", "")
        except:
            return exception.response.content.decode()

    @classmethod
    def validate_response(
        cls, response, error_msg="An error occurred", for_threat_events=False
    ):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        :param for_threat_events: {bool} Special message for Threat Events
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            error_message = cls.get_api_error_message(
                error, for_threat_events=for_threat_events
            )

            if (
                ALREADY_EXISTS_ERROR_TEXT in str(error_message).lower()
                or response.status_code == ALREADY_EXISTS_ERROR_CODE
            ):
                raise SentinelOneV2AlreadyExistsError(error_message)
            if response.status_code == UNAUTHORIZED_ERROR_CODE:
                raise SentinelOneV2UnauthorizedError(
                    "API token is invalid or expired. Immediately update it!"
                )
            if response.status_code == BAD_REQUEST_ERROR_CODE:
                raise SentinelOneV2BadRequestError(error_message)
            if response.status_code == FORBIDDEN_ERROR_CODE:
                raise SentinelOneV2PermissionError(
                    f"{error_msg}: {'Permissions are insufficient.'} {response.content}"
                )
            if response.status_code == ALREADY_EXISTS_ERROR_CODE:
                raise SentinelOneV2AlreadyExistsError()

            if response.status_code == NOT_FOUND_ERROR_CODE:
                raise SentinelOneV2NotFoundError(error)
            if response.status_code == TOO_MANY_REQUESTS_ERROR_CODE:
                raise SentinelOneV2TooManyRequestsError("rate limit was reached.")

            raise SentinelOneV2HTTPError(f"{error_msg}: {error} {response.content}")

    def get_agent_by_hostname(self, hostname):
        """
        Get agent by hostname
        :param hostname: {unicode} Hostname (computer name) to filter agents by
        :return: {Agent} Matching agent
        """
        params = {"computerName": hostname}
        agents = self._paginate_results(
            method="GET",
            url=self._get_full_url("agents"),
            params=params,
            err_msg=f"Unable to get agents with hostname {hostname}",
        )

        agents = self.parser.build_results(
            agents, "build_siemplify_agent_obj", pure_data=True
        )

        if not agents:
            raise SentinelOneV2NotFoundError(
                f"Agent with hostname {hostname} was not found"
            )

        return agents[-1]

    def get_agent_by_uuid(self, agent_uuid):
        """
        Get agent by agent_uuid
        :param agent_uuid: {str} The UUID of the agent
        :return: {Agent} Matching agent
        """
        params = {"uuids": agent_uuid}
        agents = self._paginate_results(
            method="GET",
            url=self._get_full_url("agents"),
            params=params,
            err_msg=f"Unable to get agents with uuid {agent_uuid}",
        )

        agents = self.parser.build_results(
            agents, "build_siemplify_agent_obj", pure_data=True
        )

        if not agents:
            raise SentinelOneV2NotFoundError(
                f"Agent with UUID {agent_uuid} was not found"
            )

        return agents[0]

    def get_agent_by_ip(self, ip_address: str) -> Agent:
        """
        Get agents by IP address

        Args:
            ip_address(str): IP to filter agents by.

        Returns:
            Agent: Matching agent, with ip address.
        """
        params: dict[str, str] = {"networkInterfaceInet__contains": ip_address}

        agents_data: list[SingleJson] = self._paginate_results(
            method="GET",
            url=self._get_full_url("agents"),
            params=params,
            err_msg=f"Unable to get agents with IP {ip_address}",
        )

        agents: list[Agent] = self.parser.build_results(
            agents_data,
            "build_siemplify_agent_obj",
            pure_data=True,
        )

        if not agents:
            raise SentinelOneV2NotFoundError(
                f"Agent with IP {ip_address} was not found"
            )

        return agents[-1]

    def disconnect_agent_from_network(self, agent_id):
        """
        Disconnect agent from the network.
        :param agent_id: {str} Agent ID.
        :return: {bool} True if succeed.
        """
        payload = {"filter": {"ids": [agent_id]}, "data": {}}

        response = self.session.post(
            self._get_full_url("disconnect_agent_from_network"), json=payload
        )
        self.validate_response(response)

        return True

    def reconnect_agent_to_network(self, agent_id):
        """
        Connect endpoint to the network.
        :param agent_id: {str} Agent ID.
        :return: {bool} is succeed
        """
        payload = {"filter": {"ids": [agent_id]}, "data": {}}

        response = self.session.post(
            self._get_full_url("connect_agent_to_the_network"), json=payload
        )
        self.validate_response(response)

        return True

    def get_agent_status(self, agent_uuid):
        """
        Get agent's status.
        :param agent_uuid: {str} endpoint agent uuid
        :return: {bool} value of Agent object's is_active property
        """
        agent = self.get_agent_by_uuid(agent_uuid)

        return agent.is_active

    def get_applications_from_endpoint(self, agent_id, limit=None):
        """
        Get applications list for an agent.
        :param agent_id: {str} Agent ID.
        :param limit: {str} count for applications
        :return: {list} list of application objects.
        """
        params = {"ids": agent_id}
        response = self.session.get(
            self._get_full_url("get_agent_applications_url"), params=params
        )
        self.validate_response(response)

        return self.parser.build_results(
            response.json(), "build_application_object", limit=limit
        )

    def get_hash_reputation(self, file_hash):
        """
        Get file hash reputation.
        :param file_hash: {str} file hash.
        :return: {str} file hash reputation data.
        """
        response = self.session.get(
            self._get_full_url("hash_reputation", hash=file_hash)
        )
        self.validate_response(response)

        return self.parser.build_hash_obj(response.json())

    def get_system_status(self):
        """
        Returns current system health status.
        :return: {SystemStatus} The system status obj
        """
        response = self.session.get(self._get_full_url("system_status"))
        self.validate_response(response)

        return self.parser.build_siemplify_system_status_obj(response.json())

    def get_db_system_status(self):
        """
        Returns current DB system health status.
        :return: {SystemStatus} The system status obj
        """
        response = self.session.get(self._get_full_url("db_system_status"))
        self.validate_response(response)

        return self.parser.build_siemplify_system_status_obj(response.json())

    def get_cache_server_system_status(self):
        """
        Returns current cache server system health status.
        :return: {SystemStatus} The system status obj
        """
        response = self.session.get(self._get_full_url("cache_server_system_status"))
        self.validate_response(response)

        return self.parser.build_siemplify_system_status_obj(response.json())

    def get_system_info(self):
        """
        Returns current system info.
        :return: {SystemInfo} system version information
        """
        response = self.session.get(self._get_full_url("system_info"))
        self.validate_response(response)

        return self.parser.build_result(
            response.json(), "build_siemplify_system_info_obj"
        )

    def initiate_full_scan_by_uuid(self, agent_uuid):
        """
        Initiate full endpoint scan.
        :param agent_uuid: {string} Agent's uuid.
        :return: {bool} is succeed.
        """
        payload = copy.deepcopy(INITIATE_FULL_SCAN_PAYLOAD)
        payload["filter"]["uuid"] = agent_uuid
        response = self.session.post(
            self._get_full_url("initiate_full_scan_url"), json=payload
        )
        self.validate_response(response)

        return True

    def create_path_exclusion(
        self,
        path,
        os_type,
        site_ids,
        group_ids,
        account_ids,
        description,
        tenant,
        add_subfolders,
        is_folder_path,
        mode,
    ):
        """
        Create an exclusion of pth type.
        :param path: {str} Target path.
        :param os_type: {str} can be windows, windows_legacy, macos or linux.
        :param site_ids: {str} CSV list of site IDs by which to filter
        :param group_ids: {str} CSV list of group IDs by which to filter
        :param account_ids: {str} CSV list of account IDs by which to filter
        :param description: {str} Description and references for the security analyst usage
        :param tenant: {bool} add path exclusion with globally or not
        :param add_subfolders: {bool} add paths subfolders or no
        :param is_folder_path: {bool} Path is file or folder
        :param mode: {str} mode
        :return: {list} List of Path objects
        """
        payload = {
            "filter": {},
            "data": {
                "value": path,
                "osType": os_type,
                "type": PATH_TYPE_STRING,
                "description": description,
                "mode": mode,
            },
        }
        # Filter dict prepare
        if tenant:
            payload["filter"].update({"tenant": True})
        else:
            if account_ids:
                payload["filter"].update({"accountIds": account_ids})
            if site_ids:
                payload["filter"].update({"siteIds": site_ids})
            if group_ids:
                payload["filter"].update({"groupIds": group_ids})

        # Data dict prepare
        if not is_folder_path:
            payload["data"]["pathExclusionType"] = "file"
            payload["data"]["includeSubfolders"] = False
        else:
            payload["data"]["pathExclusionType"] = (
                "subfolders" if add_subfolders else "folder"
            )
            payload["data"]["includeSubfolders"] = add_subfolders

        response = self.session.post(
            self._get_full_url("create_exclusions_url"), json=payload
        )
        self.validate_response(response)

        return self.parser.build_results(response.json(), "build_path_obj")

    def create_hash_exclusion(
        self, hash_value, os_type, site_ids, group_ids, account_ids, description, tenant
    ):
        """
        Create an exclusion of whitelist type.
        :param hash_value: {str} hash value.
        :param os_type: {str} can be windows, windows_legacy, macos or linux.
        :param site_ids: {str} comma-separated list of site IDs by which to filter
        :param group_ids: {str} comma-separated list of group IDs by which to filter
        :param account_ids: {str} comma-separated list of account IDs by which to filter
        :param description: {str} Description
        :param tenant: {str} True if should be added globally False otherwise
        :return: {list} List of Path objects
        """
        payload = {
            "filter": {},
            "data": {
                "value": hash_value,
                "osType": os_type,
                "type": HASH_TYPE_STRING,
                "description": description,
            },
        }

        if tenant:
            payload["filter"].update({"tenant": True})
        else:
            if account_ids:
                payload["filter"].update({"accountIds": account_ids})
            if site_ids:
                payload["filter"].update({"siteIds": site_ids})
            if group_ids:
                payload["filter"].update({"groupIds": group_ids})

        response = self.session.post(
            self._get_full_url("create_exclusions_url"), json=payload
        )
        self.validate_response(response)

        return self.parser.build_results(response.json(), "build_path_obj")

    def create_hash_black_list_record(
        self, hash_value, os_type, site_ids, group_ids, account_ids, description, tenant
    ):
        """
        Create an exclusion of black_list type.
        :param hash_value: {str} hash value.
        :param os_type: {str} can be windows, windows_legacy, macos or linux.
        :param site_ids: {str} comma-separated list of site IDs by which to filter
        :param group_ids: {str} comma-separated list of group IDs by which to filter
        :param account_ids: {str} comma-separated list of account IDs by which to filter
        :param description: {str} Description
        :param tenant: {bool} True if should be added globally False otherwise
        :return: {list} List of Path objects
        """
        payload = {
            "filter": {},
            "data": {
                "value": hash_value,
                "osType": os_type,
                "type": BLACK_HASH_TYPE_STRING,
                "description": description,
            },
        }

        if tenant:
            payload["filter"].update({"tenant": True})
        else:
            if account_ids:
                payload["filter"].update({"accountIds": account_ids})
            if site_ids:
                payload["filter"].update({"siteIds": site_ids})
            if group_ids:
                payload["filter"].update({"groupIds": group_ids})

        response = self.session.post(
            self._get_full_url("create_hash_blacklist_url"), json=payload
        )
        self.validate_response(response)

        return self.parser.build_results(response.json(), "build_path_obj")

    def delete_hash_black_list_record(self, hash_object_id):
        """
        Remove hash from blacklist
        :param hash_object_id: {str} Internal Sentinel ID for hash object.
        """
        payload = {"data": {"type": BLACK_HASH_TYPE_STRING, "ids": [hash_object_id]}}

        response = self.session.delete(
            self._get_full_url("delete_hash_blacklist_url"), json=payload
        )
        self.validate_response(response)

    def mitigate_threat(self, action_type, threat_ids):
        """
        Applies a mitigation action to a group of threats
        :param action_type: {keyof MITIGATION_MAPPING} Mitigation action
        :param threat_ids: {list} List of threat IDs
        :return: {int} Number of affected threats
        """
        payload = {"filter": {"ids": threat_ids}}
        response = self.session.post(
            self._get_full_url("mitigate_threat", action=action_type), json=payload
        )
        self.validate_response(response, "Unable to mitigate threat")

        return self.parser.get_affected(response.json())

    def get_threats(
        self,
        threat_ids=None,
        mitigation_statuses=None,
        created_until=None,
        created_from=None,
        resolved_threats=None,
        display_name=None,
        limit=DEFAULT_THREATS_LIMIT,
    ):
        """
        Get a list of threats
        :param threat_ids: {list} List of threat IDs
        :param mitigation_statuses: {list} List of mitigation statuses
        :param created_until: {str} Searches for threats created on or before this date
        :param created_from: {str} Searches for threats created on or after this date
        :param resolved_threats: {bool} Whether to only return resolved threats
        :param display_name: {str} Threat display name
        :param limit: {int} The maximum number of threats to return
        :return: {list} List of Threat objects
        """
        threat_ids = threat_ids or []
        mitigation_statuses = mitigation_statuses or []

        if threat_ids:
            params = {"ids": ",".join(threat_ids)}
        else:
            params = {
                "createdAt__lte": created_until,
                "createdAt__gte": created_from,
                "resolved": resolved_threats,
                "displayName__like": display_name,
                "limit": limit,
            }
            if mitigation_statuses:
                params["mitigationStatuses"] = ",".join(mitigation_statuses)

        response = self.session.get(self._get_full_url("threats"), params=params)
        self.validate_response(response, "Unable to get threats")

        return self.parser.build_results(response.json(), "build_threat_obj")

    def get_threat_or_raise(self, threat_id):
        """
        Get threat by id or raise an exception
        :param threat_id: {int} Threat ID
        :return {Threat or exception}: Instance of Threat object or raise
        """
        threat = self.get_threats([threat_id])
        if threat:
            return threat[0]

        raise SentinelOneV2NotFoundError(f"Threat with ID {threat_id} not found")

    def get_blacklist_with_hash(self, hash_value):
        """
        Get blacklist with hash value
        :param hash_value: {str} Hash value of the threat
        :return: {list} Instance of BlacklistedThreat objects
        """
        params = {
            "value": hash_value,
            "limit": DEFAULT_THREATS_LIMIT,
            "type": BLACK_HASH_TYPE_STRING,
            "countOnly": False,
        }
        response = self.session.get(self._get_full_url("blacklist"), params=params)
        self.validate_response(response, "Unable to get blacklist")

        return self.parser.build_results(
            response.json(), "build_blacklisted_threat_obj"
        )

    def get_blacklist_items(
        self, hash_value, site_ids, group_ids, account_ids, limit, query, tenant
    ):
        """
        Get blacklist.
        :param hash_value: Hash value of the threat
        :param site_ids: {str} CSV list of site IDs by which to filter
        :param group_ids: {str} CSV list of group IDs by which to filter
        :param account_ids: {str} CSV list of account IDs by which to filter
        :param limit: {int} The maximum number of items to return
        :param query: {str} Query by which to filter
        :param tenant: {bool} True if should be added globally False otherwise
        :return: List of blacklisted threats
        """
        params = {
            "value": hash_value,
            "limit": limit,
            "type": BLACK_HASH_TYPE_STRING,
            "query": query,
        }

        if tenant:
            params["tenant"] = True
            params["unified"] = True
        else:
            if account_ids:
                params["accountIds"] = ",".join(account_ids)
            if site_ids:
                params["siteIds"] = ",".join(site_ids)
            if group_ids:
                params["groupIds"] = ",".join(group_ids)

        blacklists = self._paginate_results(
            method="GET",
            url=self._get_full_url("blacklist"),
            params=params,
            err_msg="Unable to get blacklist items",
        )

        return self.parser.build_results(
            blacklists, "build_blacklisted_threat_obj", pure_data=True, limit=limit
        )

    def initialize_get_events_for_agent_query(self, agent_uuid, from_date, to_date):
        """
        Initialize query for getting events for an agent in a specific time frame
        :param agent_uuid: {str} The UUID of the agent
        :param from_date: {long} Timestamp in milliseconds to get events from
        :param to_date: {long} Timestamp in milliseconds to get events up to
        :return: {str} The query ID
        """
        payload = {
            "query": f'AgentUUID = "{agent_uuid}"',
            "fromDate": from_date,
            "toDate": to_date,
            "timeFrame": "Custom",
            "queryType": ["events"],
        }
        response = self.session.post(self._get_full_url("query_url"), json=payload)
        self.validate_response(response)

        return self.parser.get_query_id(response.json())

    def initiate_deep_visibility_query(self, query_name, from_date, to_date):
        """
        Initialize a deep visibility query
        :param query_name: {str} query to initialize
        :param from_date: {long} Timestamp in milliseconds of query fromDate
        :param to_date: {long} Timestamp in milliseconds of query toDate
        :return: {str} The query ID
        """
        payload = {
            "query": query_name,
            "fromDate": from_date,
            "toDate": to_date,
            "isVerbose": True,
            "queryType": ["events"],
        }
        response = self.session.post(self._get_full_url("init_query"), json=payload)
        self.validate_response(
            response, error_msg="Failed to initiate deep visibility query"
        )

        return self.parser.get_query_id(response.json())

    def get_deep_visibility_query_status(self, query_id):
        """
        Get the current status of a deep visibility query by its ID
        :param query_id: {str} The ID of the query
        :return: {str} The status of the query
        """
        response = self.session.get(
            self._get_full_url("deep_visibility_query_status"),
            params={"queryId": query_id},
        )
        self.validate_response(response)

        return self.parser.get_response_state(response.json())

    def get_deep_visibility_query_events(self, query_id, limit=None):
        """
        Get deep visibility query events
        :param query_id: {str} The ID of the query
        :param limit: {int} Max numbed of events to return
        :return: {[QueryEvent]} List of Deep Visibility events
        """
        payload = {"queryId": query_id, "queryType": "events", "limit": limit}

        response = self.session.get(
            self._get_full_url("deep_visibility_query_events"), params=payload
        )
        self.validate_response(response, "Unable to get deep visibility query events")

        return self.parser.build_results(
            response.json(), "build_deep_visibility_query_event", limit=limit
        )

    def get_query_status(self, query_id):
        """
        Get the current status of a query by its ID
        :param query_id: {unicode} The ID of the query
        :return: {unicode} The status of the query
        """
        response = self.session.get(
            self._get_full_url("query_status"), params={"queryId": query_id}
        )
        self.validate_response(response)

        return self.parser.get_query_status(response.json())

    def is_query_completed(self, query_id):
        """
        Check if a given query has completed
        :param query_id: {str} The ID of the query
        :return: {bool} True if completed, False otherwise
        """
        status = self.get_query_status(query_id)

        return status in COMPLETED_QUERY_STATUSES

    def is_failed_query_status(self, query_status):
        """
        Check if a given query status failed
        :param query_status: {str} The ID of the query
        :return: {bool} True if failed, False otherwise
        """
        return query_status in FAILED_QUERY_STATUSES

    def get_process_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type process for a given query
        :param query_id: {unicode} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[ProcessEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("process_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get process events for query {query_id}",
        )
        return self.parser.build_results(
            events, "build_siemplify_process_event_obj", pure_data=True
        )

    def get_file_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type file for a given query
        :param query_id: {str} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[FileEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("file_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get process events for query {query_id}",
        )

        return self.parser.build_results(
            events, "build_siemplify_file_event_obj", pure_data=True
        )

    def get_indicator_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type indicator for a given query
        :param query_id: {str} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[IndicatorEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("indicator_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get indicator events for query {query_id}",
        )

        return self.parser.build_results(
            events, "build_siemplify_indicator_event_obj", pure_data=True
        )

    def get_dns_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type dns for a given query
        :param query_id: {str} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[DNSEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("dns_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get dns events for query {query_id}",
        )

        return self.parser.build_results(
            events, "build_siemplify_dns_event_obj", pure_data=True
        )

    def get_network_actions_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type Network Actions for a given query
        :param query_id: {str} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[NetworkActionsEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("network_actions_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get network actions events for query {query_id}",
        )

        return self.parser.build_results(
            events, "build_siemplify_network_actions_event_obj", pure_data=True
        )

    def get_url_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type URL for a given query
        :param query_id: {str} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[URLEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("url_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get url events for query {query_id}",
        )

        return self.parser.build_results(
            events, "build_siemplify_url_event_obj", pure_data=True
        )

    def get_registry_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type registry for a given query
        :param query_id: {str} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[RegistryEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("registry_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get registry events for query {query_id}",
        )

        return self.parser.build_results(
            events, "build_siemplify_registry_event_obj", pure_data=True
        )

    def get_scheduled_task_events_by_query_id(self, query_id, limit=None):
        """
        Get events of type scheduled task for a given query
        :param query_id: {str} The ID of the query
        :param limit: {int} The max amount of results to return
        :return: {[ScheduledTaskEvent]} The found events
        """
        events = self._paginate_results(
            method="GET",
            url=self._get_full_url("scheduled_task_events"),
            params={"queryId": query_id},
            limit=limit,
            err_msg=f"Unable to get scheduled task events for query {query_id}",
        )

        return self.parser.build_results(
            events, "build_siemplify_scheduled_task_event_obj", pure_data=True
        )

    def get_unresolved_threats_by_time(
        self, from_time=datetime.datetime.now(), existing_ids=None, limit=None
    ):
        """
        Get unresolved threats for time greated then set.
        :param from_time: {datetime} Time to fetch from.
        :param existing_ids: {list} List of existing IDS to skip
        :param limit: {int} The max amount of results to return
        :return: {list} Instance of Threat objects.
        """
        existing_ids = existing_ids or []

        threats_json = self._paginate_results(
            method="GET",
            url=self._get_full_url("threats"),
            params={
                "resolved": False,
                "createdAt__gte": from_time.strftime(FETCH_EVENT_TIME_FORMAT),
                "sortOrder": "asc",
                "sortBy": "createdAt",
            },
            limit=limit,
            err_msg=f"Unable to get unresolved threats since {from_time.isoformat()}",
            existing_values=existing_ids,
            id_field_name="id",
        )

        return self.parser.build_results(
            threats_json, "build_threat_obj", pure_data=True
        )

    def get_threat_events(self, threat_id, event_types, event_subtypes, limit):
        """
        Get threat events.
        :param threat_id: {str} ID of the threat.
        :param event_types: {str} Event types.
        :param event_subtypes: {str} Event subtypes.
        :param limit: {int} The max amount of results to return
        :return: {list} List of ThreatEvent objects
        """

        events_json = self._paginate_results(
            method="GET",
            url=self._get_full_url("threat_events", threat_id=threat_id),
            params={"eventTypes": event_types, "eventSubTypes": event_subtypes},
            limit=limit,
            err_msg="Unable to get threat events",
            for_threat_events=True,
        )

        return self.parser.build_results(
            events_json, "build_threat_event_obj", pure_data=True
        )

    def get_group_or_raise(self, group_name):
        """
        Get Group or raise
        :param group_name: {str} group name
        :return: {Group} instance of Group object
        """
        group = self.get_group_details(group_name=group_name)
        if group:
            return group

        raise SentinelOneV2NotFoundError(f"Group {group_name} not found")

    def get_group_details(self, group_name=None):
        """
        Get Group Details
        :param group_name: {str} group name
        :return: {Group} Instance of Group object or None
        """
        group_details = self._paginate_results(
            method="GET",
            url=self._get_full_url("groups"),
            limit=1,
            params={"name": group_name},
        )  # receive single page response
        return self.parser.build_group_obj(group_details[0]) if group_details else None

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        existing_values=None,
        id_field_name=None,
        items_field_name=None,
        for_threat_events=False,
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :param existing_values: {list} List of unique identifiers to skip in the pagination
        :param id_field_name: {str} The name of the field to look for the ID of the result ot filter with existing_values
        :param items_field_name: {str} The name of the field to look for the result items
        :param for_threat_events: {bool} Special message for Threat Events
        :return: {list} List of results
        """
        existing_values = existing_values or []

        params = params or {}

        params.update({"limit": DEFAULT_PAGE_SIZE})

        response = None
        results = []

        while True:
            if response:
                if limit and len(results) >= limit:
                    break

                next_cursor = self.parser.get_next_cursor(response.json())

                if not next_cursor:
                    break

                params.update({"cursor": next_cursor})

            response = self.session.request(method, url, params=params, json=body)

            self.validate_response(
                response, err_msg, for_threat_events=for_threat_events
            )

            if existing_values and id_field_name:
                results.extend(
                    [
                        result
                        for result in self.parser.get_paginated_data(response.json())
                        if result.get(id_field_name) not in existing_values
                    ]
                )
            elif items_field_name:
                results.extend(
                    self.parser.get_paginated_data(response.json(), items_field_name)
                )
            else:
                results.extend(self.parser.get_paginated_data(response.json()))

        return results[:limit] if limit else results

    def get_sites(self, filter_key, filter_logic, filter_value, limit):
        """
        Get sites
        :param filter_key: {str} Filter key to use for results filtering
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Limit for results
        :return: {list} List of Site objects
        """
        sites = self._paginate_results(
            method="GET",
            url=self._get_full_url("sites"),
            limit=limit,
            items_field_name="sites",
        )

        return filter_items(
            items=self.parser.build_results(sites, "build_site_object", pure_data=True),
            filter_key=filter_key,
            filter_logic=filter_logic,
            filter_value=filter_value,
        )
