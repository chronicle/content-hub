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

from typing import List, Optional, TypeVar

from urllib.parse import urljoin
import requests

from .constants import ENDPOINTS, GTI_ENDPOINTS, PAGE_SIZE, REQUEST_TIMEOUT
from .datamodels import Indicator, Malware, ThreatActor, Vulnerability
from .exceptions import (
    InvalidParametersException,
    InvalidUnicodeKeyError,
    MandiantException,
)
from .MandiantParser import MandiantParser

HEADERS = {"Accept": "application/json"}


DataModelType = TypeVar("DataModelType", Indicator, Vulnerability, ThreatActor, Malware)


class MandiantManager:

    def __init__(
        self,
        api_root: str,
        verify_ssl: bool,
        ui_root: str = "",
        client_id: str | None = None,
        client_secret: str | None = None,
        gti_api_key: str | None = None,
        siemplify_logger: str | None = None,
        force_check_connectivity: bool = False,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Mandiant API root
        :param client_id: {str} Mandiant API key
        :param client_secret: {str} Mandiant API key
        :param gti_api_key (str): Google Threat Intelligence API Key
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param ui_root: {str} Mandiant UI root
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.gti_api_key = gti_api_key
        self.verify_ssl = verify_ssl
        self.ui_root = ui_root
        self.siemplify_logger = siemplify_logger
        self._validate_keys()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(HEADERS)
        self.session.auth = (client_id, client_secret)
        self.parser = MandiantParser()
        self._set_auth_token()

        if force_check_connectivity:
            self.test_connectivity()

    def _validate_keys(self) -> None:
        """Validate that the provided keys do not contain Unicode characters
        and ensure that at least one of the required keys is provided.
        """
        if not self.client_id and not self.client_secret and not self.gti_api_key:
            raise InvalidParametersException(
                "Either 'Client ID' + 'Client Secret' or 'GTI API Key' "
                "should be provided. Make sure that the correct API root "
                "is provided as well."
            )

        for key in [self.client_id, self.client_secret, self.gti_api_key]:
            if isinstance(key, str) and any(ord(char) > 127 for char in key):
                raise InvalidUnicodeKeyError(
                    "Please verify the 'Client ID,' 'Client Secret,' or 'GTI API Key'"
                    " credentials."
                )

    def _get_full_url(self, endpoint_id: str, **kwargs) -> str:
        """Construct the full URL using a URL identifier and optional variables

        Args:
            endpoint_id (str): The identifier for the desired API endpoint.
            kwargs (dict): variables passed for string formatting

        Returns:
            str: constructed full URL
        """
        endpoint = ENDPOINTS[endpoint_id]
        if self.gti_api_key:
            endpoint = GTI_ENDPOINTS[endpoint_id]

        return urljoin(self.api_root, endpoint.format(**kwargs))

    def _set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        if self.gti_api_key:
            self.session.auth = None
            self.session.headers.update({"x-apikey": self.gti_api_key})
        else:
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

    def test_connectivity(self) -> None:
        """Test connectivity"""
        params = {"value": "192.0.2.1", "type": "ipv4"}
        url = self._get_full_url("ping")
        response = self.session.get(url=url, params=params)
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
            ),
            params={"rating_types": "predicted,analyst,unrated"},
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
            raise MandiantException(
                f"{error_msg}: {error} {error.response.content}"
            ) from error

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
        has_next: bool = True
        while has_next:
            try:
                response = self.session.get(
                    self._get_full_url(url), params=params, timeout=REQUEST_TIMEOUT
                )
            except requests.exceptions.Timeout:
                if self.siemplify_logger:
                    self.siemplify_logger.warning(
                        f"Mandiant API request for '{entity_identifier}' "
                        "timed out after 20s. Dropping request and continuing."
                    )
                return []

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

            next_token = response_json.get("next")
            if next_token:
                params = {"next": next_token}
            else:
                has_next = False
        return results
