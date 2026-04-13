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
from urllib.parse import urljoin
import requests
import json
from ..core.UrlScanParser import UrlScanParser
from ..core.exceptions import UrlScanError, UrlDnsScanError


API_ROOT = "https://urlscan.io/"
HEADERS = {"Content-Type": "application/json"}
API_ENDPOINTS = {
    "ping": "user/quotas",
    "scan": "api/v1/scan",
    "search": "api/v1/search",
    "result": "api/v1/result/{scan_id}",
}

NOT_FOUND_STATUS_CODE = 404
BAD_REQUEST = 400


class UrlScanManager:
    """
    Responsible for all UrlScan.io system operations functionality
    """

    def __init__(
        self, api_key, verify_ssl=False, logger=None, force_check_connectivity=False
    ):
        self.api_key = api_key
        self.session = requests.Session()
        HEADERS.update({"API-Key": api_key})
        self.session.headers.update(HEADERS)
        self.session.verify = verify_ssl
        self.logger = logger
        self.parser = UrlScanParser()

        if force_check_connectivity:
            self.test_connectivity()

    def test_connectivity(self):
        """
        Test connectivity
        :return: {bool} Return true if successful else raise exception
        """
        response = self.session.get(self._get_full_url("ping"))
        self.validate_response(response)

        return True

    def submit_url_for_scan(self, url, visibility):
        """
        Submit URLs for scanning.
        :param url: {str} url for submit
        :param visibility: {str} Scanning visibility
        :return: {str} submission uuid
        """
        payload = {"url": url, "visibility": visibility}
        response = self.session.post(self._get_full_url("scan"), json=payload)
        self.validate_response(response)

        return self.parser.get_scan_id(response.json())

    def get_url_scan_report(self, scan_id):
        """
        Get scan report
        :param scan_id: {str} Scan id for get status
        :return: {URL} object if scan is completed None otherwise (in case of API returns 404)
        """
        response = self.session.get(self._get_full_url("result", scan_id=scan_id))
        if response.status_code == NOT_FOUND_STATUS_CODE:
            return None
        self.validate_response(response)

        return self.parser.build_url_object(response.json())

    def get_screenshot_content(self, url):
        """
        Get scan screenshot
        :param url: {str} screenshot URL
        :return: {request.Response} request content
        """
        response = self.session.get(url)
        response.raise_for_status()

        return response.content

    def get_scan_report_by_id(self, url_id):
        """
        Get scan full details by id
        :param url_id: {str} scan id
        :return: {ScanDetails} Instance of ScanDetails object
        """
        response = self.session.get(self._get_full_url("result", scan_id=url_id))
        self.validate_response(response)

        return self.parser.build_scan_details_object(response.json())

    def search_scans(self, entity, limit):
        """
        Searching existing scans by domains attribute
        :param entity: {str} item for searching
        :param limit: {int} size as param
        :return: {list} list of SearchObject instance
        """
        payload = {"q": entity, "size": limit}
        response = self.session.get(self._get_full_url("search"), params=payload)
        self.validate_response(response)

        return self.parser.build_results(response.json(), "build_search_object")

    @staticmethod
    def _get_full_url(url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(API_ROOT, API_ENDPOINTS[url_id].format(**kwargs))

    @classmethod
    def get_api_error_message(cls, exception):
        """
        Get API error message
        :param exception: {Exception} The api error
        :return: {str} error message
        """
        try:
            response_json = json.loads(exception.response.content)
            return response_json.get("message")
        except:
            return None

    @classmethod
    def validate_response(
        cls, response, error_msg="An error occurred", force_json_result=True
    ):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        :param force_json_result: {bool} If True raise exception if result is not json
        """
        try:
            response.raise_for_status()
            if force_json_result:
                response.json()

        except requests.HTTPError as error:
            error_message = cls.get_api_error_message(error)
            if response.status_code == BAD_REQUEST and "DNS" in error_message:
                raise UrlDnsScanError(error_message)
            if error_message:
                raise UrlScanError(error_message)
            raise Exception(f"{error_msg}: {error} {error.response.content}")

        return True
