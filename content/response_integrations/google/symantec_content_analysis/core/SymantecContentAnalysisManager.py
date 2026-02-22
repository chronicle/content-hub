# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import copy
import urllib.parse
import os

# =====================================
#             CONSTANTS               #
# =====================================
SHA256_LENGTH = 64
MD5_LENGTH = 32
# URLs
SUBMIT_FILE_URL = "rapi/cas/scan"
GET_SAMPLES_FOR_SHA256_URL = "rapi/samples/basic?sha256={0}"  # {0} - File Hash.
GET_SAMPLES_FOR_MD5_URL = "rapi/samples/basic?md5={0}"  # {0} - File Hash.
GET_PATTERNS_GOROUPS_URL = "rapi/pattern_groups"  # - For ping.

# =====================================
#             PAYLOADS                #
# =====================================
HEADERS = {"X-API-TOKEN": ""}

SUBMIT_FILE_PAYLOAD = {}

SUBMIT_FILE_TIMEOUT_HEADER = {
    "X-Response-Wait-MS": "300000"
}  # In Milliseconds. - Default 300000 milliseconds - 5 mins.


# =====================================
#              CLASSES                #
# =====================================
class SymantecContentAnalysisManagerError(Exception):
    pass


class SymantecContentAnalysisManager:
    def __init__(self, api_root, api_key, verify_ssl=False):
        """
        :param api_key: Symantec content analysis API key {string}
        :param verify_ssl: verify ssl certificate {bool}
        """
        self.api_root = self.validate_api_root(api_root)
        self.session = requests.session()
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["X-API-TOKEN"] = api_key
        self.session.verify = verify_ssl

    @staticmethod
    def validate_api_root(api_root):
        """
        Validate API root string contains '/' at the end because 'urlparse' lib is used.
        :param api_root: api root url {string}
        :return: valid api root {string}
        """
        if api_root[-1] == "/":
            return api_root
        return api_root + "/"

    @staticmethod
    def validate_response(http_response):
        """
        Validated an HTTP response.
        :param http_response: HTTP response object.
        :return: {void}
        """
        try:
            http_response.raise_for_status()

        except requests.HTTPError as err:
            raise SymantecContentAnalysisManagerError(
                f"Status Code: {http_response.status_code}, Content: {http_response.content}, Error: {err}"
            )

    def ping(self):
        """
        Test Symantec Content Analysis connectivity.
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_PATTERNS_GOROUPS_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return True

    def submit_file(self, file_path):
        """
        Upload file for scan.
        :param file_path: file path for scan {string}
        :return: result json {dict}
        """
        request_url = urllib.parse.urljoin(self.api_root, SUBMIT_FILE_URL)
        payload = copy.deepcopy(SUBMIT_FILE_PAYLOAD)
        file_base_name = os.path.basename(file_path)
        file_obj = open(file_path, "rb")
        payload[file_base_name] = (
            file_base_name,
            bytearray(file_obj.read()),
            "application/octet-stream",
        )

        headers = self.session.headers
        headers.update(copy.deepcopy(SUBMIT_FILE_TIMEOUT_HEADER))

        response = self.session.post(
            request_url,
            files=payload,
            headers=headers
        )
        self.validate_response(response)

        # Validate Errors.
        result = response.json().get("result")
        if response.json().get("result", {}).get("error"):
            raise SymantecContentAnalysisManagerError(
                f"Error occurred submitting file, ERROR: {result.get( 'error')}"
            )

        return response.json()

    def get_file_samples(self, file_hash):
        """
        Get samples for file hash.
        :param file_hash: file hash to get report for {string}
        :return: results {list}
        """
        if len(file_hash) == SHA256_LENGTH:
            request_url = urllib.parse.urljoin(
                self.api_root, GET_SAMPLES_FOR_SHA256_URL.format(file_hash)
            )
        elif len(file_hash) == MD5_LENGTH:
            request_url = urllib.parse.urljoin(
                self.api_root, GET_SAMPLES_FOR_MD5_URL.format(file_hash)
            )
        else:
            raise SymantecContentAnalysisManagerError(
                f"Error: Hash length is not valid. Hash: {file_hash}"
            )

        response = self.session.get(request_url)

        self.validate_response(response)

        return response.json().get("results", [])


#
