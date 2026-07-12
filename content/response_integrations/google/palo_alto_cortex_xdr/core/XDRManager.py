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

from typing import Any, NamedTuple, TYPE_CHECKING

import dataclasses

from TIPCommon.base.interfaces import Apiable

from ..core.api_utils import validate_response
from ..core.constants import ALERTS_DEFAULT_LIMIT, BATCH_SIZE
from ..core.datamodels import IncidentExtraData, IncidentInfo
from ..core.exceptions import XDRNotFoundException, XDRException
from ..core.PaloAltoCortexXDRTransformationLayer import PaloAltoCortexXDRTransformationLayer

if TYPE_CHECKING:
    import requests

    from TIPCommon.base.interfaces import ScriptLogger
    from TIPCommon.types import SingleJson

    from ..core.datamodels import (
        Endpoint,
        Incident,
        XQLSearch,
        XQLSearchResult,
    )


@dataclasses.dataclass(slots=True)
class SearchXQLParameters:
    query: str
    start_time: int
    end_time: int
    limit: int


class ApiParameters(NamedTuple):
    api_root: str


class XDRManager(Apiable):
    def __init__(
        self,
        session: requests.Session,
        api_params: ApiParameters,
        logger: ScriptLogger,
    ):
        super().__init__(
            authenticated_session=session,
            configuration=api_params,
        )
        self.api_root = (
            api_params.api_root[:-1]
            if api_params.api_root.endswith("/")
            else api_params.api_root
        )
        self.logger = logger
        self.connect_to_xdr(session.headers)

        self.transformation_layer = PaloAltoCortexXDRTransformationLayer()

    def connect_to_xdr(self, headers):
        """
        test advanced authentication
        :param headers: {dict} headers after calculation
        :return: {boolean} true if authenticated
        """
        res = self.session.post(
            url=f"{self.api_root}/api_keys/validate/", headers=headers, json={}
        )

        validate_response(res)
        self.logger.info("Successfully authenticated")
        return res.json()

    def get_incidents(
        self,
        incident_id_list: list[str] | None = None,
        modification_time: int | None = None,
        modification_filter_enum: Any | None = None,
        creation_time: int | None = None,
        creation_filter_enum: Any | None = None,
        search_from: int = 0,
        search_to: int = 100,
        sort_type: Any | None = None,
        sort_order: Any | None = None,
        statuses: list[str] | None = None,
    ) -> list[IncidentInfo]:
        """Gets a list of incidents based on specified filters.

        If 'incident_id_list' is given, it fetches all incidents for those IDs,
        handling API batching. Otherwise, it fetches a single page of incidents
        based on other filters, using 'search_from' and 'search_to' for pagination.

        Args:
            incident_id_list (list[str] | None): A list of incident IDs to fetch.
            modification_time (int | None): Filter by modification time.
            modification_filter_enum (Any | None): Operator for modification time filter
                ('gte' or 'lte').
            creation_time (int | None): Filter by creation time.
            creation_filter_enum (Any | None): Operator for creation time filter
                ('gte' or 'lte').
            search_from (int): The starting offset for paginated results.
            search_to (int): The number of results per page.
            sort_type (Any | None): Field to sort by ('modification_time' or
                'creation_time').
            sort_order (Any | None): Sort order ('asc' or 'desc').
            statuses (list[str] | None): A list of incident statuses to filter by.

        Returns:
            list[IncidentInfo]: A list of found incidents.
        """
        base_request_data: SingleJson = self._build_get_incidents_base_request(
            modification_time,
            modification_filter_enum,
            creation_time,
            creation_filter_enum,
            sort_type,
            sort_order,
            statuses,
        )

        all_incidents_data: list[SingleJson]

        if incident_id_list and isinstance(incident_id_list, list):
            all_incidents_data = self._get_incidents_by_ids(
                incident_id_list,
                base_request_data,
            )
        else:
            all_incidents_data = self._get_incidents_by_filters(
                base_request_data,
                search_from,
                search_to,
            )

        return [
            IncidentInfo.from_json(incident) for incident in all_incidents_data
        ]

    def _build_get_incidents_base_request(
        self,
        modification_time: int | None,
        modification_filter_enum: Any | None,
        creation_time: int | None,
        creation_filter_enum: Any | None,
        sort_type: Any | None,
        sort_order: Any | None,
        statuses: list[str] | None,
    ) -> SingleJson:
        base_request_data: SingleJson = {"filters": [], "sort": {}}
        filters: list[SingleJson] = base_request_data["filters"]

        if sort_type:
            base_request_data["sort"]["field"] = sort_type.value
        if sort_order:
            base_request_data["sort"]["keyword"] = sort_order.value

        if creation_filter_enum and creation_time:
            filters.append(
                {
                    "field": "creation_time",
                    "operator": creation_filter_enum.value,
                    "value": creation_time,
                }
            )
        if modification_filter_enum and modification_time:
            filters.append(
                {
                    "field": "modification_time",
                    "operator": modification_filter_enum.value,
                    "value": modification_time,
                }
            )
        if statuses is not None:
            filters.append({"field": "status", "operator": "in", "value": statuses})

        return base_request_data

    def _post_get_incidents_request(
        self,
        request_data: SingleJson,
    ) -> list[SingleJson]:
        res: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/incidents/get_incidents/",
            json={"request_data": request_data},
        )
        validate_response(res)
        reply: SingleJson = res.json().get("reply", {})

        return reply.get("incidents", [])

    def _get_incidents_by_ids(
        self,
        incident_id_list: list[str],
        base_request_data: SingleJson,
    ) -> list[SingleJson]:
        all_incidents_data: list[SingleJson] = []
        for i in range(0, len(incident_id_list), BATCH_SIZE):
            batch_ids: list[str] = incident_id_list[i : i + BATCH_SIZE]
            request_data: SingleJson = {
                "filters": base_request_data["filters"]
                           + [
                               {
                                   "field": "incident_id_list",
                                   "operator": "in",
                                   "value": batch_ids,
                               }
                           ],
                "sort": base_request_data["sort"],
                "search_from": 0,
                "search_to": BATCH_SIZE,
            }
            batch_incidents: list[SingleJson] = self._post_get_incidents_request(
                request_data,
            )
            all_incidents_data.extend(batch_incidents)

        return all_incidents_data

    def _get_incidents_by_filters(
        self,
        base_request_data: SingleJson,
        search_from: int,
        search_to: int,
    ) -> list[SingleJson]:
        request_data: SingleJson = base_request_data
        request_data["search_from"] = search_from
        request_data["search_to"] = search_to

        return self._post_get_incidents_request(request_data)

    def get_extra_incident_data(
        self, incident_id, alerts_limit=ALERTS_DEFAULT_LIMIT
    ) -> IncidentExtraData:
        """
        Get extra data fields of a specific incident including alerts and key artifacts.
        :param incident_id: {string} The ID of the incident for which you want to retrieve extra data.
        :param alerts_limit: {int} Maximum number of related alerts in the incident to retrieve (default is 1000)
        :return: {dict} the additional incident information including: alerts, network artifacts, and file artifacts.
        """
        request_data: SingleJson = {
            "incident_id": incident_id,
            "alerts_limit": alerts_limit,
        }
        res: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/incidents/get_incident_extra_data/",
            json={"request_data": request_data},
        )
        validate_response(res)
        return IncidentExtraData.from_json(res.json().get("reply", {}))

    def update_an_incident(
        self,
        incident_id,
        assigned_user=None,
        severity=None,
        status=None,
        resolve_comment=None,
    ):
        """
        Update one or more fields of a specific incident. Missing fields are ignored.
        :param incident_id: {string} An integer representing the incident ID to be updated.
        :param assigned_user: {string} The updated full name of the incident assignee.
        :param severity: {string} Administrator-defined severity, one of the following (case insensitive):
        High, Medium, Low. To remove a manually set severity pass "none" or ""
        :param status: {string} Updated incident status, one of the following: NEW, UNDER_INVESTIGATION,
        RESOLVED_THREAT_HANDLED, RESOLVED_KNOWN_ISSUE, RESOLVED_DUPLICATE, RESOLVED_FALSE_POSITIVE, RESOLVED_OTHER
        :param resolve_comment: {string} Descriptive comment explaining the incident change.
        """
        request_data = {"incident_id": incident_id, "update_data": {}}

        if assigned_user:
            request_data["update_data"]["assigned_user_mail"] = assigned_user
        if severity:
            request_data["update_data"]["manual_severity"] = severity
        if status:
            request_data["update_data"]["status"] = status

        if resolve_comment:
            request_data["update_data"]["resolve_comment"] = resolve_comment

        res = self.session.post(
            f"{self.api_root}/public_api/v1/incidents/update_incident/",
            json={"request_data": request_data},
        )
        validate_response(res)
        if not res.json()["reply"]:
            raise XDRException(f"Failed to update incident data: {incident_id}.")

    def get_all_endpoints(self, limit=100) -> list[Endpoint]:
        """ Get all endpoints

        Args:
            limit (int): The maximum number of endpoints to retrieve. Default is 100.

        Returns:
            list[Endpoint]: A list of Endpoint objects.
        """
        if not limit:
            limit = 100
        res = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/get_endpoints/"
        )
        validate_response(res)
        raw_endpoints = res.json().get("reply", [])
        endpoints = []
        for endpoint in raw_endpoints[:limit]:
            endpoints.append(self.get_endpoint_by_id(endpoint.get("agent_id")))

        return endpoints

    def get_endpoint_by_id(self, endpoint_id):
        request_data = {
            "filters": [
                {"field": "endpoint_id_list", "operator": "in", "value": [endpoint_id]}
            ]
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/get_endpoint/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply") or not res.json().get("reply", {}).get(
            "endpoints", []
        ):
            raise XDRNotFoundException(f"Unable to get endpoint {endpoint_id}.")

        return self.transformation_layer.build_siemplify_endpoint_obj(
            res.json()["reply"]["endpoints"][0]
        )

    def get_endpoint_by_ip(self, ip_address):
        request_data = {
            "filters": [{"field": "ip_list", "operator": "in", "value": [ip_address]}]
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/get_endpoint/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply") or not res.json().get("reply", {}).get(
            "endpoints", []
        ):
            raise XDRNotFoundException(f"Unable to get endpoint for IP {ip_address}.")

        return self.transformation_layer.build_siemplify_endpoint_obj(
            res.json()["reply"]["endpoints"][0]
        )

    def get_endpoint_by_hostname(self, hostname):
        request_data = {
            "filters": [{"field": "hostname", "operator": "in", "value": [hostname]}]
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/get_endpoint/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply") or not res.json().get("reply", {}).get(
            "endpoints", []
        ):
            raise XDRNotFoundException(
                f"Unable to get endpoint for hostname {hostname}."
            )

        return self.transformation_layer.build_siemplify_endpoint_obj(
            res.json()["reply"]["endpoints"][0]
        )

    def get_endpoints(
        self,
        ip_addresses=None,
        hostnames=None,
        platforms=None,
        aliases=None,
        isolation_status=None,
        group_names=None,
        endpoint_ids=None,
        limit=100,
    ):
        filters = []

        if ip_addresses:
            filters.append(
                {"field": "ip_list", "operator": "in", "value": ip_addresses}
            )

        if hostnames:
            filters.append({"field": "hostname", "operator": "in", "value": hostnames})

        if platforms:
            filters.append({"field": "platform", "operator": "in", "value": platforms})

        if group_names:
            filters.append(
                {"field": "group_name", "operator": "in", "value": group_names}
            )

        if aliases:
            filters.append({"field": "alias", "operator": "in", "value": aliases})

        if isolation_status:
            filters.append(
                {"field": "isolate", "operator": "in", "value": [isolation_status]}
            )

        if endpoint_ids:
            filters.append(
                {"field": "endpoint_id_list", "operator": "in", "value": endpoint_ids}
            )

        request_data = {"filters": filters, "limit": limit}

        res = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/get_endpoint/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException("Unable to list endpoints")

        return [
            self.transformation_layer.build_siemplify_endpoint_obj(endpoint_data)
            for endpoint_data in res.json()["reply"]["endpoints"]
        ]

    def isolate_endpoint(self, endpoint_id):
        res = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/isolate/",
            json={"request_data": {"endpoint_id": endpoint_id}},
        )
        validate_response(res)
        return True

    def unisolate_endpoint(self, endpoint_id):
        res = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/unisolate/",
            json={"request_data": {"endpoint_id": endpoint_id}},
        )
        validate_response(res)
        return True

    def scan_endpoint(self, endpoint_id):
        request_data = {
            "filters": [
                {"field": "endpoint_id_list", "operator": "in", "value": [endpoint_id]}
            ]
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/endpoints/scan/",
            json={"request_data": request_data},
        )
        validate_response(res)
        return True

    def cancel_scan_endpoint(self, endpoint_id):
        request_data = {
            "filters": [
                {"field": "endpoint_id_list", "operator": "in", "value": [endpoint_id]}
            ]
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/endpoints/abort_scan/",
            json={"request_data": request_data},
        )
        validate_response(res)
        return True

    def delete_endpoint(self, endpoint_id):
        request_data = {
            "filters": [
                {"field": "endpoint_id_list", "operator": "in", "value": [endpoint_id]}
            ]
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/endpoints/delete/",
            json={"request_data": request_data},
        )
        validate_response(res)
        return True

    def get_device_violations(
        self,
        hostnames=None,
        products=None,
        usernames=None,
        vendors=None,
        types=None,
        endpoint_ids=None,
        start_timestamp=None,
        end_timestamp=None,
        ip_addresses=None,
        violation_ids=None,
        limit=100,
    ):
        """

        :param hostnames: {[]} Filter by hostnames
        :param products:  {[]} Filter by products
        :param usernames: {[]} Filter by usernames
        :param vendors:  {[]} Filter by vendors
        :param types:  {[]} Filter by types. Valid values: cd-rom, disk, floppy disk, portabledevice
        :param endpoint_ids:  {[]} Filter by endpoints
        :param start_timestamp: {long} Filter by start timestamp of the violation (unix time)
        :param end_timestamp: {long} Filter by start timestamp of the violation (unix time)
        :param ip_addresses:  {[]} {Filter by IP addresses
        :param violation_ids:  {[]} Filter by violations IDs
        :return: {[]} List of found violations
        """
        if not limit:
            limit = 100
        filters = []

        if start_timestamp:
            filters.append(
                {"field": "timestamp", "operator": "gte", "value": start_timestamp}
            )

        if end_timestamp:
            filters.append(
                {"field": "timestamp", "operator": "lte", "value": end_timestamp}
            )

        if ip_addresses:
            filters.append(
                {"field": "ip_list", "operator": "in", "value": ip_addresses}
            )

        if hostnames:
            filters.append({"field": "hostname", "operator": "in", "value": hostnames})

        if products:
            filters.append({"field": "product", "operator": "in", "value": products})

        if usernames:
            filters.append({"field": "username", "operator": "in", "value": usernames})

        if vendors:
            filters.append({"field": "vendor", "operator": "in", "value": vendors})

        if endpoint_ids:
            filters.append(
                {"field": "endpoint_id_list", "operator": "in", "value": endpoint_ids}
            )

        if violation_ids:
            filters.append(
                {"field": "violation_id_list", "operator": "in", "value": violation_ids}
            )

        if types:
            filters.append({"field": "type", "operator": "in", "value": types})

        request_data = {"filters": filters}

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/device_control/get_violations",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException("Unable to list device violations")

        return [
            self.transformation_layer.build_siemplify_device_violation_obj(
                violation_data
            )
            for violation_data in res.json()["reply"]["violations"]
        ]

    def get_endpoint_agent_report(self, endpoint_id):
        request_data = {
            "filters": [
                {"field": "endpoint_id", "operator": "in", "value": [endpoint_id]}
            ]
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/agents_reports/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply") or not res.json()["reply"].get("data"):
            raise XDRException(f"Unable to get agent report for endpoint {endpoint_id}")

        return self.transformation_layer.build_siemplify_agent_report_obj(
            res.json()["reply"]["data"][0]
        )

    def quarantine_file_on_endpoint(self, endpoint_id, file_path, file_hash):
        """
        Quarantine file on an endpoint by its ID
        :param endpoint_id: {str} The endpoint ID
        :param file_path: {str} The path of the file you want to quarantine.
        :param file_hash: {str} The file's hash. Hash must be a valid SHA256.
        :return:
        """
        request_data = {
            "filters": [
                {"field": "endpoint_id_list", "operator": "in", "value": [endpoint_id]}
            ],
            "file_path": file_path,
            "file_hash": file_hash,
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/endpoints/quarantine/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException(f"Unable to quarantine file on endpoint {endpoint_id}")

        return True

    def restore_file_on_endpoint(self, endpoint_id, file_hash):
        """
        Restore file on an endpoint by its ID
        :param endpoint_id: {str} The endpoint ID
        :param file_hash: {str} The file's hash. Hash must be a valid SHA256.
        :return:
        """
        request_data = {"endpoint_id": endpoint_id, "file_hash": file_hash}

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/endpoints/restore/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException(f"Unable to quarantine file on endpoint {endpoint_id}")

        return True

    def whitelist_file_on_endpoint(self, file_hash, comment=None):
        """
        Whitelist file on an endpoint by its ID
        :param file_hash: {str} The file's hash. Hash must be a valid SHA256.
        :param comment: {str} String that represents additional information regarding the action.
        :return:
        """
        request_data = {"hash_list": [file_hash]}

        if comment:
            request_data["comment"] = comment

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/hash_exceptions/whitelist/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException(f"Unable to whitelist hash {file_hash}")

        return True

    def blacklist_file_on_endpoint(self, file_hash, comment=None):
        """
        Blacklist file on an endpoint by its ID
        :param file_hash: {str} The file's hash. Hash must be a valid SHA256.
        :param comment: {str} String that represents additional information regarding the action.
        :return:
        """
        request_data = {"hash_list": [file_hash]}

        if comment:
            request_data["comment"] = comment

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/hash_exceptions/blacklist/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException(f"Unable to blacklist hash {file_hash}")

        return True

    def retrieve_file_from_endpoint(self, endpoint_id, os_type, file_path):
        request_data = {
            "filters": [
                {"field": "endpoint_id_list", "operator": "in", "value": [endpoint_id]}
            ],
            "files": {os_type: [file_path]},
        }

        res = self.session.post(
            f"{self.api_root}/public_api/v1/audits/endpoints/file_retrieval/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException(
                f"Unable to retrieve file {file_path} from endpoint {endpoint_id}"
            )

        return res.json().get("reply")

    def add_hash_to_block_list(self, file_hash, comment=None):
        """
        Add file to a block list
        :param file_hash: {str} The file's hash. Hash must be a valid SHA256.
        :param comment: {str} String that represents additional information regarding the action.
        :return: {bool} True if successful, exception otherwise.
        """
        request_data = {"hash_list": [file_hash]}

        if comment:
            request_data["comment"] = comment

        res = self.session.post(
            f"{self.api_root}/public_api/v1/hash_exceptions/blocklist/",
            json={"request_data": request_data},
        )
        validate_response(res)

        if not res.json().get("reply"):
            raise XDRException(f"Unable to add hash {file_hash} to a block list.")

        return True

    @staticmethod
    def is_sha256(file_hash):
        return len(file_hash) == 64

    def execute_xql_search(self, search_params: SearchXQLParameters) -> XQLSearch:
        """Execute XQL search.

        Args:
            search_params (SearchXQLParameters): The parameters for the XQL search.

        Returns:
            XQLSearch: XQL Search.
        """
        payload: SingleJson = {
            "request_data": {
                "query": f"{search_params.query} | limit {search_params.limit}",
                "timeframe": {
                    "from": search_params.start_time,
                    "to": search_params.end_time,
                },
            }
        }
        res: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/xql/start_xql_query",
            json=payload,
        )
        validate_response(res)

        return self.transformation_layer.build_siemplify_xql_search_obj(res.json())

    def get_xql_search_results(self, query_id: str) -> XQLSearchResult:
        """Get results of XQL Search.

        Args:
            search_id (str): The ID of the XQL search.

        Returns:
            XQLSearchResult: XQL search result with events.
        """
        payload: SingleJson = {
            "request_data": {
                "query_id": query_id,
                "pending_flag": True,
                "format": "json",
            }
        }
        res: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/xql/get_query_results",
            json=payload,
        )
        validate_response(res)

        return self.transformation_layer.build_siemplify_xql_result_obj(res.json())

    def get_incident_details(
        self,
        incident_id: str,
        limit: int,
    ) -> Incident:
        """
        Get alerts details.

        Args:
            incident_id (str): The ID of the incident.
            limit (int): The maximum number of alerts to retrieve.

        Returns:
            list[Alert]: List of alerts.
        """
        payload: SingleJson = {
            "request_data": {
                "incident_id": incident_id,
                "alerts_limit": limit,
            }
        }

        response: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/incidents/get_incident_extra_data",
            json=payload,
        )
        validate_response(response)

        return self.transformation_layer.build_siemplify_incident_details_obj(
            response.json()
        )

    def add_comment_to_incident(self, incident_id: str, comment: str) -> None:
        """Add a comment to a specific incident.

        Args:
            incident_id (str): The ID of the incident to add a comment to.
            comment (str): The comment to add.
        """
        request_data: SingleJson = {
            "incident_id": incident_id,
            "update_data": {
                "comment": {"comment_action": "add", "value": comment}
            },
        }

        res: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/incidents/update_incident/",
            json={"request_data": request_data},
        )
        validate_response(res)
        if not res.json()["reply"]:
            raise XDRException(f"Failed to add comment to incident: {incident_id}.")

    def scan_endpoints(
        self,
        endpoint_ids: list[str],
        incident_id: str | None = None,
    ) -> SingleJson:
        """
        Initiate a scan on a list of endpoints.
        Args:
            endpoint_ids: A list of endpoint IDs to scan.
            incident_id: If provided, scan activity is shown in the Incident timeline.

        Returns:
            A dictionary with the action ID and the count of endpoints being scanned.
        """
        request_data: SingleJson = {
            "filters": [
                {"field": "endpoint_id_list", "operator": "in", "value": endpoint_ids}
            ]
        }

        if incident_id is not None:
            request_data["incident_id"] = incident_id

        res: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/endpoints/scan/",
            json={"request_data": request_data},
        )
        validate_response(res)
        return res.json()["reply"]

    def get_action_status(self, action_id: int) -> list[SingleJson]:
        """Get the status of an action.
        Args:
            action_id: The ID of the action to check.

        Returns:
            A list of action statuses for each endpoint.
        """
        res: requests.Response = self.session.post(
            f"{self.api_root}/public_api/v1/actions/get_action_status/",
            json={"request_data": {"group_action_id": action_id}},
        )
        validate_response(res)
        return res.json()["reply"]
