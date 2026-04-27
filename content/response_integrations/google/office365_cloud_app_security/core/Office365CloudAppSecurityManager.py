from __future__ import annotations
from typing import Any, Callable, List, Optional
from functools import wraps
from urllib.parse import urljoin

import requests
from requests import Response

from .Office365CloudAppSecurityParser import Office365CloudAppSecurityParser
from TIPCommon import filter_old_alerts
from .constants import (
    ALERT_ID_PARAM,
    ALERT_ID_LIST_PARAM,
    ALERT_PREFIX,
    API_ENDPOINTS,
    DEFAULT_PRODUCT_CODE,
    EQUAL,
    LIMIT_PER_REQUEST,
    RATE_LIMIT_STATUS_CODE
)


class Office365CloudAppSecurityManagerError(Exception):
    """
    General Exception for Office365CloudAppSecurityManager manager
    """

    pass


class Office365CloudAppSecurityConfigurationError(Exception):
    """
    Exception for Office365CloudAppSecurityManager in which credentials are incorrect
    """

    pass


class Office365CloudAppSecurityRateLimitingError(Exception):
    """
    Exception for Office365CloudAppSecurityManager if reached API rate limiting
    """

    pass


def retry_on_alert_id_prefix(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to retry a function call with modified alert IDs if a specific error
    occurs.

    This decorator wraps a function that interacts with the Office 365 Cloud App
    Security API. If the function raises an `Office365CloudAppSecurityManagerError`,
    the decorator checks if the error is related to alert IDs that might have a cleanup
    prefix. If so, it modifies the alert IDs by removing the prefix and retries the
    function call.

    Args:
        func (Callable[..., Any]): The callable function to be wrapped.

    Returns:
        Callable[..., Any]: A wrapped function that includes retry logic for handling
        alert ID prefixes.

    Raises:
        Office365CloudAppSecurityManagerError: If the original function raises an error
            and the retry conditions are not met (e.g., no cleanup prefix in alert IDs).
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)

        except Office365CloudAppSecurityManagerError as e:
            alert_id: str = kwargs.get(ALERT_ID_PARAM)
            alert_ids: list[str] = kwargs.get(ALERT_ID_LIST_PARAM, [alert_id])
            if not has_ca_prefix_in_alerts(alert_ids):
                raise e

            modified_kwargs: dict[str, str] = remove_ca_prefix_from_alert_ids(kwargs)

            return func(*args, **modified_kwargs)

    return wrapper


class Office365CloudAppSecurityManager:
    """
    Responsible for all Office365CloudAppSecurity operations functionality
    """

    def __init__(self, api_root, api_token, verify_ssl=False, siemplify=None):
        self.api_root = api_root
        self.api_token = api_token
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers = {}
        self.session.headers.update(
            {
                "Authorization": f"Token {self.api_token} ",
                "Content-Type": "application/json",
            }
        )

        self.cloud_app_parser = Office365CloudAppSecurityParser()
        self.siemplify = siemplify

    def test_connectivity(self):
        """
        Test connectivity to Office365CloudAppSecurity.
        :return:
        """
        url = API_ENDPOINTS["activities"].format(self.api_root)

        payload = {"limit": 1, "service": {"eq": DEFAULT_PRODUCT_CODE}}

        response = self.session.post(url, json=payload)

        self.validate_response(response, "Unable to connect to Cloud App Security")

        return True

    def list_files(self, filter_key, filter_logic, filter_value, limit=None):
        """
        Get files list
        :param filter_key: {str} Filter key
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Filtered items limit
        :return: {list}
        """
        url = API_ENDPOINTS["list_files"].format(self.api_root)

        if filter_logic and filter_logic == EQUAL and filter_value is not None:
            payload = {"filters": {filter_key: {"eq": [filter_value]}}}
        else:
            payload = {}
        raw_files = self._paginate_results(
            "POST", url, body=payload, limit=limit, err_msg="Unable to get files"
        )

        return self.cloud_app_parser.build_files_obj_list(
            raw_files, filter_key, filter_logic, filter_value, limit
        )

    @retry_on_alert_id_prefix
    def dismiss_alert(self, alert_id, comment=None):
        """
        Dismiss alert
        :param alert_id: {str} Alert Unique Identifier to dismiss
        :param comment: {str} A comment to explain why an alert is dismissed
        :return: {bool}
        """
        url = API_ENDPOINTS["dismiss_alert"].format(self.api_root, alert_id)

        payload = {}

        if comment:
            payload["comment"] = comment

        response = self.session.post(url, json=payload)

        self.validate_response(response, "Unable to connect to Cloud App Security")

        return True

    @retry_on_alert_id_prefix
    def bulk_resolve_alert(self, alert_id_list, comment=None):
        """
        Resolve alert
        :param alert_id_list: {str} Alert Unique Identifiers to resolve
        :param comment: {str} A comment to explain why alerts are resolved
        :return: {str} The number of resolved items
        """
        url = API_ENDPOINTS["resolve_alert"].format(self.api_root)

        payload = {"filters": {"id": {"eq": alert_id_list}}}

        if comment:
            payload["comment"] = comment

        response = self.session.post(url, json=payload)

        self.validate_response(response, "Unable to connect to Cloud App Security")

        return response.json().get("resolved")

    @retry_on_alert_id_prefix
    def close_alert(self, alert_id, state, reason_id, comment, response_key):
        """
        Close alert
        :param alert_id: {str} Alert Unique Identifier to close
        :param state: {str} The state of alert being closed
        :param reason_id: {int} The reason identifier to close the alert
        :param comment: {str} A comment to explain why alert is closed
        :param response_key" {str} Key for value to check in response
        :return:
        """
        url = API_ENDPOINTS["close_alert"].format(self.api_root, state)

        payload = {"filters": {"id": {"eq": [alert_id]}}}

        if comment:
            payload["comment"] = comment

        if reason_id is not None:
            payload["reasonId"] = reason_id

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Unable to close alert")

        if response.json().get(response_key, 0) == 0:
            raise Exception(
                f"alert with ID {alert_id} was not found in Microsoft Cloud App Security"
            )

    def get_alerts(
        self,
        service=None,
        policy=None,
        file=None,
        instance=None,
        ip=None,
        severity=None,
        resolution_status=None,
        only_read=False,
        start_time=None,
        end_time=None,
        risk=None,
        alert_type=None,
        source=None,
        limit=None,
        existing_ids: Optional[List[str]] = None,
    ):
        """
        Get alerts. Filter existing ids if provided.
        :param service: {str} The service filter value
        :param policy: {str} The policy filter value
        :param file: {str} The file filter value
        :param instance: {str} The instance filter value
        :param ip: {str} The ip filter value
        :param severity: {str} The severity filter value
        :param resolution_status: {str} The resolution_status filter value
        :param only_read: {str} The only_read filter value
        :param start_time: {str} The start time of date filter
        :param end_time: {str} The end time of date filter
        :param risk: {str} The risk filter value
        :param alert_type: {str} The alert_type filter value
        :param source: {str} The source filter value
        :param limit: {int} The limit of the results to fetch
        :param existing_ids: {[str]} List of existing alert ids to filter
        :return: {list} List of alerts
        """

        url = API_ENDPOINTS["get_alerts"].format(self.api_root)

        filters = {}

        if service:
            filters["entity.service"] = {"eq": service}

        if policy:
            filters["entity.policy"] = {"eq": policy}

        if file:
            filters["entity.file"] = {"eq": file}

        if instance:
            filters["entity.instance"] = {"eq": instance}

        if severity:
            filters["severity"] = {"eq": severity}

        if resolution_status:
            filters["resolutionStatus"] = {"eq": resolution_status}

        if only_read:
            filters["read"] = {"eq": only_read}

        if risk:
            filters["risk"] = {"eq": risk}

        if alert_type:
            filters["alertType"] = {"eq": alert_type}

        if ip:
            filters["entity.ip"] = {"eq": ip}

        if source:
            filters["source"] = {"eq": source}

        if start_time and end_time:
            filters["date"] = {"range": [{"start": start_time, "end": end_time}]}

        elif start_time:
            filters["date"] = {"gte": start_time}

        elif end_time:
            filters["date"] = {"lte": end_time}
        if instance:
            filters["instance"] = {"eq": instance}

        payload = {"filters": filters, "sortDirection": "asc", "sortField": "date"}
        raw_alerts = self._paginate_results(
            "POST", url, body=payload, limit=limit, err_msg="Unable to get alerts"
        )
        fetched_alerts = [
            self.cloud_app_parser.build_siemplify_alert_obj(activity)
            for activity in raw_alerts
        ]

        # filter already processed alerts
        if existing_ids:
            filtered_alerts = []
            start_offset = 0
            while fetched_alerts:
                start_offset += len(fetched_alerts)
                filtered_alerts.extend(
                    filter_old_alerts(
                        siemplify=self.siemplify,
                        alerts=fetched_alerts,
                        existing_ids=existing_ids,
                    )
                )
                if limit and (
                    len(filtered_alerts) >= limit or len(fetched_alerts) < limit
                ):
                    return filtered_alerts[:limit]
                raw_alerts = self._paginate_results(
                    "POST",
                    url,
                    body=payload,
                    start_offset=start_offset,
                    limit=LIMIT_PER_REQUEST,
                    err_msg=f"Unable to get alerts from offset {start_offset}",
                )
                fetched_alerts = [
                    self.cloud_app_parser.build_siemplify_alert_obj(activity)
                    for activity in raw_alerts
                ]
        else:
            filtered_alerts = fetched_alerts

        return filtered_alerts[:limit] if limit else filtered_alerts

    def get_alert_activities(self, alert_id):
        """
        Get Activities
        :param alert_id: {str} Alert Unique Identifier
        :return: {list} List of alerts
        """
        url = API_ENDPOINTS["get_activities"].format(self.api_root)

        payload = {"filters": {"activity.alertId": {"eq": alert_id}}}

        response = self.session.post(url, json=payload)
        self.validate_response(
            response, f"Unable to get activities for alert {alert_id}"
        )

        return [
            self.cloud_app_parser.build_siemplify_activity_obj(activity)
            for activity in response.json().get("data", [])
        ]

    def get_activities(self):
        """
        Get Activities
        :return: {list} List of alerts
        """
        url = API_ENDPOINTS["get_activities"].format(self.api_root)
        raw_activities = self._paginate_results(
            "POST", url, err_msg="Unable to get activities"
        )

        return [
            self.cloud_app_parser.build_siemplify_activity_obj(activity)
            for activity in raw_activities
        ]

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        start_offset=0,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param start_offset: {int} The start offset of the results to fetch
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if body is None:
            body = {}

        body.update({"skip": start_offset, "limit": str(LIMIT_PER_REQUEST)})

        response = self.session.request(method, url, params=params, json=body)

        self.validate_response(response, err_msg)
        results = response.json().get("data", [])

        while True:
            if limit and len(results) >= limit:
                break

            if not response.json().get("hasNext", False):
                break

            body.update({"skip": start_offset + len(results)})
            print(len(results))

            response = self.session.request(method, url, params=params, json=body)

            self.validate_response(response, err_msg)
            results.extend(response.json().get("data", []))

        return results[:limit] if limit else results

    def get_ip_related_activities(self, ip, product_name, time_frame, limit):
        """
        Get IP related activities
        :param ip: {str} The ip address
        :param product_name: {str} The product ID of the app connected to cloudapp security
        :param time_frame: {int} The time in hours to fetch activities that occurred according to the specified value of hours ago
        :param limit: {int} The limit of the results to fetch
        :return: {list} List of results
        """
        url = API_ENDPOINTS["get_ip_related_activities"].format(self.api_root)

        filters = {
            "ip.address": {"eq": ip},
            "date": {"gte_ndays": int((time_frame / 24))},
        }

        filters = self.apply_product_filter(filters, product_name)

        payload = {"filters": filters}

        try:
            raw_activities = self._paginate_results(
                "POST",
                url,
                body=payload,
                limit=limit,
                err_msg="Unable to get activities",
            )

        except requests.exceptions.RequestException as e:
            raise Office365CloudAppSecurityConfigurationError(
                "Credentials are incorrect, please check the configuration of the integration."
            )

        return [
            self.cloud_app_parser.build_siemplify_activity_obj(activity)
            for activity in raw_activities
        ]

    def get_user_related_activities(self, username, time_frame, product_name, limit):
        """
        Get User related activities
        :param username: {str} The user name
        :param time_frame: {int} The time in hours to fetch activities that occurred according to the specified value of hours ago
        :param product_name: {str} The product ID of the app connected to cloudapp security
        :param limit: {int} The limit of the results to fetch
        :return: {list} List of results
        """
        url = API_ENDPOINTS["get_user_related_activities"].format(self.api_root)

        filters = {"user.username": {"eq": username}}

        filters = self.apply_product_filter(filters, product_name)
        filters = self.apply_date_filter(filters, time_frame)

        payload = {"filters": filters}

        try:
            raw_activities = self._paginate_results(
                "POST",
                url,
                body=payload,
                limit=limit,
                err_msg="Unable to get activities",
            )

        except requests.exceptions.RequestException as e:
            raise Office365CloudAppSecurityConfigurationError(
                "Credentials are incorrect, please check the configuration of the integration."
            )

        return [
            self.cloud_app_parser.build_siemplify_activity_obj(activity)
            for activity in raw_activities
        ]

    @staticmethod
    def validate_response(
        response: Response, error_msg: str = "An error occurred"
    ) -> bool:
        """
        Validates Microsoft Office 365 CloudApp Security API response

        Args:
            response: CloudApp API response
            error_msg: Default response message

        Returns:
            True if response is valid
        """
        try:
            if response.status_code == 401:
                raise Office365CloudAppSecurityConfigurationError(
                    "Credentials are incorrect, please check the configuration of the integration."
                )
            if response.status_code == 400:
                errors = response.json().get("errors", [])
                error_message = ". ".join(error.get("error") for error in errors)
                raise Office365CloudAppSecurityManagerError(error_message)
            if response.status_code == RATE_LIMIT_STATUS_CODE:
                raise Office365CloudAppSecurityRateLimitingError(
                    f"{error_msg}: Max allowed of requests reached limit."
                )
            response.raise_for_status()

        except requests.HTTPError as error:
            raise Office365CloudAppSecurityManagerError(
                f"{error_msg}: {error} {error.response.content}"
            ) from error

        return True

    @staticmethod
    def apply_product_filter(filters, product_name):
        if not product_name or product_name == "":
            product_name = "All"

        if product_name != "All":
            filters["service"] = {"eq": product_name}

        return filters

    @staticmethod
    def apply_date_filter(filters, time_frame):
        filters["date"] = {"gte_ndays": int((time_frame / 24))}

        return filters

    def get_entity(self, entity_identifier):
        url = API_ENDPOINTS["entities"].format(self.api_root)

        filters = {"filters": {"displayName": {"eq": [entity_identifier]}}}

        raw_entities = self._paginate_results("GET", url, body=filters)
        if len(raw_entities) == 1:
            entity_obj = self.cloud_app_parser.build_siemplify_entity_obj(
                raw_entities[0]
            )
            return entity_obj
        raise Exception(f"Entity {entity_identifier} was not found")

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, API_ENDPOINTS[url_id].format(**kwargs))

    def get_ip_address_ranges(self):
        """
        Get ip address ranges
        :return: {[IpAddressRange]} list of IpAddressRange objects
        """
        url = self._get_full_url("get_ip_address_ranges")
        ip_address_ranges = self._paginate_results(
            "POST", url, err_msg="Unable to get IP address ranges"
        )

        return [
            self.cloud_app_parser.build_ip_address_range_object(ip_address_range)
            for ip_address_range in ip_address_ranges
        ]

    def update_ip_address_range(
        self, ip_address_range_name, ip_address_range, ip_addresses
    ):
        """
        Update IP address range
        :param ip_address_range_name: {str} ip address range name
        :param ip_address_range: {IpAddressRange} IpAddressRange object
        :param ip_addresses: {[str]} list of ip address
        :return: {void}
        """
        url = self._get_full_url(
            "update_ip_address_range", ip_address_range_id=ip_address_range.id
        )
        payload = {
            "name": ip_address_range_name,
            "category": ip_address_range.category,
            "organization": ip_address_range.organization,
            "subnets": ip_addresses,
            "tags": ip_address_range.tags,
        }

        response = self.session.post(url, json=payload)
        self.validate_response(response)

    def get_ip_address_range(self, ip_address_range_id):
        """
        Extracts IP Address Range and covers it in IpAddressRange object

        Args:
            ip_address_range_id: ID of IP Address Range

        Returns:
            IpAddressRange object of a given ID
        """
        url = self._get_full_url(
            "get_ip_address_range", ip_address_range_id=ip_address_range_id
        )
        response = self.session.get(url)
        self.validate_response(response)
        return self.cloud_app_parser.build_ip_address_range_object(response.json())

    def create_ip_address_range(
        self,
        name: str,
        category: int,
        organization: str,
        subnets: List[str],
        tags: List[str],
    ) -> str:
        """
        Creates IP Address Range with given parameters.

        Args:
            name: Name of IP Address Range
            category: Category of IP Address Range
            organization: Organization of IP Address Range
            subnets: List of subnets of IP Address Range
            tags: List of tags of IP Address Range

        Returns:
            ID of IP Address Range
        """
        url = API_ENDPOINTS["subnet_create_rule"].format(self.api_root)

        payload = {
            "name": name,
            "category": category,
            "organization": organization,
            "subnets": subnets,
            "tags": tags,
        }

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Cannot create entity")
        ip_address_range_id = response.text.replace('"', "")
        if ip_address_range_id:
            return ip_address_range_id
        raise Exception("Unexpected return after creating IP address range")


def has_ca_prefix_in_alerts(alert_ids: list[str]) -> bool:
    return any(aid.startswith(ALERT_PREFIX) for aid in alert_ids)


def remove_ca_prefix_from_alert_ids(
    kwargs: dict[str, str | list[str]],
) -> dict[str, str | list[str]]:
    """
    Formats the keyword argument by stripping ALERT_PREFIX prefix if
    it's a string or a list of strings.

    Args:
        kwargs (dict[str, str | list[str]]): A dict of keyword arguments.

    Returns:
        dict[str, str | list[str]]: A dict of keyword arguments with the alert id with
        ALERT_PREFIX prefix changed and the rest unchanged.
    """
    if kwargs.get(ALERT_ID_PARAM):
        kwargs[ALERT_ID_PARAM]: str = kwargs.get(ALERT_ID_PARAM).lstrip(ALERT_PREFIX)

    if kwargs.get(ALERT_ID_LIST_PARAM):
        kwargs[ALERT_ID_LIST_PARAM]: list[str] = [
            aid.lstrip(ALERT_PREFIX) for aid in kwargs.get(ALERT_ID_LIST_PARAM)
        ]

    return kwargs
