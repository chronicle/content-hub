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
import json
from urllib.parse import urljoin
import requests

from TIPCommon import filter_old_alerts

from .UtilsManager import validate_response
from .StellarCyberStarlightParser import StellarCyberStarlightParser
from .StellarCyberStarlightConstants import (
    ENDPOINTS,
    HEADERS,
    ASCENDING_SORT,
    BAD_REQUEST_STATUS_CODE,
    ALERTS_FETCH_SIZE,
    ALERTS_LIMIT,
    STATUS_SELECT_ONE,
    ALERT_ID_FIELD,
    NOT_KEY_OR_TOKEN_ALERT,
    TIMESTAMP_FIELD_DEFAULT_VALUE,
)
from .StellarCyberStarlightExceptions import (
    SearchExecutionException,
    StellarCyberStarlightException,
)


class StellarCyberStarlightManager:

    def __init__(
        self, api_root, username, api_key, api_token, verify_ssl=False, siemplify=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the Stellar Cyber Starlight instance.
        :param username: Username of the Stellar Cyber Starlight account.
        :param api_key: API Key of the Stellar Cyber Starlight account.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the Stellar Cyber Starlight server is valid.
        :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.username = username
        self.api_key = api_key
        self.api_token = api_token
        self.siemplify = siemplify
        self.parser = StellarCyberStarlightParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        if self.is_string_utf8(self.username):
            self.username = str(self.username.encode("utf-8"))
        if api_token:
            self.jwt_token = self._generate_access_token(self.username, self.api_token)
            self.session.headers.update({"Authorization": f"Bearer {self.jwt_token}"})
            self.session.auth = ""
        elif api_key:
            self.session.auth = (self.username, self.api_key)
        else:
            raise StellarCyberStarlightException(NOT_KEY_OR_TOKEN_ALERT)

    @staticmethod
    def is_string_utf8(item):
        return any(ord(char) > 127 for char in item)

    def _generate_access_token(self, username, api_key):
        self.session.auth = (username, api_key)
        request_url = self._get_full_url("access_token")
        response = self.session.post(request_url)
        validate_response(response, "Invalid API Token provided. Please validate it.")
        result = self.parser.get_access_token(response.json())
        return result

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to the Stellar Cyber Starlight.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        payload = {"size": 1, "query": {"match_all": {}}}

        response = self.session.get(request_url, json=payload)
        validate_response(response, "Unable to connect to Stellar Cyber Starlight.")

    def make_simple_search(self, index, size, query, sort_field, sort_order):
        """
        Make simple search request
        :param index: Index in which to make the search
        :param size: Max results to return
        :param query: Query filter for search
        :param sort_field: Field to use for sorting
        :param sort_order: Sorting order for the result
        :return: List of Hit objects
        """
        request_url = self._get_full_url("simple_search", index=index)
        sort_order = "asc" if sort_order == ASCENDING_SORT else "desc"
        payload = {
            "size": size,
            "query": {
                "constant_score": {
                    "filter": {"bool": {"must": [{"query_string": {"query": query}}]}}
                }
            },
        }
        if sort_field:
            payload["sort"] = [{sort_field: {"order": sort_order}}]

        response = self.session.get(request_url, json=payload)
        try:
            validate_response(response)
        except Exception as e:
            if response.status_code == BAD_REQUEST_STATUS_CODE:
                raise SearchExecutionException(
                    self.parser.build_errors(response.json())
                )
            raise Exception(e)
        return self.parser.build_all_hits(response.json())

    def make_advanced_search(self, index, dsl_query):
        """
        Make advanced search request
        :param index: Index in which to make the search
        :param dsl_query: DSL query filter for search
        :return: List of Hit objects
        """
        request_url = self._get_full_url("simple_search", index=index)
        response = self.session.get(request_url, json=json.loads(dsl_query))
        try:
            validate_response(response)
        except Exception as e:
            if response.status_code == BAD_REQUEST_STATUS_CODE:
                raise SearchExecutionException(
                    self.parser.build_errors(response.json())
                )
            raise Exception(e)
        return self.parser.build_all_hits(response.json())

    def get_alerts(
        self,
        existing_ids,
        start_time,
        lowest_severity,
        fetch_limit,
        timestamp_field=TIMESTAMP_FIELD_DEFAULT_VALUE,
    ):
        """
        Get alerts.
        :param existing_ids: {list} The list of existing ids.
        :param start_time: {str} The datetime from where to fetch indicators.
        :param lowest_severity: {int} Lowest severity that will be used to fetch indicators.
        :param fetch_limit: {int} Max alerts to fetch
        :param timestamp_field: {str} Field that will be used as timestamp
        :return: {list} The list of Alerts.
        """
        request_url = self._get_full_url("get_alerts")
        payload = {
            "size": fetch_limit,
            "from": 0,
            "query": {
                "constant_score": {
                    "filter": {
                        "bool": {
                            "must": [
                                {"range": {timestamp_field: {"gte": start_time}}},
                                {"range": {"event_score": {"gte": lowest_severity}}},
                                {
                                    "query_string": {
                                        "query": '(NOT _exists_:event_status) OR event_status:"New"'
                                    }
                                },
                            ]
                        }
                    }
                }
            },
            "sort": [{timestamp_field: {"order": "asc"}}],
        }
        alerts = [
            self.parser.build_alert_object(alert_json, timestamp_field)
            for alert_json in self._paginate_results(
                method="GET", url=request_url, body=payload, fetch_limit=fetch_limit
            )
        ]
        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )
        return sorted(filtered_alerts, key=lambda alert: alert.timestamp)[:fetch_limit]

    def _paginate_results(
        self,
        method,
        url,
        result_key="hits",
        fetch_limit=ALERTS_LIMIT,
        params=None,
        body=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results
        :param method: {unicode} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {unicode} The url to send request to
        :param result_key: {unicode} The key to extract data
        :param fetch_limit: {int} Max alerts to fetch
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {unicode} The message to display on error
        :return: {list} List of results
        """
        if body is None:
            body = {}
        body["from"] = 0
        body["size"] = ALERTS_FETCH_SIZE

        response = self.session.request(method, url, params=params, json=body)
        validate_response(response, err_msg)
        json_result = response.json()
        results = json_result.get(result_key, {}).get(result_key, [])

        while len(results) < json_result.get(result_key, {}).get("total", 0).get(
            "value", 0
        ):
            if len(results) >= fetch_limit:
                break
            body.update({"from": len(results)})
            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            results.extend(response.json().get(result_key, {}).get(result_key, []))

        return results

    def update_security_event(self, event_id, index, event_comment, event_status):
        """
        Function that updates the security event in Stellar Cyber
        :param event_id: {str} Event ID
        :param index: {str} Event Index
        :param event_comment: {str} Comment that will be added to the event
        :param event_status: {str} Event Status
        """
        request_url = self._get_full_url("update_event")
        payload = {"index": index, "_id": event_id}

        if event_status != STATUS_SELECT_ONE:
            payload["status"] = event_status

        if event_comment:
            payload["comments"] = event_comment

        response = self.session.post(request_url, json=payload)
        try:
            validate_response(response)
        except Exception as e:
            if response.status_code != 401:
                raise Exception(response.text)
            raise Exception(e)
