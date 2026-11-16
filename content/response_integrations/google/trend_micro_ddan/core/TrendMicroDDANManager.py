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
import base64
import copy
import hashlib
import platform
import uuid
import requests
from urllib.parse import urljoin
from .TrendMicroDDANExceptions import TrendMicroDDANInProgressException
from .TrendMicroDDANParser import TrendMicroDDANParser
from .UtilsManager import validate_response
from .constants import ENDPOINTS, PRODUCT_NAME, SOURCE_NAME, IN_PROGRESS_STATUS_CODE
from soar_sdk.SiemplifyUtils import unix_now


class TrendMicroDDANManager:
    def __init__(self, api_root, api_key, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        Args:
            api_root (str): API root of the TrendMicroDDAN instance
            api_key (str): API key of the TrendMicroDDAN account
            verify_ssl (bool): Specifies if certificate that is configured on the api root should be validated
            siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = TrendMicroDDANParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.client_id = str(uuid.uuid4())
        self.default_headers = self.prepare_default_headers()

    def prepare_default_headers(self):
        """
        Prepare default headers for API requests
        Args:

        Returns:
            (dict) dict of default headers
        """
        return {
            "X-DTAS-ProtocolVersion": "2.0",
            "X-DTAS-ClientUUID": self.client_id,
            "X-DTAS-Time": str(unix_now()),
            "X-DTAS-Challenge": str(uuid.uuid4()),
            "X-DTAS-ProductName": PRODUCT_NAME,
            "X-DTAS-ClientHostname": platform.node(),
            "X-DTAS-SourceID": "1",
            "X-DTAS-SourceName": SOURCE_NAME,
        }

    def prepare_request_headers(self, additional_headers=None, body=""):
        """
        Prepare headers for API requests
        Args:
            additional_headers (dict): additional header to add to default ones
            body: (str): body of request
        Returns:
            (dict) dict of headers
        """
        headers = copy.deepcopy(self.default_headers)

        if additional_headers:
            headers.update(additional_headers)

        checksum = self.calculate_checksum(headers, body)
        headers["X-DTAS-Checksum"] = checksum.hexdigest()
        return headers

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

    def calculate_checksum(self, headers, body=""):
        """
        Calculate headers checksum
        Args:
            headers (dict): headers dict
            body: (str): body of request
        Returns:
            (str) calculated checksum
        """
        checksum = self.api_key

        if "X-DTAS-ChecksumCalculatingOrder" in headers:
            x_dtas_checksum_calculating_order_list = headers.get(
                "X-DTAS-ChecksumCalculatingOrder"
            ).split(",")

            for key in x_dtas_checksum_calculating_order_list:
                checksum += headers[key]
        else:
            for key, value in headers.items():
                if (
                    "X-DTAS-" in key
                    and "X-DTAS-Checksum" not in key
                    and "X-DTAS-ChecksumCalculatingOrder" not in key
                ):
                    checksum += value

        checksum += body
        return hashlib.sha1(checksum.encode("utf-8"))

    def register(self):
        """
        Register
        Args:

        Returns:
            (bool) True if successful, exception otherwise
        """
        url = self._get_full_url("register")
        response = self.session.get(url, headers=self.prepare_request_headers())
        validate_response(response)
        return True

    def unregister(self):
        """
        Unregister
        Args:

        Returns:
            () None
        """
        url = self._get_full_url("unregister")
        response = self.session.get(url, headers=self.prepare_request_headers())
        validate_response(response)

    def test_connectivity(self):
        """
        Test connectivity
        Args:

        Returns:
            () None
        """
        url = self._get_full_url("test_connection")
        response = self.session.get(url, headers=self.prepare_request_headers())
        validate_response(response)

    def check_duplicate(self, sha1_hash):
        """
        Check duplicates for file url
        Args:
            sha1_hash (str): sha1 hash to use in request
        Returns:
            (str)
        """
        headers = self.prepare_request_headers(
            {"Content-Type": "text/plain"}, sha1_hash
        )

        url = self._get_full_url("check_duplicate_sample")
        response = self.session.put(url, headers=headers, data=sha1_hash)
        validate_response(response)
        return response.text

    def submit_sample(self, sha1_hash, sample_type, sample):
        """
        Submit sample - file or file url
        Args:
            sha1_hash (str): sha1 hash to use in request
            sample_type (str): specifies type of sample, file or file url
            sample (str): sample to use in request can be url or file
        Returns:
            () None
        """
        headers = self.prepare_request_headers(
            {
                "X-DTAS-SHA1": sha1_hash,
                "X-DTAS-SampleType": sample_type,
                "X-DTAS-ChecksumCalculatingOrder": "X-DTAS-ProtocolVersion,X-DTAS-ClientUUID,X-DTAS-SourceID,"
                "X-DTAS-SourceName,X-DTAS-SHA1,X-DTAS-Time,X-DTAS-SampleType,"
                "X-DTAS-Challenge",
            }
        )

        url = self._get_full_url("upload_sample")
        self.session.post(url, headers=headers, files={"uploadsample": sample})

    def get_report(self, sha1_hash):
        """
        Get file url report
        Args:
            sha1_hash (str): sha1 hash to use in request
        Returns:
            (Report) Report object
        """
        headers = self.prepare_request_headers({"X-DTAS-SHA1": sha1_hash})

        url = self._get_full_url("get_report")
        response = self.session.get(url, headers=headers)

        if response.status_code == IN_PROGRESS_STATUS_CODE:
            raise TrendMicroDDANInProgressException

        validate_response(response)
        return self.parser.build_report_object(
            self.parser.convert_xml_to_json(response.text)
        )

    def get_event_logs(self, sha1_hash, limit):
        """
        Get event logs
        Args:
            sha1_hash (str): sha1 hash to use in request
            limit (int): limit for results
        Returns:
            ([EventLog]) list of EventLog objects
        """
        headers = self.prepare_request_headers({"X-DTAS-SHA1": sha1_hash})

        url = self._get_full_url("get_event_log")
        response = self.session.get(url, headers=headers)
        validate_response(response)
        return self.parser.build_event_log_objects(
            self.parser.convert_xml_to_json(response.text)
        )[:limit]

    def get_suspicious_objects(self, sha1_hash, limit):
        """
        Get suspicious objects
        Args:
            sha1_hash (str): sha1 hash to use in request
            limit (int): limit for results
        Returns:
            ([SuspiciousObject]) list of SuspiciousObject objects
        """
        headers = self.prepare_request_headers({"X-DTAS-SHA1": sha1_hash.upper()})

        url = self._get_full_url("get_suspicious_object")
        response = self.session.get(url, headers=headers)
        validate_response(response)
        return self.parser.build_suspicious_object_objects(
            self.parser.convert_xml_to_json(response.text)
        )[:limit]

    def get_screenshot(self, sha1_hash):
        """
        Get screenshot
        Args:
            sha1_hash (str): sha1 hash to use in request
        Returns:
            (str) base64 encoded screenshot
        """
        headers = self.prepare_request_headers({"X-DTAS-SHA1": sha1_hash})

        url = self._get_full_url("get_sandbox_screenshot")
        response = self.session.get(url, headers=headers)
        validate_response(response)
        return base64.b64encode(response.content).decode()
