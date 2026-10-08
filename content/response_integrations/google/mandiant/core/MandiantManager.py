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
from typing import Optional, List, TypeVar
from urllib.parse import urljoin

import requests

from mandiant.core.MandiantParser import MandiantParser
from mandiant.core.constants import PAGE_SIZE
from mandiant.core.datamodels import Indicator, Vulnerability, ThreatActor, Malware

HEADERS = {"Accept": "application/json"}

ENDPOINTS = {
    "auth": "/token",
    "ping": "/v4/indicator",
    "indicator_details": "/v4/indicator",
    "threat_actor_details": "/v4/actor/{actor_identifier}",
    "vulnerability_details": "/v4/vulnerability/{vulnerability_identifier}",
    "threat_actor_indicators": "/v4/actor/{threat_actor_identifier}/indicators",
    "malware_indicators": "/v4/malware/{malware_identifier}/indicators",
    "malware_details": "/v4/malware/{malware_identifier}",
}

DataModelType = TypeVar("DataModelType", Indicator, Vulnerability, ThreatActor, Malware)


class MandiantManager:
    def __init__(
        self,
        api_root,
        client_id,
        client_secret,
        verify_ssl,
        ui_root="",
        siemplify_logger=None,
        force_check_connectivity=False,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Mandiant API root
        :param client_id: {str} Mandiant API key
        :param client_secret: {str} Mandiant API key
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param ui_root: {str} Mandiant UI root
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        self.ui_root = ui_root
        self.siemplify_logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(HEADERS)
        self.session.auth = (client_id, client_secret)
        self.parser = MandiantParser()
        self._set_auth_token()

        if force_check_connectivity:
            self.test_connectivity()

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update(
            {"Authorization": f"Bearer {self._generate_token()}"}
        )

    def _generate_token(self):
        """
        Generate auth token
        :return: {str} The auth token
        """
        url = self._get_full_url("auth")
        payload = {"grant_type": "client_credentials"}

        response = self.session.post(url, data=payload)
        self.validate_response(response)
        return self.parser.get_token(response.json())

    def test_connectivity(self):
        """
        Test connectivity
        """
        params = {"value": "173.254.208.91", "type": "ipv4"}
        response = self.session.get(self._get_full_url("ping"), params=params)
        self.validate_response(response)

    def get_indicator_details(self, entity_identifier) -> List[DataModelType]:
        """
        Get Indicator details
        :param entity_identifier: {str} The identifier
        :return: {datamodel} Object of datamodel.Indicator
        """
        return self._paginate_results_with_next(
            "indicator_details", entity_identifier, "build_indicators_list"
        )

    def get_vulnerability_details(self, entity_identifier) -> Vulnerability:
        """
        Get Indicator details
        :param entity_identifier: {str} The identifier
        :return: {datamodel} Object of datamodel.Vulnerability
        """
        response = self.session.get(
            self._get_full_url(
                "vulnerability_details", vulnerability_identifier=entity_identifier
            )
        )
        self.validate_response(response)

        return self.parser.build_vulnerability_obj(response.json())

    def get_actor_details(self, entity_identifier) -> ThreatActor:
        """
        Get Actor details
        :param entity_identifier: {str} The identifier
        :return: {datamodel} Object of datamodel.Vulnerability
        """
        response = self.session.get(
            self._get_full_url(
                "threat_actor_details", actor_identifier=entity_identifier
            )
        )
        self.validate_response(response)

        return self.parser.build_actor_obj(response.json())

    def get_malware_details(self, identifier: str) -> Malware:
        """
        Get Malware details
        :param identifier: {str} The identifier
        :return: {datamodel} Object of datamodel.Malware
        """
        response = self.session.get(
            self._get_full_url("malware_details", malware_identifier=identifier)
        )
        self.validate_response(response)

        return self.parser.build_malware_obj(response.json())

    def get_threat_actor_indicators(self, identifier, limit, lowest_severity=None):
        """
        Get Threat Actor indicators
        :param identifier: {str} The identifier
        :param limit: {int} The limit of the results to fetch
        :param lowest_severity: {int} Lowest severity to filter results with
        :return: {list} List of datamodel.Indicator
        """
        url = self._get_full_url(
            "threat_actor_indicators", threat_actor_identifier=identifier
        )

        return self._paginate_results(
            method="GET",
            url=url,
            parser_method="build_indicators_list",
            limit=limit,
            lowest_severity=lowest_severity,
        )

    def get_malware_indicators(self, identifier, limit, lowest_severity=None):
        """
        Get Malware indicators
        :param identifier: {str} The identifier
        :param limit: {int} The limit of the results to fetch
        :param lowest_severity: {int} Lowest severity to filter results with
        :return: {list} List of datamodel.Indicator
        """
        url = self._get_full_url("malware_indicators", malware_identifier=identifier)

        return self._paginate_results(
            method="GET",
            url=url,
            parser_method="build_indicators_list",
            limit=limit,
            lowest_severity=lowest_severity,
        )

    def get_vulnerability_indicators(self, identifier, limit, lowest_severity=None):
        """
        Get Malware indicators
        :param identifier: {str} The identifier
        :param limit: {int} The limit of the results to fetch
        :param lowest_severity: {int} Lowest severity to filter results with
        :return: {list} List of datamodel.Indicator
        """
        url = self._get_full_url("malware_indicators", malware_identifier=identifier)

        return self._paginate_results(
            method="GET",
            url=url,
            parser_method="build_indicators_list",
            limit=limit,
            lowest_severity=lowest_severity,
        )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise Exception(f"{error_msg}: {error} {error.response.content}")

        return True

    def _paginate_results(
        self,
        method,
        url,
        parser_method,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        page_size=PAGE_SIZE,
        lowest_severity=None,
        severity_key="mscore",
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
        :param lowest_severity: {int} Lowest severity to filter results with
        :param severity_key: {str} The key of severity property
        :return: {list} List of results
        """

        params = params or {}
        offset = 0
        params["limit"] = min(page_size, limit) if limit else page_size
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
            current_items = getattr(self.parser, parser_method)(response.json())
            filtered_items = (
                [
                    item
                    for item in current_items
                    if getattr(item, severity_key) >= lowest_severity
                ]
                if lowest_severity
                else current_items
            )

            results.extend(filtered_items)

            if len(current_items) < page_size:
                break

        return results[:limit] if limit else results

    def _paginate_results_with_next(
        self,
        url: str,
        entity_identifier: str,
        parser_method: str,
        limit: int = PAGE_SIZE,
        err_msg: str = "Unable to get results",
        lowest_severity: Optional[int] = None,
        severity_key: str = "mscore",
    ) -> List[DataModelType]:
        results = []
        params = {"value": entity_identifier, "limit": limit}
        while True:
            response = self.session.get(self._get_full_url(url), params=params)
            response_json = response.json()

            self.validate_response(response, err_msg)

            current_items = getattr(self.parser, parser_method)(response_json)
            filtered_items = (
                [
                    item
                    for item in current_items
                    if getattr(item, severity_key) >= lowest_severity
                ]
                if lowest_severity
                else current_items
            )

            results.extend(filtered_items)
            if response_json.get("next"):
                params = {"next": response_json.get("next")}
            else:
                break
        return results
