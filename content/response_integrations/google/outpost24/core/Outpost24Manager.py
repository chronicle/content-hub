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
import requests
import json
from .constants import (
    PING_URL,
    GET_TOKEN_URL,
    GET_DEVICES_URL,
    DEFAULT_API_LIMIT,
    FINDING_TYPES,
    GET_FINDINGS_URL,
    DEFAULT_LIMIT,
)
from urllib.parse import urlencode
from .Outpost24Parser import Outpost24Parser
from .Outpost24Exceptions import DeviceNotFoundError
from .UtilsManager import (
    validate_response,
    filter_old_alerts,
    filter_alerts_by_timestamp,
)
from soar_sdk.SiemplifyUtils import convert_string_to_datetime


class Outpost24Manager:
    def __init__(self, api_root, username, password, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Outpost24 API root
        :param username: {str} Outpost24 username
        :param password: {str} Outpost24 password
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.set_auth_token()
        self.parser = Outpost24Parser()

    def set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update(
            {"Authorization": f"Bearer {self.get_auth_token()}"}
        )

    def get_auth_token(self):
        """
        Send request in order to generate token.
        :return: {str} The authorization token
        """
        url = GET_TOKEN_URL.format(self.api_root)

        payload = {"username": self.username, "password": self.password}

        response = self.session.post(url, data=payload)
        validate_response(response)
        return response.text

    def test_connectivity(self):
        """
        Test connectivity
        """
        url = PING_URL.format(self.api_root)
        response = self.session.get(url)
        validate_response(response)

    def get_device_information(
        self,
        entity_identifier,
        risk_level_filter,
        return_finding_information,
        finding_type,
        max_findings_to_return,
        is_hostname=False,
    ):
        """
        Function that gets the device(s) information from Outpost24, and request additional findings if needed
        :param entity_identifier: {str} Entity identifier
        :param risk_level_filter: {list} Risk levels to use in filters
        :param return_finding_information: {bool} True if additional findings should be returned, False otherwise
        :param finding_type: {str} Finding Type - All, Vulnerability, Information
        :param max_findings_to_return: {str} Limit of how many findings to return
        :param is_hostname: {bool} True if the processed entity is hostname type, False if it's IP address type
        :return {EntityObject} Entity object containing all the data
        """
        params = {}

        if is_hostname:
            # For hostnames we can apply filters in the API request
            params = {"filter": [{"field": "hostname", "value": entity_identifier}]}
            params = urlencode(params)

            url = GET_DEVICES_URL.format(self.api_root)
            response = self.session.get(url, params=params)
            validate_response(response)
            json_result = response.json()

            if len(json_result) > 0:
                entity_basic_details = self.parser.build_entity_object(
                    raw_data=json_result[0]
                )
            else:
                raise DeviceNotFoundError(
                    f"Entity: {entity_identifier} not found in Outpost24."
                )
        else:
            # For IP Addresses we need to fetch everything and then filter the correct
            # IP address on our side
            params = {"limit": DEFAULT_API_LIMIT, "offset": 0}
            url = GET_DEVICES_URL.format(self.api_root)
            response = self.session.get(url, params=params)
            validate_response(response)
            json_result = response.json()
            num_of_results = len(json_result)
            total_number_of_results = num_of_results

            if num_of_results < 1:
                raise DeviceNotFoundError(f"No devices found in Outpost24.")

            while (
                num_of_results == DEFAULT_API_LIMIT
            ):  # the API response doesn't have any indicator that it has next page,
                # only if you fetch the same number of entities as the limit,
                # it indicates that it has more data on next pages
                params.update({"offset": total_number_of_results})
                response = self.session.get(url, params=params)
                validate_response(response)
                json_result.extend(response.json())
                num_of_results = len(response.json())
                total_number_of_results = total_number_of_results + num_of_results

            ip_address_details = self.parser.find_ip_address(
                raw_data=json_result, entity_identifier=entity_identifier
            )
            if ip_address_details is None:
                raise DeviceNotFoundError(
                    f"Entity: {entity_identifier} not found in Outpost24."
                )

            entity_basic_details = self.parser.build_entity_object(
                raw_data=ip_address_details
            )

        if return_finding_information:
            finding_information_filter = []

            finding_information_filter.append(
                {"field": "targetId", "value": entity_basic_details.id}
            )
            finding_information_filter.append(
                {"field": "type", "value": FINDING_TYPES.get(finding_type)}
            )

            params = {
                "sort": "-lastSeen",
                "limit": DEFAULT_API_LIMIT,
                "offset": 0,
                "filter": finding_information_filter,
            }
            params = urlencode(params)

            url = GET_FINDINGS_URL.format(self.api_root)
            response = self.session.get(url, params=params)
            validate_response(response)
            json_result = response.json()

            filtered_results = self.parser.filter_found_information(
                data=json_result, risk_level_filter=risk_level_filter
            )

            num_of_results = len(json_result)
            total_number_of_results = num_of_results
            number_of_filtered_results = len(filtered_results)

            if number_of_filtered_results > max_findings_to_return:
                filtered_results = filtered_results[:max_findings_to_return]
                number_of_filtered_results = len(filtered_results)

            while (
                num_of_results == DEFAULT_API_LIMIT
                and number_of_filtered_results < max_findings_to_return
            ):
                params.update(
                    {
                        "sort": "-lastSeen",
                        "limit": DEFAULT_API_LIMIT,
                        "offset": total_number_of_results,
                        "filter": finding_information_filter,
                    }
                )
                params = urlencode(params)
                response = self.session.get(url, params=params)
                validate_response(response)
                json_result.extend(response.json())
                filtered_results_page = self.parser.filter_found_information(
                    data=json_result, risk_level_filter=risk_level_filter
                )

                if (
                    number_of_filtered_results + len(filtered_results_page)
                    > max_findings_to_return
                ):
                    number_od_results_to_get = (
                        max_findings_to_return - number_of_filtered_results
                    )
                    filtered_results_page = filtered_results_page[
                        :number_od_results_to_get
                    ]

                filtered_results = filtered_results + filtered_results_page
                number_of_filtered_results = len(filtered_results)

                num_of_results = len(response.json())
                total_number_of_results = total_number_of_results + num_of_results

            self.parser.add_findings_to_entity_object(
                entity_object=entity_basic_details, data=filtered_results
            )

        return entity_basic_details

    def get_findings(self, existing_ids, limit, start_timestamp, type_filter):
        """
        Get findings
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_timestamp: {datetime} The timestamp for oldest finding to fetch
        :param type_filter: {str} Type filter to apply
        :return: {list} The list of filtered Finding objects
        """
        request_url = GET_FINDINGS_URL.format(self.api_root)
        params = {
            "sort": "-lastSeen",
            "limit": DEFAULT_LIMIT,
            "filter": json.dumps(
                [{"field": "type", "value": type_filter, "comparison": "eq"}]
            ),
            "offset": 0,
        }
        response = self.session.get(request_url, params=params)
        validate_response(response)
        json_result = response.json()
        findings = self.parser.build_findings_list(json_result)

        while len(
            json_result
        ) >= DEFAULT_LIMIT and start_timestamp <= convert_string_to_datetime(
            findings[-1].last_seen
        ):
            params.update({"offset": len(findings)})
            response = self.session.get(request_url, params=params)
            validate_response(response)
            json_result = response.json()
            findings.extend(self.parser.build_findings_list(json_result))

        filtered_by_timestamp = filter_alerts_by_timestamp(
            logger=self.siemplify_logger,
            alerts=findings,
            last_success_time=start_timestamp,
        )
        filtered_findings = filter_old_alerts(
            logger=self.siemplify_logger,
            alerts=filtered_by_timestamp,
            existing_ids=existing_ids,
        )
        return sorted(filtered_findings, key=lambda finding: finding.last_seen)[:limit]
