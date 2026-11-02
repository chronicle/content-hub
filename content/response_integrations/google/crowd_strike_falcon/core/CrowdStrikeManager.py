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

import itertools
import json
from collections.abc import Callable
from time import sleep
from typing import Any, Generator, Iterator
import requests
import urllib.parse
from urllib.parse import urljoin
from requests_toolbelt import MultipartEncoder

from datetime import datetime

from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.types import SingleJson
from TIPCommon.base.utils import CreateSession

from crowd_strike_falcon.core.PaginationStrategy import (
    OffsetPaginationStrategy,
    PaginationStrategy,
    TokenPaginationStrategy,
)
from crowd_strike_falcon.core.constants import (
    ACTION_TYPE_MAPPING,
    API_ENDPOINTS,
    API_ROOT_DEFAULT,
    AUTH_ACTIVITY_AUDIT_EVENT_TYPE,
    CHUNK_SIZE,
    CONNECTION_IP_FILTER,
    DATE_TIME_FORMAT,
    DETECTION_STATUS_MAPPING,
    FILTER_STRATEGY_MAPPING,
    FilterStrategy,
    IOC_DEFAULT_SEVERITY,
    IOC_INDICATORS_MAX_PAGE_SIZE,
    LOCAL_IP_FILTER,
    MAX_HOSTS_TO_FETCH,
    MAX_IOCS_TO_FETCH,
    MAX_PAGE_SIZE,
    MAX_RETRIES,
    OPEN,
    REOPEN,
    RETRY_INTERVAL,
    SEVERITIES,
    UNASSIGN,
    UPDATE_INCIDENT_STATUS_MAPPING,
    UPDATE_INCIDENT_USER_UNASSIGN_CODE,
    PAUSE_DURATION,
    REPOSITORY_MAP,
    VERDICT_MAPPING,
)
from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser
from crowd_strike_falcon.core.datamodels import (
    AlertDetails,
    BaseModel,
    Detection,
    Device,
    IncidentDetails,
    LoginHistory,
    OnDemandScanData,
    OnlineState,
    Process,
    SearchEventsData,
    SubmissionData,
)
from crowd_strike_falcon.core.exceptions import (
    CrowdStrikeManagerError,
    CrowdStrikeSessionCreatedError,
    CrowdStrikeNotFoundError,
    CrowdStrikeUnsupportedType,
    CrowdStrikeTimeoutError,
    CrowdStrikeBadRequestError,
    CrowdStrikeImproperlyConfiguredError,
)
from crowd_strike_falcon.core.utils import resolve_time_frame, TimeRange


DATETIME_FORMAT = "YYYY-MM-DDTHH:MM:SSZ"
HEADERS = {"Content-Type": "application/json"}

SHA256 = "sha256"
MD5 = "md5"
ADDRESS = "ipv4"
DOMAIN = "domain"
DEFAULT_EXPIRATION_DAYS = 30
PAGE_SIZE = 50
MAX_DETECTIONS_TO_FETCH = 100
MAX_PROCESSED_IDS_PER_REQUEST = 400

POLICY_DEFAULT_FOR_DETECT = "detect"
STATUS = [OPEN, REOPEN]
AT_SYMBOL = "@"


class CrowdStrikeManager:
    """
    CrowdStrike Manager
    """

    def __init__(
        self,
        client_id,
        client_secret,
        use_ssl=False,
        api_root=API_ROOT_DEFAULT,
        force_check_connectivity=False,
        logger=None,
        customer_id=None,
    ):
        self.api_root = api_root
        self.session = CreateSession.create_session()

        self.session.verify = use_ssl
        self.session.headers = HEADERS
        token = self.fetch_token(client_id, client_secret, use_ssl, customer_id)
        self.session.headers.update({"Authorization": f"bearer {token}"})

        self.parser = CrowdStrikeParser()

        self.logger = logger

        if force_check_connectivity:
            self.test_connectivity()

    @staticmethod
    def get_query_filter(filter_dict: SingleJson) -> str:
        """Get Query filter string.
        Args:
            filter_dict (SingleJson): Filter key values dict.
        Returns:
            str: Query filter string.
        """
        filters = []
        local_ip = filter_dict.get(LOCAL_IP_FILTER)
        connection_ip = filter_dict.get(CONNECTION_IP_FILTER)

        if local_ip and connection_ip and local_ip == connection_ip:
            filters.append(
                (
                    f"({LOCAL_IP_FILTER}: '{local_ip}', "
                    f"{CONNECTION_IP_FILTER}: '{connection_ip}')"
                )
            )
            filter_dict.pop(LOCAL_IP_FILTER, None)
            filter_dict.pop(CONNECTION_IP_FILTER, None)

        for key, value in filter_dict.items():
            if isinstance(value, list):
                filters.append(f"{key}: {value}")
            else:
                filters.append(f"{key}: '{value}'")

        return "+".join(filters)

    @staticmethod
    def _get_valid_params(params):
        return {k: v for k, v in params.items() if v is not None}

    def fetch_token(
        self,
        client_id: str,
        client_secret: str,
        use_ssl: bool = False,
        customer_id: str | None = None,
    ) -> str:
        """Fetch authentication token for Devices payloads.

        Args:
            client_id (str): The client ID for API authentication.
            client_secret (str): The client secret associated with the client ID.
            customer_id (str | None, optional): The member_cid for API authentication.
            use_ssl (bool, optional): Whether to verify SSL certificates.
                                    Defaults to False.

        Returns:
            str: The access token retrieved from the API.

        Raises:
            Exception: If the response does not contain an access token or if the
                       request fails. The raised exception includes the response content
                       and theHTTP status code.
        """
        url = self._get_full_url("fetch_token")
        payload = {"client_id": client_id, "client_secret": client_secret}
        if customer_id:
            payload["member_cid"] = customer_id
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = self.session.post(url, data=payload, headers=headers, verify=use_ssl)
        self.validate_response(response)

        access_token = response.json().get("access_token", "")

        if access_token:
            return access_token

        raise Exception(
            f"Failed fetching token, Response: {response.content}, "
            f"status: {response.status_code}"
        )

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url for session.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, API_ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to CrowdFalcon.
        :return:
        """
        self.search_devices_ids(limit=1)

        return True

    def search_devices_ids(
        self,
        device_id: str | None = None,
        external_ip: str | None = None,
        hostname: str | None = None,
        last_seen: str | None = None,
        local_ip: str | None = None,
        connection_ip: str | None = None,
        mac_address: str | None = None,
        machine_domain: str | None = None,
        platform_name: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        for_hosts: bool = False,
        cid: str | None = None,
        include_hidden_hosts: bool = False,
        sort: str | None = "last_seen.desc",
    ) -> list[str]:
        """Search for hosts in your environment by platform, hostname, IP, and other
        criteria.

        Args:
            device_id (str): The ID of the customer.
            external_ip (str): External IP of the device, as seen by CrowdStrike.
            hostname (str): The name of the machine. Supports prefix and suffix
                searching with * wildcard (abc* / *abc).
            last_seen (str): Timestamp of devices most recent connection to Falcon.
                ex. YYYY-MM-DDTHH:MM:SSZ.
            local_ip (str): The device's local IP address. the IP address of this
                device at the last time it connected.
            connection_ip (str): The connection IP of the device.
            mac_address (str): The MAC address of the device
                (2001:db8:ffff:ffff:ffff:ffff:ffff:ffff).
            machine_domain (str): Active Directory domain name.
            platform_name (str): Operating system platform. (Mac, etc).
            status (str): Containment Status of the machine. (Normal,
                containment_pending, contained, lift_containment_pending).
            limit (int): Max amount of devices to return.
            for_hosts (bool): True if it is for hosts.
            cid (str): The ID of the customer.
            include_hidden_hosts (bool): If True it includes the hidden host.
            sort (str): Field and order to sort results by (e.g. last_seen.desc).

        Returns:
            list: list of device details.
        """
        filter_data = {
            "device_id": device_id,
            "external_ip": external_ip,
            "hostname": hostname,
            "last_seen": last_seen,
            "local_ip": local_ip,
            "connection_ip": connection_ip,
            "mac_address": mac_address,
            "machine_domain": machine_domain,
            "platform_name": platform_name,
            "status": status,
            "cid": cid,
        }

        filter_data = {key: value for key, value in filter_data.items() if value}
        params = {"filter": self.get_query_filter(filter_data)}
        if sort:
            params["sort"] = sort

        device_ids = self._paginate_results(
            self._get_full_url("queries_devices"),
            params=params,
            limit=limit,
            error_msg="Unable to search for devices ids",
            for_hosts=for_hosts,
        )

        if include_hidden_hosts:
            hidden_device_ids = self._paginate_results(
                self._get_full_url("queries_hidden_devices"),
                params=params,
                limit=limit,
                error_msg="Unable to search for hidden devices ids",
                for_hosts=for_hosts,
            )
            combined_ids = list(set(device_ids + hidden_device_ids))
            return combined_ids[:limit] if limit else combined_ids

        return device_ids

    def search_devices(
        self,
        cid: str | None = None,
        include_hidden_hosts: bool = False,
        method: str | None = None,
        limit: int | None = None,
        **kwargs
    ) -> list[Device]:
        """Search for hosts in your environment by platform, hostname, IP, and other
        criteria.

        Args:
            cid (str | None): The ID of the customer.
            include_hidden_hosts (bool): If True it includes the hidden host.
            method (str | None): API request method
            limit (int | None): Limit of hosts to fetch.

        Returns:
            list: list of device datamodels.Device object.
        """
        starts_with_name = kwargs.get("starts_with_name")
        if starts_with_name:
            kwargs["hostname"] = kwargs.pop("starts_with_name")

        limit = limit or kwargs.get("limit")

        ids = self.search_devices_ids(
            cid=cid,
            include_hidden_hosts=include_hidden_hosts,
            limit=limit,
            **kwargs,
        )

        if not ids:
            return []

        devices = self.get_devices(
            devices_ids=ids,
            limit=limit,
            for_hosts=kwargs.get("for_hosts"),
            method=method,
        )

        if starts_with_name:
            filtered_devices = [
                device
                for device in devices
                if self.match_device_host_name(device, starts_with_name)
            ]
            return (
                sorted(filtered_devices, key=lambda machine: machine.last_seen_unix)
                if filtered_devices
                else None
            )

        return devices

    def search_device_ids(self, cid: str | None = None, **kwargs) -> list[str]:
        """Search device ids by hostname, IP, and other criteria.

        Args:
            cid (str | None): The ID of the customer.

        Returns:
            list: list of device ids
        """
        starts_with_name = kwargs.get("starts_with_name")
        if starts_with_name:
            kwargs["hostname"] = kwargs.pop("starts_with_name")

        ids = self.search_devices_ids(cid=cid, **kwargs)

        return ids if ids else []

    def create_device_session(self, device_id):
        """
        Create session for provided device
        :param device_id: {str} device id
        :return: {str} session_id
        """
        body = {"device_id": device_id, "origin": "", "queue_offline": True}
        response = self.session.post(self._get_full_url("create_session"), json=body)
        self.validate_response(response, custom_response=True)

        return self.parser.get_resources(
            response.json(), builder_method="get_session_id"
        )[0]

    def start_device_session(self, device_id):
        """
        Create session for provided device
        :param device_id: {str} device id
        :return: {str} session_id
        """
        body = {"host_ids": [device_id], "queue_offline": True}
        response = self.session.post(self._get_full_url("start_session"), json=body)
        self.validate_response(response, custom_response=True)

        return self.parser.build_batch_session_object(response.json(), device_id)

    def batch_get_command(self, batch_id, filename):
        """
        Create session for provided device
        :param batch_id: {str} batch id
        :param filename: {str} file name that should be uploaded
        :return: {str}
        """
        payload = {"batch_id": batch_id, "file_path": f'"{filename}"'}

        response = self.session.post(
            self._get_full_url("pull_file_from_host"), json=payload
        )
        self.validate_response(response, custom_response=True)

        return self.parser.build_batch_get_obj(response.json())

    def get_status_of_batch_command(self, batch_request_id):
        """
        Create session for provided device
        :param batch_request_id: {str} batch_request_id
        :return: {str}
        """
        params = {"batch_get_cmd_req_id": batch_request_id}
        response = self.session.get(
            self._get_full_url("pull_file_from_host"), params=params
        )
        self.validate_response(response, custom_response=True)

        return self.parser.get_resources_dict(
            response.json(), "build_batch_command_obj"
        )

    def execute_responder_command(self, session_id, command, admin_command, device_id):
        """
        Execute responder command
        :param session_id: {str} session_id
        :param command: {str} command
        :param admin_command: {bool} admin
        :param device_id: {str} device id
        :return: {str} cloud_request_id
        """
        body = {
            "base_command": command.split()[0],
            "command_string": command,
            "device_id": device_id,
            "persist": True,
            "session_id": session_id,
        }
        endpoint = "responder_command_admin" if admin_command else "responder_command"
        response = self.session.post(self._get_full_url(endpoint), json=body)
        self.validate_response(response, custom_response=True)
        return self.parser.get_resources(
            response.json(), builder_method="get_cloud_request_id"
        )[0]

    def get_status_of_responder_command(self, cloud_request_id, admin_command):
        """
        Get status of session
        :param cloud_request_id: {str} session_id
        :admin_command: {bool} admin
        :return: {list} ov Session.obj
        """

        params = {"cloud_request_id": cloud_request_id, "sequence_id": 0}
        response = self.session.get(
            self._get_full_url(
                "responder_command_admin" if admin_command else "responder_command"
            ),
            params=params,
        )
        self.validate_response(response, custom_response=True)
        return self.parser.get_resources(
            response.json(), builder_method="build_command_object"
        )

    def get_file_content(self, session_id, filehash):
        """
        Get file content
        :param session_id: {str} session id
        :param filehash: {str} file hash
        :return: {str} file content
        """
        params = {"session_id": session_id, "sha256": filehash}
        response = self.session.get(self._get_full_url("file_content"), params=params)
        response.raise_for_status()

        return response.content

    def get_devices(
        self,
        devices_ids: list[str] | None = None,
        limit: int | None = None,
        for_hosts: bool = False,
        method: str | None = None,
    ) -> list[Device]:
        """Get devices by its ids

        Args:
            devices_ids: list of device ids
            limit: limit
            for_hosts: True if it is for hosts
            method: API request method

        Returns:
            list: List of Device objects.
        """
        if not devices_ids:
            return []

        ids_to_fetch = devices_ids[:limit] if limit else devices_ids
        devices = []
        method = method or "GET"

        for i in range(0, len(ids_to_fetch), CHUNK_SIZE):
            chunk = ids_to_fetch[i : i + CHUNK_SIZE]
            kwargs = {}
            if method.upper() == "POST":
                kwargs["json"] = {"ids": chunk}
            else:
                kwargs["params"] = {"ids": chunk}

            response = self.session.request(
                method,
                self._get_full_url("entities_devices"),
                **kwargs
            )
            self.validate_response(response, "Unable to get devices info")
            devices.extend(self.parser.get_resources(response.json()))

        return self.parser.build_results(
            devices, "build_siemplify_device_obj", pure_data=True
        )

    def get_device_ids_by_hostname(
        self,
        filter_data: dict[str, Any],
        page_size: int = MAX_PAGE_SIZE,
    ) -> Generator[str, None, None]:
        """Gets device IDs by hostname using offset pagination.

        Args:
            filter_data: A dictionary of filters to apply to the search.
            page_size: The number of device IDs to retrieve per page.

        Yields:
            A generator of device IDs.
        """
        yield from self.offset_pagination_generator(
            url=self._get_full_url("queries_devices"),
            params={"filter": self.get_query_filter(filter_data)},
            page_size=page_size,
            error_msg="Unable to search for devices ids",
        )

    def get_device_details_by_device_ids(
        self,
        ids: list[str],
    ) -> Generator[SingleJson, None, None]:
        """Gets device details for a list of device IDs.

        Args:
            ids: A list of device IDs.

        Yields:
            A generator of device detail dictionaries.
        """
        yield from self.request_results_generator(
            url=self._get_full_url("entities_devices"),
            method="POST",
            body={"ids": ids},
            error_msg="Unable to search for devices",
        )

    @staticmethod
    def get_object_details_by_ids(
        ids_producer: Generator[str, None, None],
        details_request_stream: Callable[[list[str]], Generator[Any, None, None]],
        to_data_model: Callable[[Any], BaseModel],
        page_size: int = MAX_PAGE_SIZE,
    ) -> Generator[Any, None, None]:
        """Fetches and converts object details from a stream of IDs.

        This function orchestrates fetching details for objects by processing a
        stream of their IDs, making paginated requests for details, and
        converting the raw API responses into structured data models.

        Args:
            ids_producer: A generator that yields object IDs.
            details_request_stream: A callable that takes a list of IDs and a page size,
                and returns a generator of raw object details from the API.
            to_data_model: A callable that converts a raw object detail into a
                structured data model (e.g., a `datamodels.BaseModel` subclass).
            page_size: The number of IDs to include in each batch request for details.

        Yields:
            A generator of structured data model objects, each representing the
            details of an object.
        """
        while ids := list(itertools.islice(ids_producer, page_size)):
            yield from map(to_data_model, details_request_stream(ids))

    @staticmethod
    def filter_data_stream(
        extractor: Callable[[BaseModel], Any],
        value: Any,
        filter_strategy: str | None,
        objects: Generator[Device, None, None],
    ) -> Generator[Device, None, None]:
        """Filters a stream of data objects based on a given value and strategy.

        Args:
            extractor: A function to extract the value to be filtered on from an object.
            value: The value to filter by.
            filter_strategy: The filtering strategy to use (e.g., 'Contains').
            objects: A generator of data objects to filter.

        Yields:
            A generator of filtered data objects.
        """
        if value and filter_strategy == FilterStrategy.Contains.value:
            filter_func = FILTER_STRATEGY_MAPPING[filter_strategy]
            for obj in objects:
                try:
                    original_value = extractor(obj)

                except AttributeError as e:
                    raise CrowdStrikeImproperlyConfiguredError(
                        "Extractor is improperly configured."
                    ) from e

                if filter_func(original_value, value):
                    yield obj
        else:
            yield from objects

    @staticmethod
    def optimize_page_size(page_size: int, limit: int, filter_strategy: str) -> int:
        """Optimizes the page size for API requests based on the filter strategy.

        When an 'Equal' filter strategy is used, the CrowdStrike API handles the
        filtering, so the page size can be reduced to match the limit if the
        limit is smaller. This avoids fetching unnecessary data.

        Args:
            page_size: The default or requested page size.
            limit: The maximum number of items to return.
            filter_strategy: The filtering strategy being used.

        Returns:
            The optimized page size.
        """
        if filter_strategy == FilterStrategy.Equal.value and limit < page_size:
            return limit
        return page_size

    def get_devices_by_hostname(
        self,
        hostname: str,
        filter_strategy: str,
        *,
        cid: str | None = None,
        limit: int | None = MAX_HOSTS_TO_FETCH,
        page_size: int | None = MAX_PAGE_SIZE,
    ) -> list[Device]:
        """Retrieves a list of devices that match a given hostname.

        Args:
            hostname: The hostname to search for.
            filter_strategy: The filtering strategy to use.
            cid: The customer ID.
            limit: The maximum number of devices to return.
            page_size: The number of devices to retrieve per page.

        Returns:
            A list of Device objects.
        """
        filter_data = {}
        if filter_strategy == FilterStrategy.Equal.value and hostname:
            filter_data["hostname"] = [hostname]
        if cid:
            filter_data["cid"] = cid

        page_size = self.optimize_page_size(page_size, limit, filter_strategy)

        device_ids_stream = self.get_device_ids_by_hostname(filter_data, page_size)

        device_details_stream = self.get_object_details_by_ids(
            ids_producer=device_ids_stream,
            details_request_stream=self.get_device_details_by_device_ids,
            to_data_model=self.parser.build_siemplify_device_obj,
            page_size=page_size,
        )

        filtered_devices = self.filter_data_stream(
            extractor=lambda device: device.hostname,
            value=hostname,
            filter_strategy=filter_strategy,
            objects=device_details_stream,
        )
        return list(itertools.islice(filtered_devices, limit))

    def get_ioc_ids_by_types_and_value(
        self,
        ioc_types: list[str] = None,
        ioc_value: str = None,
        page_size: int = IOC_INDICATORS_MAX_PAGE_SIZE,
    ) -> Generator[str, None, None]:
        """Gets IOC IDs based on IOC types and value.

        This function constructs a filter query to search for Indicators of
        Compromise (IOCs) and paginates through the results to yield their IDs.

        Args:
            ioc_types: A list of IOC types to filter by (e.g., 'domain', 'md5').
            ioc_value: The specific value of the IOC to search for.
            page_size: The number of IOC IDs to retrieve per API request.

        Yields:
            A generator of IOC IDs that match the filter criteria.
        """
        filter_parts = []
        if ioc_types:
            filter_parts.append(f"type:{ioc_types}")
        if ioc_value:
            filter_parts.append(f"value:'{ioc_value}'")

        params = {}
        if filter_parts:
            params["filter"] = "+".join(f"{part}" for part in filter_parts)

        yield from self.token_pagination_generator(
            url=self._get_full_url("get_ioc_id"),
            params=params,
            page_size=page_size,
            error_msg="Unable to search for devices ids",
        )

    def get_ioc_details_by_ids(
        self,
        ioc_ids: list[str],
    ) -> Generator[SingleJson, None, None]:
        """Gets detailed information for IOCs from a list of their IDs.

        Args:
            ioc_ids: A list of IOC IDs to retrieve details for.

        Yields:
            A generator of objects representing the details of each IOC.
        """
        yield from self.request_results_generator(
            url=self._get_full_url("get_iocs"),
            params={"ids": ioc_ids},
            error_msg="Unable to search for IOCs",
        )

    def get_uploaded_iocs(
        self,
        ioc_types: list[str] = None,
        ioc_value: str = None,
        filter_strategy: str = FilterStrategy.Equal.value,
        *,
        limit: int | None = MAX_IOCS_TO_FETCH,
        page_size: int | None = IOC_INDICATORS_MAX_PAGE_SIZE,
    ):
        """Gets a list of uploaded IOCs that match the given criteria.

        Args:
            ioc_types: A list of IOC types to filter by (e.g., 'domain', 'md5').
            ioc_value: The specific value of the IOC to search for.
            filter_strategy: The filtering strategy to apply. Can be 'Equal' for
                server-side filtering or other values for client-side
                filtering.
            limit: The maximum number of IOCs to return.
            page_size: The number of items to retrieve per page in API requests.

        Returns:
            A list of objects, each representing an uploaded IOC that matches
            the search criteria.
        """
        page_size = self.optimize_page_size(page_size, limit, filter_strategy)

        ioc_ids_stream = self.get_ioc_ids_by_types_and_value(
            ioc_types=ioc_types,
            ioc_value=(
                ioc_value
                if filter_strategy == FilterStrategy.Equal.value and ioc_value
                else None
            ),
            page_size=page_size,
        )

        ioc_details_stream = self.get_object_details_by_ids(
            ids_producer=ioc_ids_stream,
            details_request_stream=self.get_ioc_details_by_ids,
            to_data_model=self.parser.build_siemplify_indicator_obj,
            page_size=page_size,
        )

        filtered_ioc = self.filter_data_stream(
            extractor=lambda ioc: ioc.value,
            value=ioc_value,
            filter_strategy=filter_strategy,
            objects=ioc_details_stream,
        )
        return list(itertools.islice(filtered_ioc, limit))

    def filter_indicator_ids(self, indicator_ids, filter_logic, value, limit=None):
        """
        Filter devices by provided filter field and value
        :param indicator_ids {list} List of Indicators objects
        :param value {str} value to compare
        :param filter_logic {str} value to search
        :param limit {int}
        return {list} List of filtered devices
        """
        found_results = []

        for indicator in indicator_ids:
            indicator_value = indicator.split(":")[-1]
            if FILTER_STRATEGY_MAPPING[filter_logic](indicator_value, value):
                found_results.append(indicator)

            if limit and len(found_results) >= limit:
                break

        return found_results

    def filter_devices(self, devices, filter_strategy, value, limit=None):
        """
        Filter devices by provided filter field and value
        :param devices {list} List of Device objects
        :param value {str} value to compare
        :param filter_strategy {str} value to search
        :param limit {int}
        return {list} List of filtered devices
        """
        found_results = []

        for device in devices:
            if FILTER_STRATEGY_MAPPING[filter_strategy](device.hostname, value):
                found_results.append(device)

            if limit and len(found_results) >= limit:
                break

        return found_results

    def get_detection_status(self, detection_ids):
        """
        Get detection status with the given ID.
        :param detection_ids: {list or str} The unique identifier of the detection.
        :return: {str} Detection status.
        """
        detection_ids = (
            detection_ids if isinstance(detection_ids, list) else [detection_ids]
        )

        response = self.session.post(
            self._get_full_url("detection_details"), json={"ids": detection_ids}
        )
        self.validate_response(
            response,
            f"Unable to get status of the detection with identifier "
            f"{', '.join(detection_ids)}",
        )

        resource = self.parser.get_resources(response.json())

        if resource:
            return self.parser.get_detection_status(resource[0])

        raise CrowdStrikeManagerError(
            "Unable to get status of the detection with identifier "
            f"{', '.join(detection_ids)}"
        )

    def add_comment_to_detection(self, comment, detection_ids, status):
        """
        Add a comment to the specified detection.
        :param comment: {str} The comment that will add information about the detection.
        :param detection_ids: {list or str} The unique identifier of the detection.
        :param status: {str} The status of the detection.
        :return: {bool} True if successful, raise exception otherwise.
        """
        detection_ids = (
            detection_ids if isinstance(detection_ids, list) else [detection_ids]
        )

        json_payload = {"ids": detection_ids, "comment": comment, "status": status}

        response = self.session.patch(
            self._get_full_url("detections"), json=json_payload
        )
        self.validate_response(
            response,
            f"Failed to add a comment to the detection with identifier "
            f"{', '.join(detection_ids)}",
        )

        return True

    def get_user_uuid(self, email):
        """
        Get User UUID with given Email.
        :param email: {str} User Email.
        :return: {list} User UUID.
        """
        response = self.session.get(
            self._get_full_url("user_uuids"), params={"uid": email}
        )
        self.validate_response(response, f"Unable to get UUID with email {email}")

        return self.parser.get_resources(response.json())

    def get_user_uuid_or_raise(self, email):
        """
        Get User UUID with given Email or raise.
        :param email: {str} User Email.
        :return: {list} List of uuids or raise.
        """
        uuids = self.get_user_uuid(email=email)

        if uuids:
            return uuids[0]

        raise CrowdStrikeManagerError(f"Unable to get UUID with email {email}")

    def update_detection(self, uuid, detection_ids, detection_status):
        """
        Update the status of a detection with the option to assign the detection to a Falcon user.
        :param uuid: {str} User UUID.
        :param detection_ids: {list} The unique identifiers of the detection.
        :param detection_status: {str} The status of the detection.
        :return: {bool} True if successful, raise exception otherwise.
        """
        data = {
            "ids": detection_ids,
            "status": detection_status,
            "assigned_to_uuid": uuid,
        }

        response = self.session.patch(
            self._get_full_url("detections"), json=self._get_valid_params(data)
        )
        self.validate_response(
            response, f"Failed to update detection {', '.join(map(str, detection_ids))}"
        )

        return True

    def _discover_streams(self, app_name):
        """
        Discover stream link and token to fetch detections
        :param app_name: App name with which stream will be created
        :return: Stream with link and token
        """
        params = {"appId": app_name}

        response = self.session.get(
            self._get_full_url("discover_streams"), params=params
        )
        self.validate_response(response, "Unable to discover streams")

        return self.parser.build_siemplify_stream(response.json())

    def get_stream_detections_with_limit(
        self,
        app_name: str,
        offset: int,
        limit: int,
    ) -> list[Detection]:
        """List detections from stream with limit.

        Args:
            app_name: App name with which stream will be created
            offset: Offset from which we will get detections
            limit: Limit of detections to fetch

        Returns:
            List up to limit of detections from the stream.
        """
        detections = []
        for detection in self.get_stream_detections(app_name, offset):
            if detection is None:
                continue

            detections.append(detection)

            if len(detections) >= limit:
                break

        return detections

    def get_stream_detections(
        self,
        app_name: str,
        offset: int,
        event_types: list[str] = None,
    ) -> Iterator[Detection | None]:
        """Yields a detection from stream.

        Args:
            app_name: App name with which stream will be created
            offset: Offset from which we will get detections
            event_types: List of event types to fetch

        Returns:
            Yield detections from stream or None if received empty response
        """
        stream = self._discover_streams(app_name=app_name)

        payload: dict[str, int | str] = {"offset": offset} if offset else {}
        if event_types is not None:
            payload["eventType"] = ",".join(event_types)

            if AUTH_ACTIVITY_AUDIT_EVENT_TYPE not in event_types:
                payload["eventType"] += f",{AUTH_ACTIVITY_AUDIT_EVENT_TYPE}"

        response = None

        try:
            response = self.session.get(
                stream.url,
                params=payload,
                stream=True,
                headers={
                    "Authorization": f"Token {stream.token}",
                    "Accepts": "application/json",
                },
                # The previous value was (5, 10), which caused the ReadTimeout error.
                # The new value is increased to 5 minutes (300 seconds)
                # for stable performance with streaming.
                timeout=(5, 300),
            )

            self._validate_stream_response(response)

            for stream_line in response.iter_lines():
                detection = None

                if stream_line.strip():
                    detection = self.parser.build_siemplify_detection_obj(
                        json.loads(stream_line)
                    )
                    if self.logger:
                        self.logger.info(
                            f"Received detection with offset- {detection.offset}"
                        )
                    if not self.parser.get_event_data(detection.raw_data):
                        if self.logger:
                            self.logger.info(
                                f"Skipping detection with offset {detection.offset}. "
                                f'Reason: "events" key is empty'
                            )
                        continue

                yield detection

        except Exception as e:
            raise CrowdStrikeManagerError(
                "Stream to fetch detections reaches timeout"
                if "Read Timed out" in str(e)
                else str(e)
            )

        finally:
            if response is not None:
                if self.logger:
                    self.logger.info("Closing the stream...")
                response.close()

    @staticmethod
    def _validate_stream_response(response, message="Response is not 200"):
        """
        Validate stream response and close if status is not 200
        :param response: Response object
        :param message: Message to raise exception with
        """
        if response.status_code != 200:
            response.close()
            raise CrowdStrikeManagerError(
                f"{message} (Status code: {response.status_code}): {response.text}"
            )

    def upload_ioc(
        self,
        ioc_type,
        ioc_value,
        platforms,
        severity,
        host_group_ids,
        action,
        comment=None,
        expiration_date=None,
    ):
        """
        Upload custom indicators that you want CrowdStrike to watch.
        :param ioc_type: {str} The type of the indicator. Valid types include:
                sha256: A hex-encoded sha256 hash string. Length - min: 64, max: 64.
                sha1: A hex-encoded sha1 hash string. Length - min 40, max: 40.
                md5: A hex-encoded md5 hash string. Length - min 32, max: 32.
                domain: A domain name. Length - min: 1, max: 200.
                ipv4: An IPv4 address. Must be a valid IP address.
                ipv6: An IPv6 address. Must be a valid IP address.
        :param ioc_value: {str} The string representation of the indicator.
        :param platforms: {list} list of the platforms related to the IOC
        :param severity: {str} IOC severity
        :param host_group_ids: {list} list of host group ids
        :param action: {str} param identifies which action will be enabled for this IOC: detect/block
        :param comment: {bool} IOC comment
        :param expiration_date: {str} The expiration date for the IOC
        :return: {void}
        """
        json_payload = {
            "comment": comment,
            "indicators": [
                {
                    "type": ioc_type,
                    "value": ioc_value,
                    "action": ACTION_TYPE_MAPPING[action],
                    "severity": severity,
                    "platforms": platforms,
                    "host_groups": host_group_ids,
                    "expiration": expiration_date,
                }
            ],
        }
        if not host_group_ids:
            json_payload["indicators"][0].update({"applied_globally": True})

        response = self.session.post(
            self._get_full_url("upload_ioc"), json=self._get_valid_params(json_payload)
        )
        self.validate_response(
            response, f"Unable to upload custom ioc {ioc_type}:{ioc_value}"
        )

    def get_custom_indicators(
        self, ioc_types=None, value=None, filter_logic=None, limit=None
    ):
        """
        Get custom indicators that CrowdStrike is watching.
        :param ioc_types: {list} The list of types for the indicator. Valid types include:
                sha256: A hex-encoded sha256 hash string. Length - min: 64, max: 64.
                sha1: A hex-encoded sha1 hash string. Length - min 40, max: 40.
                md5: A hex-encoded md5 hash string. Length - min 32, max: 32.
                domain: A domain name. Length - min: 1, max: 200.
                ipv4: An IPv4 address. Must be a valid IP address.
                ipv6: An IPv6 address. Must be a valid IP address.
        :param value: {str} The string representation of the indicator.
        :param filter_logic: {str} Filter logic. Can be equal or contains
        :param limit: {int} The max amount of indicators to return
        :return: {list} The indicators
        """
        params = {"types": ioc_types}

        ids = self._paginate_results(
            self._get_full_url("ioc_listing"),
            params=self._get_valid_params(params),
            limit=limit,
            error_msg="Unable to get custom indicators ids",
        )

        if not ids:
            return []

        if filter_logic and value:
            ids = self.filter_indicator_ids(ids, filter_logic, value, limit=limit)

        # Get the details of the indicators by the received ids
        indicators = self._paginate_results(
            self._get_full_url("ioc_endpoint"),
            params={"ids": ids},
            limit=limit,
            error_msg="Unable to get custom indicators",
        )

        return self.parser.build_results(
            indicators, "build_siemplify_indicator_obj", pure_data=True
        )

    def delete_ioc(self, ioc_id):
        """
        Delete ioc by ID
        :param ioc_id: {str} ioc ID
        :return: {void}
        """
        params = {"ids": ioc_id}

        response = self.session.delete(self._get_full_url("delete_ioc"), params=params)
        self.validate_response(response, f"Failed to delete the ioc with ID {ioc_id}.")

    def match_device_host_name(self, device, starts_with_name):
        """
        Check if hostname matches with device name
        :param device: {Device} instance
        :param starts_with_name: {str} The starting string of device name
        :return: [{Device}] if match results None otherwise
        """
        host_name = device.hostname.lower()
        starts_with = host_name.startswith(starts_with_name.lower())

        if not starts_with:
            return False

        if starts_with and len(host_name) == len(starts_with_name):
            return True

        return starts_with and host_name[len(starts_with_name)] == "."

    def get_devices_ran_on(self, ioc_type, value, limit=None):
        """
        Find hosts that have observed a given custom IOC.
        :param ioc_type: {str} The type of indicator from the list of supported indicator types. Valid types include:
            sha256: A hex-encoded sha256 hash string. Length - min: 64, max: 64.
            sha1: A hex-encoded sha1 hash string. Length - min 40, max: 40.
            md5: A hex-encoded md5 hash string. Length - min 32, max: 32.
            domain: A domain name. Length - min: 1, max: 200.
        :param value: {str} The actual string representation of your indicator.
        :param limit: {int} Max amount of devices to return
        :return: {list} The devices' details
        """
        params = {"type": ioc_type, "value": value}
        # NOTICE! The API returns 404 code when no devices are found for the indicator! So ignore 404
        ids = self._paginate_results(
            self._get_full_url("ioc_queries"),
            params=params,
            limit=limit,
            error_msg=f"Unable to get devices ran on for {ioc_type}:{value}",
            builtin_pagination=True,
            ignore_404=True,
        )

        if not ids:
            return []

        # NOTICE! The hosts can age out in the API, in such cases the request above will still return them, but the
        # request below will throw a 404 code! So ignore 404 codes in here
        devices = self._paginate_results(
            self._get_full_url("entities_devices"),
            params={"ids": ids},
            limit=limit,
            error_msg="Unable to search for devices",
            ignore_404=True,
        )

        return self.parser.build_results(
            devices, "build_siemplify_device_obj", pure_data=True
        )

    def get_detections(
        self,
        detection_id=None,
        status=None,
        date_updated=None,
        md5=None,
        severity=None,
        filename=None,
        timestamp=None,
        ioc_type=None,
        ioc_source=None,
        ioc_value=None,
        device_id=None,
        device_hostname=None,
        device_external_ip=None,
        device_local_ip=None,
        limit=None,
    ):
        """
        Get detections details
        :param detection_id: {int} The ID of the detection.
        :param status: {str} The current status of the detection. Values include new, in_progress, true_positive, false_positive, and ignored.
        :param date_updated: {str} The date of the most recent update to a detection. i.e: 2017-01-31T22:36:11Z.
        :param md5: {str} MD5 of the triggering process.
        :param severity: {int} Severity rating for the behavior. Value can be any integer between 1-100.
        :param filename: {str} File name of the triggering process.
        :param timestamp: {str} The time when the behavior detection occurred.
                          i.e: 2017-01-12T06:51:42Z.
        :param ioc_type: {str} The type of the triggering IOC. Values include hash_sha256, hash_md5,domain,filename,registry_key,command_line, and behavior.
        :param ioc_source: {str} Source that triggered an IOC detection. Values include library_load, primary_module, file_read, and file_write.
        :param ioc_value: {str} IOC value.
        :param device_id: {str} Device ID as seen by CrowdStrike.
        :param device_hostname: {str} Device host name.
        :param device_external_ip: {str} Device's external IP.
        :param device_local_ip: {str} The device's local IP address, with optional wildcards (*).
            As a detections parameter, this is the IP address at the time the detection occurred.
            To use wildcards, prefix the IP address with an asterisk (*) and enclose the IP address in single quotes.
        :param limit: {int} Max amount of devices to return
        :return: {json} The found detection details (list of dicts)
        """

        filter_data = {
            "detection_id": detection_id,
            "status": status,
            "date_updated": date_updated,
            "behaviors.md5": md5,
            "behaviors.severity": severity,
            "behaviors.filename": filename,
            "behaviors.timestamp": timestamp,
            "behaviors.ioc_type": ioc_type,
            "behaviors.ioc_source": ioc_source,
            "behaviors.ioc_value": ioc_value,
            "device.device_id": device_id,
            "device.hostname": device_hostname,
            "device.external_ip": device_external_ip,
            "device.local_ip": device_local_ip,
        }

        filter_data = self._get_valid_params(filter_data)

        # Filter query construction
        filter_query = "+".join(
            [f"{key}:'{value}'" for key, value in filter_data.items()]
        )
        url = f"{self.api_root}/detects/queries/detects/v1"

        response = self.session.get(url)
        self.validate_response(response, "Unable to get detections")

        ids = self._paginate_results(
            url,
            params={"filter": filter_query},
            limit=limit,
            error_msg="Unable to get detections ids",
        )

        if not ids:
            return []

        url = f"{self.api_root}/detects/entities/summaries/GET/v1"

        detections = self._paginate_results(
            url,
            method="POST",
            body={"ids": ids},
            limit=limit,
            error_msg="Unable to get detections",
        )
        return [
            self.parser.build_siemplify_detection_obj(detection)
            for detection in detections
        ]

    def close_detection(self, detection_id, show_in_ui=False):
        """
        Close detection in Crowdstrike Falcon
        :param detection_id: {str} Crowdstrike Falcon detection id
        :param show_in_ui: {bool} if False, hides detection in Crowdstrike Falcon
        :return: {bool} True if successful, raise exception otherwise.
        """
        data = {"ids": [detection_id], "show_in_ui": show_in_ui, "status": "closed"}
        response = self.session.patch(self._get_full_url("detections"), json=data)
        self.validate_response(response, f"Failed to close detection {detection_id}")

        return True

    @staticmethod
    def validate_response(
        response,
        error_msg="An error occurred",
        ignore_404=False,
        custom_response=False,
        handle_not_found=False,
    ):
        try:
            if ignore_404 and response.status_code == 404:
                return

            response.raise_for_status()

        except requests.HTTPError as error:
            if custom_response:
                if "error" in response.json().keys():
                    if custom_response:
                        if "Command not found" != response.json()["error"]:
                            raise CrowdStrikeSessionCreatedError(
                                response.json()["error"]
                            )

                elif response.json().get("errors"):
                    if custom_response:
                        if "Command not found" not in [
                            error_obj.get("message")
                            for error_obj in response.json().get("errors")
                        ]:
                            raise CrowdStrikeSessionCreatedError(
                                ", ".join(
                                    [
                                        error_obj.get("message")
                                        for error_obj in response.json().get("errors")
                                    ]
                                )
                            )

            if handle_not_found and response.status_code == 404:
                raise CrowdStrikeNotFoundError(
                    f"{error_msg}: {error} {error.response.content}"
                )

            if response.status_code == 415:
                raise CrowdStrikeUnsupportedType(
                    f"{error_msg}: {error} {error.response.content}"
                )

            if response.status_code == 400:
                error_msg = CrowdStrikeManager._get_error_payload(error, error_msg)
                raise CrowdStrikeBadRequestError(error_msg) from error

            raise CrowdStrikeManagerError(
                f"{error_msg}: {error} {error.response.content}"
            )

        if "error" in response.json().keys():
            if custom_response:
                if "Command not found" == response.json()["error"]:
                    raise CrowdStrikeManagerError(response.json()["error"])
            raise CrowdStrikeSessionCreatedError(response.json()["error"])

        elif response.json().get("errors"):
            if custom_response:
                if "Command not found" in [
                    error_obj.get("message")
                    for error_obj in response.json().get("errors")
                ]:
                    raise CrowdStrikeManagerError(
                        ", ".join(
                            [
                                error_obj.get("message")
                                for error_obj in response.json().get("errors")
                            ]
                        )
                    )

            if handle_not_found:
                if 404 in [
                    error_obj.get("code") for error_obj in response.json().get("errors")
                ]:
                    raise CrowdStrikeNotFoundError(
                        ", ".join(
                            [
                                error_obj.get("message")
                                for error_obj in response.json().get("errors")
                            ]
                        )
                    )
                if 400 in [
                    error_obj.get("code") for error_obj in response.json().get("errors")
                ]:
                    raise CrowdStrikeBadRequestError(f"{error_msg}")

            raise CrowdStrikeSessionCreatedError(
                ", ".join(
                    [
                        error_obj.get("message")
                        for error_obj in response.json().get("errors")
                    ]
                )
            )

    @staticmethod
    def _get_error_payload(error: requests.HTTPError, error_msg: str) -> str:
        try:
            response_payload = error.response.json()
            error = response_payload.get("error")
            errors = response_payload.get("errors")

        except json.JSONDecodeError:
            return f"{error_msg}: {error.response.text}"

        if error:
            return f"{error_msg}: {error}"

        if errors:
            error_string = ", ".join([error.get("message") for error in errors])
            return f"{error_msg}: {error_string}"

        return error_msg

    def update_ioc(
        self,
        ioc_id,
        expiration_date=None,
        detect_policy=True,
        source=None,
        description=None,
        severity=None,
    ):
        """
        Update ioc
        :param ioc_id: {str} ioc ID
        :param expiration_date: {str} The date until which the indicator should be valid for. This only applies to domain, ipv4, and ipv6 types.
        :param detect_policy: {bool} when the value is detected on a host enacted a detect policy, else none(This is equivalent to turning the indicator off)
        :param source: {str} The source where this indicator originated. This can be used for tracking where this indicator was defined. Limit 200 characters.
        :param description: {str} The friendly description of the indicator. Limit 200 characters.
        :param severity: {str} ioc severity
        :return: {void}
        """
        json_payload = {
            "indicators": [
                {
                    "id": ioc_id,
                    "source": source,
                    "action": POLICY_DEFAULT_FOR_DETECT if detect_policy else None,
                    "description": description,
                    "expiration": expiration_date,
                    "severity": (
                        IOC_DEFAULT_SEVERITY
                        if detect_policy and not severity
                        else severity
                    ),
                }
            ]
        }

        json_payload["indicators"] = [
            self._get_valid_params(item) for item in json_payload.get("indicators")
        ]
        response = self.session.patch(
            self._get_full_url("update_ioc"), json=json_payload
        )
        self.validate_response(
            response, f"Unable to update custom ioc with ID {ioc_id}"
        )
        return self.parser.get_resources(response.json())

    def get_processes_ran_on(
        self, ioc_type, value, device_id, device_name=None, limit=None
    ):
        """
        Search for processes associated with a custom IOC
        :param ioc_type: {str} The type of indicator from the list of supported indicator types. Valid types include:
            sha256: A hex-encoded sha256 hash string. Length - min: 64, max: 64.
            sha1: A hex-encoded sha1 hash string. Length - min 40, max: 40.
            md5: A hex-encoded md5 hash string. Length - min 32, max: 32.
            domain: A domain name. Length - min: 1, max: 200.
        :param value: {str} The actual string representation of your indicator.
        :param device_id: {str} The device ID you want to specifically check against.
        :param device_name: {str} The device name you want to specifically check against.
        :param limit: {int} The max amount of results to return
        :return: {json} The process' details
        """
        # NOTICE! The API returns 404 code when no processes are found for the indicator! So ignore 404
        params = {"type": ioc_type, "value": value, "device_id": device_id}
        ids = self._paginate_results(
            self._get_full_url("queries_processes"),
            params=params,
            limit=limit,
            error_msg=f"Unable to get processes ran on for {ioc_type}:{value}",
            builtin_pagination=True,
            ignore_404=True,
        )
        if not ids:
            return []

        # NOTICE! The processes can age out in the API, in such cases the request above will still return them, but the
        # request below will throw a 404 code! So ignore 404 codes in here
        processes = self._paginate_results(
            self._get_full_url("entities_processes"),
            params={"ids": ids},
            error_msg="Unable to search for processes",
            ignore_404=True,
        )

        return self.parser.build_results(
            raw_json=processes,
            method="build_siemplify_process",
            pure_data=True,
            hostname=device_name,
            indicator_value=value,
        )

    def get_processes_by_device_name(
        self, device_name: str, ioc_type: str, ioc_value: str, cid: str | None = None
    ) -> list[Process]:
        """Get processes by device name

        Args:
            device_name (str): device name (e.g. LP-ZIV)
            ioc_type (str): The type of indicator from the list of supported indicator
            types. Valid types include:
                sha256: A hex-encoded sha256 hash string. Length - min: 64, max: 64.
                sha1: A hex-encoded sha1 hash string. Length - min 40, max: 40.
                md5: A hex-encoded md5 hash string. Length - min 32, max: 32.
                domain: A domain name. Length - min: 1, max: 200.
                ipv4: An IPv4 address. Must be a valid IP address.
                ipv6: An IPv6 address. Must be a valid IP address.
            ioc_value (str): The actual string representation of your indicator.
            cid (str | None, optional): The ID of the customer.

        Returns:
            list[Process]: List of found processes model
        """
        results = []
        devices = self.search_devices(cid=cid, starts_with_name=device_name)

        if not devices:
            raise CrowdStrikeManagerError(f"Device {device_name} was not found")

        device_id = devices[0].device_id

        if device_id:
            results.extend(
                self.get_processes_ran_on(
                    ioc_type=ioc_type,
                    value=ioc_value,
                    device_id=device_id,
                    device_name=device_name,
                )
            )

        return results

    def contain_host_by_device_id(self, device_ids):
        """
        Contain(Quarantine) host by device ID.
        :param device_ids: {str or list} the ID of the host device.
        :return: {bool} Is success.
        """
        device_ids = device_ids if isinstance(device_ids, list) else [device_ids]

        response = self.session.post(
            self._get_full_url("devices_actions"),
            json={"ids": device_ids},
            params={"action_name": "contain"},
        )
        self.validate_response(response)

        return True

    def lift_containment_from_host_by_device_id(self, device_ids):
        """
        Lift containment from host by device ID.
        :param device_ids: {str or list} the ID of the host device.
        :return: {bool} Is success.
        """
        device_ids = device_ids if isinstance(device_ids, list) else [device_ids]

        response = self.session.post(
            self._get_full_url("devices_actions"),
            json={"ids": device_ids},
            params={"action_name": "lift_containment"},
        )
        self.validate_response(response)

        return True

    def get_alerts(
        self,
        severity: int | None,
        start_timestamp: int,
        limit: int,
        fetch_idp: bool = True,
        include_hidden_alerts: bool = True,
    ) -> list[AlertDetails]:
        """Get Alerts.

        Args:
            severity: filter by severity
            start_timestamp: filter by start timestamp
            limit: limit for results
            fetch_idp: Fetch Identity Protection detections if true, all else otherwise
            include_hidden_alerts: Include hidden alerts

        Returns:
            {[AlertDetails]} list of AlertDetails objects
        """

        params = {
            "filter": self.build_get_alerts_filters(
                severity=severity, start_timestamp=start_timestamp, fetch_idp=fetch_idp
            ),
            "limit": limit,
            "sort": "created_timestamp.asc",
            "include_hidden": include_hidden_alerts,
        }
        response = self.session.get(self._get_full_url("get_alerts"), params=params)
        self.validate_response(response)
        return self.get_alerts_details(self.parser.get_resources(response.json()))

    def get_modified_alerts(
        self,
        start_timestamp: datetime,
    ) -> list[AlertDetails]:
        """Get modified alerts since a specific timestamp.

        Args:
            start_timestamp: The starting timestamp to fetch modified alerts from.

        Returns:
            list[AlertDetails]: List of AlertDetails objects.
        """
        clean_ts = start_timestamp.isoformat(timespec="microseconds").replace(
            "+00:00", "000Z"
        )

        query_filter = f"updated_timestamp:>='{clean_ts}'"

        params = {
            "filter": query_filter,
            "sort": "updated_timestamp.asc",
        }

        response = self.session.get(self._get_full_url("get_alerts"), params=params)
        self.validate_response(response)

        alert_ids = self.parser.get_resources(response.json())

        if not alert_ids:
            return []

        return self.get_alerts_details(alert_ids)

    def get_alerts_details(self, ids: list[str]) -> list[AlertDetails]:
        """Get alerts details.

        Args:
            ids: {list} alerts' ids

        Returns:
            {[AlertDetails]} list of AlertDetails objects
        """
        if not ids:
            return []

        response = self.session.post(
            self._get_full_url("get_alerts_details"), json={"composite_ids": ids}
        )
        self.validate_response(response, handle_not_found=True)
        return self.parser.get_resources(
            response.json(), "build_siemplify_alert_details"
        )

    def search_detection(self, id_: str):
        """Get detection details.

        Args:
            id_: Detection id
        """
        response = self.session.post(
            self._get_full_url("get_alerts_details"), json={"composite_ids": [id_]}
        )
        self.validate_response(
            response,
            error_msg=(
                f"identity protection detection with ID {id_}"
                " wasn't found in Crowdstrike."
                " Please check the spelling."
            ),
            handle_not_found=True,
        )

    @staticmethod
    def build_get_alerts_filters(
        severity: int | None, start_timestamp: int, fetch_idp: bool = True
    ) -> str:
        """Build get alerts filters.

        Args:
            severity: filter by severity
            start_timestamp: filter by start timestamp
            fetch_idp: Fetch Identity Protection detections if true, all else otherwise

        Returns: query filter
        """
        created_datetime_str = datetime.fromtimestamp(start_timestamp / 1000).strftime(
            DATE_TIME_FORMAT
        )

        query_filter = ""
        if severity is not None:
            query_filter += f"severity:>={severity}"

        query_filter += f"+product{':' if fetch_idp else ':!'}'idp'"
        query_filter += "+status:['new','in_progress']"
        query_filter += f"+created_timestamp:>='{created_datetime_str}'"

        return query_filter

    def get_incidents(
        self, severity: int, last_success_datetime: str, limit: int
    ) -> list[IncidentDetails]:
        """Get Incidents

        Args:
            severity: Severity filter
            last_success_datetime: Date time filter
            limit: Limit for results

        Returns:
            List of IncidentDetails objects
        """

        params = {
            "filter": self.build_get_incidents_filters(
                end=last_success_datetime, fine_score=severity
            ),
            "sort": "end.asc",
            "limit": limit,
        }

        incident_ids = self._paginate_incidents_results(
            self._get_full_url("get_incidents"),
            params=params,
            limit=limit,
            error_msg=f"Unable to get incidents",
        )

        return self.get_incidents_details(incident_ids)

    def get_incidents_details(self, ids: list) -> list[IncidentDetails]:
        """Get alerts details

        Args:
            ids: Incident ids

        Returns:
            List of IncidentDetails objects
        """
        if not ids:
            return []

        response = self.session.post(
            self._get_full_url("get_incidents_details"), json={"ids": ids}
        )

        self.validate_response(response, handle_not_found=True)

        return sorted(
            self.parser.get_resources(
                response.json(), "build_siemplify_incident_details"
            ),
            key=lambda x: x.end_time,
            reverse=False,
        )

    @staticmethod
    def build_get_incidents_filters(end: str, fine_score: int):
        """Build get Incident filters

        Args:
            fine_score: Severity filter value
            end: End timestamp filter

        Returns:
            Filter query
        """
        query_filter = (
            f"end:>='{datetime.fromtimestamp(end / 1000).strftime(DATE_TIME_FORMAT)}'"
        )
        query_filter += "+status:!'40'"
        if fine_score is not None:
            query_filter += f"+fine_score:>='{fine_score}'"

        return query_filter

    def get_incident_behaviors(self, incident_id: str) -> list:
        """Get Incident Behaviors

        Args:
            incident_id: Incident id for which the behaviors has to be fetched

        Returns:
            List of Behaviors
        """
        params = {
            "filter": f"incident_id:'{incident_id}'",
            "limit": "400",
            "sort": "timestamp.desc",
        }
        response = self.session.get(
            self._get_full_url("get_incident_behaviors"), params=params
        )
        self.validate_response(response)
        return self.parser.get_resources(response.json())

    def get_incident_behaviors_details(self, ids: list) -> list:
        """Get Incident Behaviors details

        Args:
            ids: Behavior ids

        Returns:
            List of Incident Behavior Details objects
        """
        if not ids:
            return []

        response = self.session.post(
            self._get_full_url("get_incident_behaviors_details"), json={"ids": ids}
        )
        self.validate_response(response, handle_not_found=True)
        return self.parser.get_resources(
            response.json(), "build_siemplify_incident_behaviors_details"
        )

    def _paginate_incidents_results(
        self,
        url: str,
        params: dict = None,
        body: SingleJson = None,
        method: str = None,
        limit: int = None,
        error_msg: str = None,
    ) -> list:
        """Paginate the results of a get incidents

        Args:
            url: The url to send request to
            method: The method of the request
            params: The params of the request
            body: The JSON body of the request
            limit: The limit of the results to fetch
            error_msg: The error message to display on error

        Returns:
            List of results
        """
        method = method or "GET"
        error_msg = error_msg or "Unable to get results"
        params = params or {}

        params.update({"offset": 0, "limit": PAGE_SIZE})

        response = self.session.request(method, url, params=params, json=body)
        self.validate_response(response, error_msg)
        json_response = response.json()
        results = self.parser.get_resources(json_response)

        while True:
            if len(results) >= self.parser.get_page_total(json_response):
                break

            if limit and len(results) >= limit:
                return results[:limit]

            params.update({"offset": params["offset"] + PAGE_SIZE})

            response = self.session.request(method, url, params=params, json=body)
            self.validate_response(response, error_msg)
            json_response = response.json()

            results.extend(self.parser.get_resources(json_response))

        return results[:limit]

    def get_detections_connector(
        self,
        first_behavior,
        severity=None,
        confidence=None,
        limit=MAX_DETECTIONS_TO_FETCH,
        filters=None,
        sort_by="first_behavior",
        sort_order="asc",
    ):
        """
        Paginate the results of a job
        :param first_behavior: {str} Datetime for the first detection to fetch. Format:'2020-01-12T16:17:19Z'
        :param severity: {int} Severity rating for the behavior. Value can be any integer between 1-100.
        :param confidence: {int} Confidence rating for the behavior. Value can be any integer between 0-100.
        :param limit: {str} Maximum number of detections to fetch
        :param filters: {list} Filters for apply query
        :param sort_by: {str} The field name to sort data
        :param sort_order: {str} Sort direction
        :return: {list} List of Detections
        """
        payload = {
            "filter": self.prepare_filter(
                first_behavior, severity, confidence, filters
            ),
            "sort": f"{sort_by}.{sort_order}",
            "limit": max(limit, MAX_DETECTIONS_TO_FETCH),
        }
        payload_str = "&".join(f"{k}={v}" for k, v in payload.items())
        response = self.session.get(
            self._get_full_url("detections_connector"), params=payload_str
        )
        self.validate_response(response)

        resources = self.parser.get_resources(response.json())

        if self.logger:
            self.logger.info(f"Detections parameters {json.dumps(payload_str)}")
            self.logger.info(
                f"Received following detection IDs {json.dumps(resources)}"
            )

        return sorted(
            self.get_detection_details(resources),
            key=lambda elem: resources.index(elem.detection_id),
        )

    def prepare_filter(self, first_behavior, severity, confidence, filters=None):
        """
        Create filter by given parameters
        :param first_behavior: {str} Datetime for the first detection to fetch. Format:'2020-01-12T16:17:19Z'
        :param severity: {int} Severity rating for the behavior. Value can be any integer between 1-100.
        :param confidence: {int} Confidence rating for the behavior. Value can be any integer between 0-100.
        :param filters: {int} Filters for apply query
        :return: {str} Filter string
        """
        query_filter = "status:'new'"

        if first_behavior:
            query_filter += f"+first_behavior:>='{first_behavior}'"
        if severity:
            try:
                severity = int(severity)
                query_filter += f"+max_severity:>={severity}"
            except:
                query_filter += f"+max_severity_displayname:{SEVERITIES[SEVERITIES.index(severity.title()):]}"
        if confidence:
            query_filter += f"+max_confidence:>={confidence}"
        if filters:
            query_filter += f"+{'+'.join(filters)}"

        return urllib.parse.quote(query_filter)

    def get_detection_details(self, ids):
        """
        Paginate the results of a job
        :param ids: {list} Ids of detections to load details
        :return: {list} List of DetectionDetails
        """
        if not ids:
            return []

        response = self.session.post(
            self._get_full_url("detection_details"), json={"ids": ids}
        )
        self.validate_response(response)

        return self.parser.get_resources(
            response.json(), "build_siemplify_detection_detail"
        )

    def _paginate_results(
        self,
        url,
        params=None,
        body=None,
        method=None,
        limit=None,
        error_msg=None,
        builtin_pagination=False,
        ignore_404=False,
        for_hosts=False,
    ):
        """
        Paginate the results of a job
        :param url: {str} The url to send request to
        :param method: {str} The method of the request
        :param params: {dict} The params of the request
        :param body: {json} The JSON body of the request
        :param limit: {int} The limit of the results to fetch
        :param error_msg: {str} The error message to display on error
        :return: {list} List of results
        """
        method = method or "GET"
        error_msg = error_msg or "Unable to get results"
        params = params or {}

        params.update(
            {
                "offset": None if builtin_pagination else 0,
                "limit": 1000 if for_hosts else PAGE_SIZE,
            }
        )

        results = []

        while True:
            response = self.session.request(method, url, params=params, json=body)
            self.validate_response(response, error_msg, ignore_404=ignore_404)
            json_response = response.json()

            current_page_results = self.parser.get_resources(json_response)
            if not current_page_results:
                break

            results.extend(current_page_results)

            if builtin_pagination:
                if not self.parser.get_next_page_cursor(json_response):
                    break
            else:
                if len(results) >= self.parser.get_page_total(json_response):
                    break

            if (limit and len(results) >= limit) or for_hosts:
                return results[:limit]

            if builtin_pagination:
                params.update({"offset": self.parser.get_page_offset(json_response)})
            else:
                params.update({"offset": params["offset"] + PAGE_SIZE})

        return results[:limit] if limit else results

    def offset_pagination_generator(
        self,
        *args,
        page_size: int = MAX_PAGE_SIZE,
        **kwargs,
    ) -> Generator[Any, None, None]:
        """A generator that handles offset-based pagination for API requests.

        This method wraps `request_results_generator` and configures it to use
        an `OffsetPaginationStrategy`.

        Args:
            *args: Positional arguments to be passed to `request_results_generator`.
            page_size: The number of items to retrieve per page.
            **kwargs: Keyword arguments to be passed to `request_results_generator`.

        Yields:
            A generator of results from the paginated API requests.
        """
        yield from self.request_results_generator(
            *args,
            pagination_strategy=OffsetPaginationStrategy(limit=page_size),
            **kwargs,
        )

    def token_pagination_generator(
        self,
        *args,
        page_size: int = MAX_PAGE_SIZE,
        **kwargs,
    ) -> Generator[Any, None, None]:
        """A generator that handles token-based pagination for API requests.

        This method wraps `request_results_generator` and configures it to use
        a `TokenPaginationStrategy`.

        Args:
            *args: Positional arguments to be passed to `request_results_generator`.
            page_size: The number of items to retrieve per page.
            **kwargs: Keyword arguments to be passed to `request_results_generator`.

        Yields:
            A generator of results from the paginated API requests.
        """
        yield from self.request_results_generator(
            *args,
            pagination_strategy=TokenPaginationStrategy(limit=page_size),
            **kwargs,
        )

    def request_results_generator(
        self,
        url: str,
        method: str = "GET",
        *,
        params: dict[str, Any] = None,
        body: dict[str, Any] = None,
        error_msg: str = "Unable to get results",
        pagination_strategy: PaginationStrategy = None,
    ) -> Generator[Any, None, None]:
        """A generic generator for making paginated API requests.

        This function handles the logic of making repeated requests to an API
        endpoint, extracting results, and managing pagination state based on the
        provided strategy.

        Args:
            url: The URL of the API endpoint.
            method: The HTTP method to use for the request.
            params: A dictionary of query parameters for the request.
            body: A dictionary representing the JSON body for the request.
            error_msg: The error message to raise if a request fails.
            pagination_strategy: An object that defines the pagination logic.

        Yields:
            A generator of results from the paginated API requests.
        """
        params = params or {}

        if pagination_strategy is not None:
            pagination_initial_state = pagination_strategy.get_initial_state()
            params.update(pagination_initial_state)

        while True:
            response = self.session.request(method, url, params=params, json=body)
            self.validate_response(response, error_msg)

            json_response = response.json()

            current_page_results = self.parser.get_resources(json_response)
            if not current_page_results:
                break

            yield from current_page_results

            if not (
                pagination_strategy
                and pagination_strategy.has_next_page(
                    last_page_count=len(current_page_results),
                    total=self.parser.get_page_total(json_response),
                )
            ):
                break

            pagination_strategy.update_next_page_token(response)

            params.update(pagination_strategy.get_next_page_state())

    def get_vulnerability_ids(
        self,
        cid: str | None = None,
        aid: list | None = None,
        severity: list | None = None,
        limit: int | None = None,
    ) -> list[str]:
        """Get vulnerability ids

        Args:
            cid (str | None): The ID of the customer.
            aid (list | None): Ids of vulnerabilities
            severity (list | None): Ids of severity filter for vulnerabilities
            limit (int | None): Maximum number of ids to return

        Returns:
            list[str]: list of ids.
        """
        filter_data = {"aid": aid, "cve.severity": severity or None, "status": STATUS}

        if cid:
            filter_data["cid"] = cid

        return self._paginate_vulnerability_results(
            self._get_full_url("vulnerability_ids"),
            params={
                "filter": self.get_query_filter(self._get_valid_params(filter_data))
            },
            limit=limit,
        )

    def get_vulnerabilities_detailed_information(self, vulnerability_ids):
        """
        Get vulnerabilities detailed information by ids. Max ids = 400
        :param vulnerability_ids: {list} Ids for vulnerabilities
        :return: {list} List of Vulnerabilities
        """
        params = {"ids": vulnerability_ids}
        response = self.session.get(
            self._get_full_url("vulnerability_details"), params=params
        )
        self.validate_response(response)
        return self.parser.build_results(
            raw_json=response.json(), method="build_vulnerability_detail_obj"
        )

    def get_vulnerabilities(self, vulnerability_ids):
        """
        Get vulnerability details
        :param vulnerability_ids: {list} Ids for vulnerabilities
        :return: {list} List of VulnerabilityDetail
        """
        vulnerability_details = []
        for vulnerability_ids_chunk in [
            vulnerability_ids[x : x + MAX_PROCESSED_IDS_PER_REQUEST]
            for x in range(0, len(vulnerability_ids), MAX_PROCESSED_IDS_PER_REQUEST)
        ]:
            vulnerability_details.extend(
                self.get_vulnerabilities_detailed_information(
                    vulnerability_ids=vulnerability_ids_chunk
                )
            )

        return vulnerability_details

    def get_remediation_details(self, ids):
        """
        Get remediation details
        :param ids: {list} Ids of remediation
        :return: {list} List of RemediationDetails
        """
        params = {"ids": ids}
        response = self.session.get(
            self._get_full_url("remediation_details"), params=params
        )
        self.validate_response(response)
        return self.parser.build_results(
            raw_json=response.json(), method="build_remediation_detail_obj"
        )

    def _paginate_vulnerability_results(
        self, url, params=None, method=None, limit=None
    ):
        """
        Paginate the results of a job
        :param url: {str} The url to send request to
        :param method: {str} The method of the request
        :param params: {dict} The params of the request
        :param limit: {int} The limit of the results to fetch
        :return: {list} , {int} List of results and total from endpoint
        """
        method = method or "GET"
        params = params or {}

        params.update(
            {
                "limit": min(
                    limit or MAX_PROCESSED_IDS_PER_REQUEST,
                    MAX_PROCESSED_IDS_PER_REQUEST,
                )
            }
        )

        response = json_response = None
        vulnerability_ids = []

        while True:
            if limit and len(vulnerability_ids) >= limit:
                break
            if response and json_response:
                after_page = self.parser.get_after_page(json_response)
                if not after_page:
                    break
                params.update({"after": after_page})

            response = self.session.request(method, url, params=params)
            self.validate_response(response)

            json_response = response.json()

            vulnerability_ids.extend(self.parser.get_resources(json_response))
        total = self.parser.get_page_total(json_response) if json_response else 0
        return vulnerability_ids[:limit], total

    def get_ioc_id(self, ioc_value):
        """
        Get ioc ID by value
        :param ioc_value: {str} ioc value
        :return: {list} List of ioc IDs
        """
        params = {"filter": f"value:'{ioc_value}'"}

        response = self.session.get(self._get_full_url("get_ioc_id"), params=params)
        self.validate_response(response)
        return self.parser.get_resources(response.json())

    @staticmethod
    def build_ioc_filters(types, filter_value=None, filter_logic=None):
        """
        Build ioc filters
        :param types: {list} list of ioc types
        :param filter_value: {str} ioc value
        :param filter_logic: {str} filter logic that needs to be applied
        :return: {str} ioc filters
        """
        filters_string = ",".join([f'type:"{type}"' for type in types])

        if filter_value and filter_logic == FilterStrategy.Equal.value:
            filters_string += f'+ value:"{filter_value}"'

        return filters_string

    def get_iocs(self, ids, filter_value=None, filter_logic=None):
        """
        Get IOCs by provided ids
        :param ids: {list} list of ids
        :param filter_value: {str} ioc value for filtering
        :param filter_logic: {str} filter logic that needs to be applied
        :return: {list} list of CustomIndicator objects
        """
        params = {"ids": ids}

        iocs = self._paginate_results(
            self._get_full_url("get_iocs"),
            params=params,
            error_msg="Failed to get IOCs",
        )

        iocs_objects = self.parser.build_results(
            iocs, "build_siemplify_indicator_obj", pure_data=True
        )

        if filter_value and filter_logic == FilterStrategy.Contains.value:
            iocs_objects = [
                ioc
                for ioc in iocs_objects
                if FILTER_STRATEGY_MAPPING[filter_logic](ioc.value, filter_value)
            ]

        return iocs_objects

    def get_host_group_by_name(self, name):
        """
        Get host group by name
        :param name: {str} host group name
        :return: {HostGroup} HostGroup object
        """
        host_groups = self._paginate_results(
            self._get_full_url("get_host_groups"), error_msg="Failed to get host groups"
        )

        host_group_objects = self.parser.build_results(
            host_groups, "build_host_group_object", pure_data=True
        )
        return next(
            (
                host_group_object
                for host_group_object in host_group_objects
                if host_group_object.name == name
            ),
            None,
        )

    def get_devices_login_histories(
        self, ids: list[str], cid: str | None = None
    ) -> list[LoginHistory]:
        """Get login histories for devices

        Args:
            ids (list[str]): list of device ids
            cid (str | None): The ID of the customer.

        Returns:
            [LoginHistory]: list of LoginHistory objects.
        """
        if not ids:
            return []

        headers = {}
        if cid:
            headers = {"X-CS-CUSTID": cid}

        results = []
        for i in range(0, len(ids), CHUNK_SIZE):
            chunk = ids[i : i + CHUNK_SIZE]
            payload = {"ids": chunk}

            response = self.session.post(
                self._get_full_url("get_devices_login_histories"),
                json=payload,
                headers=headers,
            )
            self.validate_response(response)
            results.extend(
                self.parser.build_results(
                    response.json(),
                    "build_login_history_object"
                )
            )

        return results

    def get_devices_online_states(self, ids: list[str]) -> list[OnlineState]:
        """
        Get online states for devices
        :param ids: {[str]} list of device ids
        :return: {[OnlineState]} list of OnlineState objects
        """
        if not ids:
            return []

        results = []
        for i in range(0, len(ids), CHUNK_SIZE):
            chunk = ids[i : i + CHUNK_SIZE]
            params = {"ids": chunk}

            response = self.session.get(
                self._get_full_url("get_devices_online_states"),
                params=params
            )
            self.validate_response(response)
            results.extend(
                self.parser.build_results(response.json(), "build_online_state_object")
            )

        return results

    def update_alert(
        self,
        alert_id: str,
        status: str | None = None,
        verdict: str | None = None,
        assign_to: str | None = None,
    ) -> None:
        """Update alert

        Args:
            alert_id: {str} alert id
            status: {str | None} status to assign
            verdict: {str | None} verdict to assign
            assign_to: {str | none} name to assign

        Returns:
            None
        """
        data = {"composite_ids": [alert_id], "action_parameters": []}

        if assign_to == UNASSIGN:
            data.get("action_parameters").append({"name": "unassign", "value": ""})
        elif assign_to:
            data.get("action_parameters").append(
                {"name": "assign_to_name", "value": assign_to}
            )

        if DETECTION_STATUS_MAPPING.get(status):
            data.get("action_parameters").append(
                {"name": "update_status", "value": DETECTION_STATUS_MAPPING.get(status)}
            )
        if VERDICT_MAPPING.get(verdict):
            data.get("action_parameters").append(
                {"name": "add_tag", "value": VERDICT_MAPPING.get(verdict)}
            )

        response = self.session.patch(self._get_full_url("update_alerts"), json=data)
        self.validate_response(response)

    def update_alert_detail(self, comment, detection_id):
        """Add a comment to the specified identity protection detection.

        Args:
            comment: The comment that will be added to the detection.
            detection_id: Detection Id

        Returns:
            Boolean Value
        """
        self.search_detection(detection_id)

        data = {
            "ids": [detection_id],
            "action_parameters": [{"name": "append_comment", "value": comment}],
        }

        response = self.session.patch(self._get_full_url("update_alert"), json=data)
        self.validate_response(response)

    def upload_file(
        self, file_path: str, comment: str, is_confidential: bool, password: str
    ):
        """
        Upload a file for further analysis
        :param file_path: {str} The path of the file to analyze
        :param comment: {str} Comment for uploading file
        :param is_confidential: {bool} Should the file data be treated as confidential
        :param password: {str} Password that would need to be used, when working with Adobe or Office files.
        :return: {str} The hash of the uploaded file
        """
        with open(file_path, "rb") as file:
            url = self._get_full_url("upload_file")

            data = MultipartEncoder(
                fields={
                    "file_name": file_path,
                    "comment": comment,
                    "is_confidential": "true" if is_confidential else "false",
                    "password": password,
                    "sample": (file_path, file, "multipart/form-data"),
                }
            )

            headers = self.session.headers.copy()
            headers.update({"Content-Type": data.content_type})

            response = self.session.post(url, data=data, headers=headers)

        self.validate_response(response, custom_response=True)
        return response.json()["resources"][0]["sha256"]

    def upload_archive(
        self, file_path: str, comment: str, is_confidential: bool, password: str
    ):
        """
        Upload an archive for further analysis
        :param file_path: {str} The path of the file to analyze
        :param comment: {str} Comment for uploading file
        :param is_confidential: {bool} Should the file data be treated as confidential
        :param password: {str} Password that would need to be used, when working with archive files.
        :return: {str} The hash of the uploaded file
        """
        with open(file_path, "rb") as file:
            url = self._get_full_url("upload_archive")

            data = MultipartEncoder(
                fields={
                    "name": file_path,
                    "comment": comment,
                    "is_confidential": "true" if is_confidential else "false",
                    "password": password,
                    "file": (file_path, file, "multipart/form-data"),
                }
            )

            headers = self.session.headers.copy()
            headers.update({"Content-Type": data.content_type})

            response = self.session.post(url, data=data, headers=headers)
            self.logger.info(f"Response - {response.json()}")
            archive_hash = response.json()["resources"][0]["sha256"]
            status = response.json()["resources"][0]["status"]

            retry = 0
            while status != "done":
                sleep(RETRY_INTERVAL)
                if status == "error":
                    if retry >= MAX_RETRIES:
                        raise CrowdStrikeManagerError(
                            response.json()["resources"][0]["error"]
                        )
                    retry += 1

                url = self._get_full_url("get_archive")
                query_params = {"id": archive_hash}
                response = self.session.get(url, params=query_params)
                self.validate_response(response)
                status = response.json()["resources"][0]["status"]

        self.validate_response(response)
        return response.json()["resources"][0]["sha256"]

    def get_archive_files(
        self, archive_hash: str, start_time: int, script_timeout: int
    ):
        """
        Extract files from uploaded archive and fetch extracted files info
        :param archive_hash: {str} payload for submission
        :param start_time: {int} Action start time
        :param script_timeout: {int} Action script timeout
        """

        url = self._get_full_url("extract_archive")
        data = {"extract_all": True, "sha256": archive_hash}

        response = self.session.post(url, json=data)
        self.validate_response(response)

        status = response.json()["resources"][0]["status"]
        extraction_id = response.json()["resources"][0]["id"]

        while status != "done":
            if status == "error":
                raise CrowdStrikeManagerError(response.json()["resources"][0]["error"])

            if is_approaching_timeout(start_time, script_timeout):
                raise CrowdStrikeTimeoutError()

            url = self._get_full_url("extract_archive")
            query_params = {"id": extraction_id}

            response = self.session.get(url, params=query_params)
            self.logger.info(f"Response - {response.json()}")
            self.validate_response(response)
            status = response.json()["resources"][0]["status"]

        url = self._get_full_url("extract_archive")
        query_params = {"include_files": True, "id": extraction_id}

        response = self.session.get(url, params=query_params)

        if not response.json()["resources"]:
            raise CrowdStrikeNotFoundError(
                f"Archive extraction data with id {extraction_id} isn't found"
            )

        return self.parser.build_file_objects(response.json()["resources"][0]["files"])

    def submit_for_analysis(self, submission_data):
        """
        Submit entity for analysis
        :param submission_data: {dict} payload for submission
        """

        url = self._get_full_url("submit_for_analysis")
        response = self.session.post(url, json={"sandbox": [submission_data]})
        self.validate_response(response, custom_response=True)

        return response.json()["resources"][0]["id"]

    def filter_submissions(self, _filter: str):
        """
        Filter existing submissions
        :param _filter: {str} filter to apply on list submissions
        """
        url = self._get_full_url("filter_submissions")
        query_dict = {"filter": _filter}

        response = self.session.get(url, params=query_dict)
        self.validate_response(response)

        return response.json()["resources"]

    def get_submissions(self, ids: list[str]) -> list[SubmissionData]:
        """
        List existing submissions
        :param ids: {str} ids for which to return submissions
        """

        url = self._get_full_url("get_submissions")
        query_string = "?ids=" + "&ids=".join(ids)

        self.logger.info(f"Query -> {query_string}")

        response = self.session.get(url + query_string)
        self.validate_response(response)

        self.logger.info(f"Response -> {response.json()}")

        return self.parser.build_submissions_data(response.json()["resources"])

    def get_submission_reports(self, ids: list[str]):
        """
        Get submission reports
        :param ids: {str} ids for which to return submissions
        """

        url = self._get_full_url("get_submission_reports")
        query_string = "?ids=" + "&ids=".join(ids)

        response = self.session.get(url + query_string)
        self.logger.info(f"Response - {response.json()}")
        self.validate_response(response)

        return self.parser.build_submission_reports(response.json()["resources"])

    def search_incident(self, incident_id: str) -> IncidentDetails:
        """Search for an incident in crowdstrike

        Args:
            incident_id: Id of the incident

        Returns:
            An incident object
        """
        payload = {"ids": [incident_id]}

        response = self.session.post(
            self._get_full_url("get_incidents_details"), json=payload
        )

        self.validate_response(
            response,
            error_msg=(
                f"Incident with ID {incident_id} wasn't found in Crowdstrike."
                " Please check the spelling"
            ),
        )

        return self.parser.get_resources(
            response.json(), "build_siemplify_incident_details"
        )[0]

    def get_uuid(self, assign_to: str, cid: str | None = None) -> str:
        """To search a user in corwdstrike.

        Args:
            assign_to (str): The user that needs to be searched.
            cid (str): The ID of the customer

        Returns:
            str: Unique identifier of the given user.
        """
        error_msg = (
            f"User {assign_to} wasn't found in Crowdstrike. Please check the spelling."
        )
        if assign_to.lower() == UPDATE_INCIDENT_USER_UNASSIGN_CODE:
            return UPDATE_INCIDENT_USER_UNASSIGN_CODE

        elif "@" in assign_to:
            payload = {
                "filter": self.prepare_get_uuid_filter(assign_to=assign_to, cid=cid)
            }
        elif len(assign_to.split()) > 1:
            first_name = assign_to.split()[0]
            last_name = assign_to.split()[1]
            payload = {
                "filter": self.prepare_get_uuid_filter(
                    first_name=first_name, last_name=last_name, cid=cid
                )
            }
        else:
            raise Exception(error_msg)

        response = self.session.get(self._get_full_url("search_user"), params=payload)
        self.validate_response(response, error_msg=error_msg)

        return self.parser.get_resources(response.json())

    @staticmethod
    def prepare_get_uuid_filter(
        first_name: str = None,
        last_name: str = None,
        assign_to: str = None,
        cid: str | None = None,
    ) -> str:
        """Create filter by given parameters

        Args:
            first_name: First name of the user
            last_name: Last name of the user
            assign_to: Raw input

        Returns:
            Filter string
        """
        query_filter: str = ""
        if first_name and last_name:
            query_filter = f"first_name:'{first_name}' + last_name:'{last_name}'"
        if assign_to:
            query_filter = f"uid:'{assign_to}'"

        if cid:
            query_filter += f"+cid:'{cid}'"

        return query_filter

    def update_incident(
        self, incident_id: str, id_status: str, assign_to: str, cid: str | None = None
    ) -> None:
        """Update the incident using data provided by the end user.

        Args:
            incident_id (str): Incident id.
            id_status: Status of the incident id.
            assign_to: The user to whom the incident would be assigned.
            cid (str | None): ID of the customer.
        """
        self.search_incident(incident_id)

        payload = {"action_parameters": [], "ids": [incident_id]}

        if id_status is not None:
            if id_status.lower() in UPDATE_INCIDENT_STATUS_MAPPING:
                payload.get("action_parameters").append(
                    {
                        "name": "update_status",
                        "value": UPDATE_INCIDENT_STATUS_MAPPING.get(id_status.lower()),
                    }
                )

        if assign_to is not None:
            uuid = self.get_uuid(assign_to, cid)

            if not uuid:
                raise CrowdStrikeNotFoundError(
                    'Either specified Customer ID or "Assign To" value wasn\'t found '
                    "in CrowdStrike. Please check the spelling."
                )

            if uuid == UPDATE_INCIDENT_USER_UNASSIGN_CODE:
                payload.get("action_parameters").append(
                    {"name": UPDATE_INCIDENT_USER_UNASSIGN_CODE}
                )
            else:
                payload.get("action_parameters").append(
                    {"name": "update_assigned_to_v2", "value": uuid[0]}
                )

        response = self.session.post(
            self._get_full_url("update_incident"), json=payload
        )
        self.validate_response(response)

    def add_incident_comment(self, comment: str, incident_id: str) -> None:
        """Add a comment to the specified incident.

        Args:
            comment: The comment that will add to the incident.
            incident_id: Incident id
        """
        self.search_incident(incident_id)

        data = {
            "ids": [incident_id],
            "action_parameters": [{"name": "add_comment", "value": comment}],
        }

        response = self.session.post(
            self._get_full_url("add_incident_comment"), json=data
        )

        self.validate_response(response)

    def start_on_demand_scan(
        self,
        file_paths_to_scan: list[str],
        file_paths_to_exclude: list[str],
        cpu_priority: int,
        description: str,
        quarantine_hosts: bool,
        endpoint_notification: bool,
        sensor_ml_level_detection: int,
        sensor_ml_level_prevention: int,
        cloud_ml_level_detection: int,
        cloud_ml_level_prevention: int,
        max_scan_duration: int | None = None,
        host_group_id: str | None = None,
        host_id: str | None = None,
    ) -> OnDemandScanData:
        """Start on demand scan of a particular host.

        Args:
            host_id: {str} host id to start the scan for
            host_group_id: {str} host group id to start the scan for
            file_paths_to_scan: {list[str]} list of file paths to scan
            file_paths_to_exclude: {list[str]} list of file paths to exclude scan from
            cpu_priority: {int} cpu priority
            description: {str} scan description
            quarantine_hosts: {bool} to quarantine hosts or not for the scan
            endpoint_notification: {bool} whether to create notification or not
            sensor_ml_level_detection: {str} Sensor Anti-malware Detection Level
            sensor_ml_level_prevention: {str} Sensor Anti-malware Prevention Level
            cloud_ml_level_detection: {str} Cloud Anti-malware Detection Level
            cloud_ml_level_prevention: {str} Cloud Anti-malware Prevention Level
            max_scan_duration: {int} duration for scan

        Returns:
            OnDemandScanData
        """
        data = {
            "hosts": [] if not host_id else [host_id],
            "host_groups": [] if not host_group_id else [host_group_id],
            "scan_inclusions": file_paths_to_scan,
            "scan_exclusions": file_paths_to_exclude,
            "initiated_from": "falcon_adhoc",
            "cpu_priority": cpu_priority,
            "description": description,
            "quarantine": quarantine_hosts,
            "endpoint_notification": endpoint_notification,
            "sensor_ml_level_detection": sensor_ml_level_detection,
            "sensor_ml_level_prevention": sensor_ml_level_prevention,
            "cloud_ml_level_detection": cloud_ml_level_detection,
            "cloud_ml_level_prevention": cloud_ml_level_prevention,
            "max_duration": max_scan_duration,
            "pause_duration": PAUSE_DURATION,
        }

        response = self.session.post(self._get_full_url("on_demand_scan"), json=data)

        self.validate_response(response)

        return self.parser.build_on_demand_scan_data(response.json())

    def get_on_demand_scan_details(self, scan_id: str) -> OnDemandScanData:
        """Get On Demand Scan Details by scan id

        Args:
            scan_id: {str} Scan id to get details of scan

        Returns:
            OnDemandScanData
        """
        url = self._get_full_url("on_demand_scan")
        query_params = {"ids": scan_id}

        response = self.session.get(url, params=query_params)

        self.validate_response(response)

        return self.parser.build_on_demand_scan_data(response.json())

    def execute_responder_script(
        self, device_id: str, session_id: str, command: str
    ) -> str | None:
        """Execute responder script.

        Args:
            session_id (str): session_id
            command (str): command
            admin_command (bool): admin
            device_id (str): device id

        Returns:
            str | None: cloud_request_id
        """
        body = {
            "base_command": command.split()[0],
            "command_string": command,
            "device_id": device_id,
            "persist": True,
            "session_id": session_id,
        }
        url = self._get_full_url("responder_command_admin")
        response = self.session.post(url, json=body)
        self.validate_response(response, custom_response=True)
        results = self.parser.get_resources(
            response.json(), builder_method="get_cloud_request_id"
        )
        if not results:
            return None

        return results[0]

    def add_comment_to_alert(self, alert_id: str, comment: str) -> None:
        """Adds comment to the alert.

        Args:
            alert_id (str): Alert ID
            comment (str): Comment to be added in the alert.
        """
        data = {
            "composite_ids": [alert_id],
            "action_parameters": [{"name": "append_comment", "value": comment}],
        }
        url = self._get_full_url("update_alerts")
        response = self.session.patch(url=url, json=data)
        self.validate_response(response)

    def initiate_search_job(
        self,
        repository: str,
        query: str,
        time_frame: str,
        max_results: int,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> str:
        """Initiates a search job in the specified repository with the given query
        and time frame.

        Args:
            repository (str): The name of the repository to search in.
            query (str): The search query string.
            time_frame (str): The time frame for the search, which can be a preset
            value or "Custom".
            max_results (int): The maximum number of results to return.
            start_time (int | None): The start time in ISO format for custom time
            frames.
            end_time (int | None): The end time in ISO format for custom time frames.

        Returns:
            str: The ID of the created search job.

        Raises:
            CrowdStrikeManagerError: If the request to initiate the search job fails.
        """
        repo_value: str = REPOSITORY_MAP.get(repository)

        if not repo_value:
            raise CrowdStrikeManagerError(f"Unsupported repository: {repository}")

        url: str = self._get_full_url("query_jobs", repo_value=repo_value)
        time_range: TimeRange = resolve_time_frame(time_frame, start_time, end_time)
        query += f" | head({max_results})"

        payload: dict[str, str] = {
            "queryString": query,
            "start": str(time_range.start_ts),
            "end": str(time_range.end_ts) if end_time else "now",
        }

        response = self.session.post(url=url, json=payload)
        self.validate_response(response)

        return response.json()["id"]

    def get_search_job_results(
        self,
        job_id: str,
        repository: str,
    ) -> list[SearchEventsData]:
        """Retrieves the results of a search job from the specified repository.

        Args:
            job_id (str): The ID of the search job to retrieve results for.
            repository (str): The name of the repository where the search job was
            executed.

        Returns:
            list[SearchEventsData]: A list of SearchEventsData objects containing the
            search results.

        Raises:
            CrowdStrikeManagerError: If the request to retrieve the search job results
            fails.
        """
        repo_value: str = REPOSITORY_MAP.get(repository)

        if not repo_value:
            raise CrowdStrikeManagerError(f"Unsupported repository: {repository}")

        url: str = self._get_full_url("query_jobs", repo_value=repo_value)
        url += f"/{job_id}"

        response = self.session.get(url=url)
        self.validate_response(response)

        results = self.parser.parse_search_events(response.json(), job_id=job_id)

        return results

    def get_active_scan_ids(self, since_time: str) -> list[str]:
        """Fetch scan IDs for scans in 'running', 'scheduled', 'pending' status,
        optionally filtered by creation time.

        Args:
            since_time (str): Optional ISO 8601 timestamp to filter scans
            created on or after this time.

        Returns:
            list[str]: List of active scan IDs.
        """
        filter_query = (
            f"status:['running','scheduled','pending']+created_on:>='{since_time}'"
        )
        url = self._get_full_url("query_scans")
        params = {"filter": filter_query}
        response = self.session.get(url, params=params)
        self.validate_response(response)

        return response.json().get("resources", [])

    def hide_hosts_by_device_ids(self, device_ids: list[str]) -> None:
            """Hide hosts by device IDs.

            Args:
                device_ids (list[str]): A list of device IDs to hide.

            Raises:
                Exception: If the response validation fails.
            """
            device_ids = device_ids if isinstance(device_ids, list) else [device_ids]

            response = self.session.post(
                self._get_full_url("devices_actions"),
                json={"ids": device_ids},
                params={"action_name": "hide_host"},
            )

            self.validate_response(response)
