from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin
import requests

from forti_analyzer.core.constants import (
    DEFAULT_MAX_LIMIT,
    DONE_STATUS,
    ENDPOINTS,
    LOGS_LIMIT,
    SEVERITY_MAPPING,
)
from forti_analyzer.core import datamodels
from forti_analyzer.core.FortiAnalyzerParser import FortiAnalyzerParser
from forti_analyzer.core.UtilsManager import validate_response, prepare_time_ranges

if TYPE_CHECKING:
    from soar_sdk.SiemplifyLogger import SiemplifyLogger

    from typing import Any, List, Tuple


class FortiAnalyzerManager:
    def __init__(
        self,
        api_root: str,
        username: str,
        password: str,
        verify_ssl: bool,
        siemplify_logger: SiemplifyLogger | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        The method is used to init an object of Manager class.
        Args:
            api_root (str): API root of the FortiAnalyzer instance.
            username (str): Username of the FortiAnalyzer account.
            password (str): Password of the FortiAnalyzer account.
            verify_ssl (bool): Specifies if certificate that is configured on the api
            root should be validated.
            siemplify_logger(SiemplifyLogger): Siemplify logger.
            session_id (str): The session id to use for connection.
        """
        self.api_root: str = api_root[:-1] if api_root.endswith("/") else api_root
        self.username: str = username
        self.password: str = password
        self.verify_ssl: bool = verify_ssl
        self.siemplify_logger: SiemplifyLogger = siemplify_logger
        self.parser: FortiAnalyzerParser = FortiAnalyzerParser()
        self.session: requests.Session = requests.Session()
        self.session.verify: bool = verify_ssl
        self.api_session: str = session_id if session_id is not None else self.login()

    def _get_full_url(self, url_id, **kwargs) -> str:
        """
        Get full url from url identifier.
        Args:
            url_id (str): The id of url
            **kwargs: Variables passed for string formatting

        Returns:
            (str) The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def login(self) -> str:
        """
        Login to FortiAnalyzer
        Returns:
            (str): session id
        """
        url = self._get_full_url("rpc")
        payload = {
            "method": "exec",
            "params": [
                {
                    "data": {"passwd": self.password, "user": self.username},
                    "url": "/sys/login/user",
                }
            ],
            "id": 1,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)

        return response.json().get("session")

    def logout(self) -> None:
        """
        Logout from FortiAnalyzer
        Returns:
            (): None
        """
        url = self._get_full_url("rpc")
        payload = {
            "method": "exec",
            "params": [{"url": "/sys/logout"}],
            "session": self.api_session,
            "id": 1,
        }

        response = self.session.post(url, json=payload)
        validate_response(response)

    def test_connectivity(self) -> None:
        """
        Test connectivity
        Returns:
            (void)
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "get",
            "params": [
                {"apiver": 3, "limit": 1, "offset": 0, "url": "/eventmgmt/alerts"}
            ],
            "session": self.api_session,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)

    def get_device(self, ip=None, hostname=None) -> datamodels.Device:
        """
        Get device by entity
        Args:
            ip (str): IP address
            hostname (str): Hostname

        Returns:
            (datamodels.Device)
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "1",
            "method": "get",
            "params": [
                {
                    "filter": ["ip", "==", ip] if ip else ["name", "==", hostname],
                    "url": "/dvmdb/device",
                }
            ],
            "session": self.api_session,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)
        result = response.json().get("result", [])
        if result:
            data = result[0].get("data", [])
            if data:
                return self.parser.build_device_obj(raw_json=data[0])

    def find_alert(self, alert_id: str) -> datamodels.Alert:
        """
        Find alert by id
        Args:
            alert_id: The id of the alert

        Returns:
            (datamodels.Alert)
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "get",
            "params": [
                {
                    "apiver": 3,
                    "filter": f"alertid={alert_id}",
                    "url": "/eventmgmt/alerts",
                }
            ],
            "session": self.api_session,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)
        result = response.json().get("result", {})
        if result:
            data = result.get("data", [])
            if data:
                return self.parser.build_alert_object(raw_data=data[0])

    def mark_as_read(self, alert_id: str, adom: str) -> bool:
        """
        Mark alert as read
        Args:
            alert_id: The id of the alert
            adom: The adom of the alert
        Returns:
            (bool): status of action
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "update",
            "params": [
                {
                    "apiver": 3,
                    "alertids": [alert_id],
                    "url": f"/eventmgmt/adom/{adom}/alerts/read",
                }
            ],
            "session": self.api_session,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)
        if response.json().get("result", {}).get("status") == DONE_STATUS:
            return True

    def assign_user(self, alert_id: str, adom: str, username: str) -> bool:
        """
        Assign user to the alert
        Args:
            alert_id: The id of the alert
            adom: The adom of the alert
            username: The username to assign to
        Returns:
            (bool): status of action
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "update",
            "params": [
                {
                    "apiver": 3,
                    "alertids": [alert_id],
                    "assign-to": username,
                    "url": f"/eventmgmt/adom/{adom}/alerts/assign",
                }
            ],
            "session": self.api_session,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)
        if response.json().get("result", {}).get("status") == DONE_STATUS:
            return True

    def acknowledge_alert(
        self, alert_id: str, adom: str, username: str, acknowledge: bool
    ) -> bool:
        """
        Acknowledge/Unacknowledge the alert
        Args:
            alert_id: The id of the alert
            adom: The adom of the alert
            username: The username to assign to
            acknowledge: Whether to acknowledge or unacknowledge the alert
        Returns:
            (bool): status of action
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "update",
            "params": [
                {
                    "apiver": 3,
                    "alertids": [alert_id],
                    "update-by": username,
                    "url": f"/eventmgmt/adom/{adom}/alerts/{'ack' if acknowledge else 'unack'}",
                }
            ],
            "session": self.api_session,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)
        if response.json().get("result", {}).get("status") == DONE_STATUS:
            return True

    def add_comment_to_alert(
        self, alert_id: str, adom: str, comment: str
    ) -> datamodels.AlertCommentResponse:
        """
        Add comment to alert
        Args:
            alert_id: id of alert
            adom: adom of alert
            comment: comment to add to alert
        Returns:
            (AlertCommentResponse): AlertCommentResponse object
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "update",
            "params": [
                {
                    "apiver": 3,
                    "alertid": [alert_id],
                    "comment": comment,
                    "update-by": "admin",
                    "url": f"/eventmgmt/adom/{adom}/alerts/comment",
                }
            ],
            "session": self.api_session,
        }

        response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.build_alert_comment_response_object(response.json())

    def get_alerts(
        self, start_timestamp: int, severity_filter: str, limit: int
    ) -> List[datamodels.Alert]:
        """
        Get Alerts
        Args:
            start_timestamp (int): Start time to fetch alerts from
            severity_filter (str): Severity value to use for filtering
            limit (int): Limit for results

        Returns:
            (list): List of Alert objects
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "get",
            "session": self.api_session,
        }
        time_intervals = prepare_time_ranges(start_timestamp)
        results = []

        for start, end in time_intervals:
            if len(results) > max(limit, DEFAULT_MAX_LIMIT):
                break

            params = {
                "apiver": 3,
                "time-range": {"start": start, "end": end},
                "url": "/eventmgmt/alerts",
            }

            if severity_filter:
                params["filter"] = f"severity<={SEVERITY_MAPPING.get(severity_filter)}"

            current_results = self._paginate_results(
                method="POST",
                url=url,
                parser_method="build_alert_object",
                params=params,
                body=payload,
            )

            results.extend(current_results)

        return sorted(results, key=lambda item: item.alert_time)[
            : max(limit, DEFAULT_MAX_LIMIT)
        ]

    def get_alert_details(self, alert_id: str, adom: str) -> List[dict]:
        """
        Get Alert Details
        Args:
            alert_id (str): alert id to fetch alert details
            adom (str): adom of alert

        Returns:
            ([dict]): list of raw data dicts
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "get",
            "params": [
                {
                    "apiver": 3,
                    "alertids": [alert_id],
                    "url": f"/eventmgmt/adom/{adom}/alerts/extra-details",
                }
            ],
            "session": self.api_session,
        }

        response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.get_data(raw_data=response.json())

    def get_alert_logs(self, alert_id: str, adom: str) -> List[dict]:
        """
        Get Alert Logs
        Args:
            alert_id (str): alert id to fetch alert logs
            adom (str): adom of alert

        Returns:
            ([dict]): list of raw data dicts
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "get",
            "params": [
                {
                    "apiver": 3,
                    "alertid": [alert_id],
                    "limit": LOGS_LIMIT,
                    "offset": 0,
                    "time-order": "asc",
                    "url": f"/eventmgmt/adom/{adom}/alertlogs",
                }
            ],
            "session": self.api_session,
        }

        response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.get_data(response.json())

    def _paginate_results(
        self,
        method: str,
        url: str,
        parser_method: str,
        params: dict = None,
        body: dict = None,
        limit: int = None,
        err_msg: str = "Unable to get results",
        page_size: int = 100,
    ) -> [Any]:
        """
        Paginate the results
        Args:
            method (str): The method of the request (GET, POST, PUT, DELETE, PATCH)
            url (str): The url to send request to
            parser_method (str): The name of parser method to build the result
            params (dict): The params of the request
            body (dict): The json payload of the request
            limit (int): The limit of the results to fetch
            err_msg (str): The message to display on error
            page_size (int): Items per page

        Returns:
            ([Any]): List of results
        """
        params = params or {}
        page_number = 0
        params["limit"] = page_size
        params.update({"offset": page_number * page_size})

        response = None
        results = []

        while True:
            if response:
                if limit and len(results) >= limit:
                    break

                page_number += 1
                params.update({"offset": page_number * page_size})

            body["params"] = [params]
            response = self.session.request(method, url, json=body)

            validate_response(response, err_msg)
            current_items = [
                getattr(self.parser, parser_method)(item)
                for item in response.json().get("result", {}).get("data", [])
            ]

            results.extend(current_items)

            if len(current_items) < page_size:
                break

        return results[:limit] if limit else results

    def create_search_task(
        self,
        log_type: str,
        is_case_sensitive: bool,
        query: str,
        device_id: str,
        start_time: str,
        end_time: str,
        time_order: str,
    ) -> str:
        """
        Method for searching logs on FortiAnalyzer server
        Args:
            log_type: type of logs to search
            is_case_sensitive: make query case-sensitive
            query: search query
            device_id: device id
            start_time: search results starting from
            end_time: search results by
            time_order: search result order(asc, desc)
        Returns:
            Task id
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "add",
            "params": [
                {
                    "apiver": 3,
                    "case-sensitive": is_case_sensitive,
                    "device": [{"devid": device_id}],
                    "logtype": log_type,
                    "time-order": time_order,
                    "time-range": {
                        "end": str(end_time) if end_time else None,
                        "start": str(start_time),
                    },
                    "url": "/logview/adom/root/logsearch",
                }
            ],
            "session": self.api_session,
        }
        if query:
            payload["params"][0].update({"filter": query})
        response = self.session.post(url, json=payload)
        validate_response(response)
        return response.json().get("result", {}).get("tid")

    def search_logs(self, task_id, logs_to_return) -> Tuple:
        """
        Manager method searches for logs with provided task id
        Args:
            task_id: search task id
            logs_to_return: count of logs to return
        Returns:
            Tuple: int, Log objects
        """
        url = self._get_full_url("rpc")
        payload = {
            "id": "string",
            "jsonrpc": "2.0",
            "method": "get",
            "params": [
                {
                    "apiver": 3,
                    "limit": logs_to_return,
                    "offset": 0,
                    "url": f"/logview/adom/root/logsearch/{task_id}",
                }
            ],
            "session": self.api_session,
        }
        response = self.session.post(url, json=payload)
        validate_response(response)
        response_json = response.json()
        results = []

        progress = int(response_json.get("result", {}).get("percentage", {}))
        if progress == 100:  # build and return results when search task completed
            results = self.parser.build_search_log_objects(response_json)
        return progress, results
