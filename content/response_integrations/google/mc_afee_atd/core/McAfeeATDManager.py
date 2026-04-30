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

# ==============================================================================
# title           :McAfeeATDManager.py
# description     :McAfeeATDManager integration logic.
# author          :victor@siemplify.co
# date            :15-8-18
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations

import base64
import copy
import json

import requests

# =====================================
#               CONSTS                #
# =====================================
# Consts
DEFAULT_THRESHOLD = 3

LOGIN_HEADER_TYPE = "application/vnd.ve.v1.0+json"

# URL
LOGIN_URL = "session.php"
SUBMIT_FILE_URL = "fileupload.php"
GET_PDF_REPORT_URL = "showreport.php?iTaskId={0}&iType=pdf"  # {0} - Task ID.
GET_JSON_REPORT_URL = "showreport.php?iTaskId={0}&iType=json"  # {0} - Task ID.
GET_TXT_REPORT_URL = "showreport.php?iTaskId={0}&iType=txt"  # {0} - Task ID.
CHECK_HASH_BLACKLISTED_URL = "atdHashLookup.php"
CHECK_TASK_STATUS_URL = "samplestatus.php"
GET_VM_PROFILES_URL = "vmprofiles.php"

# Headers
REQUEST_HEADERS = {"Accept": "application/vnd.ve.v1.0+json", "VE-SDK-API": ""}

# Payloads contain string with dict in it(Same in documentation + Checked).
# Payloads
SUBMIT_FILE_PAYLOAD = {
    "data": '{"data":{"xMode":0,"overrideOS":1,"messageId":"","vmProfileList":"11","submitType":"0","url":""},"filePriorityQ":"run_now" }'
}

SUBMIT_FILE_FILE_PATTERN = {"amas_filename": ""}

SUBMIT_URL_PAYLOAD = {
    "data": '{"data":{"xMode":0,"overrideOS":1,"messageId":"","vmProfileList":"11","submitType":"1","url":""}}'
}

CHECK_HASH_BLACKLISTED_PAYLOAD = {"data": '{"md5":""}'}

READY_STATUSES = ["Completed"]


# =====================================
#              CLASSES                #
# =====================================
class McAfeeATDManagerError(Exception):
    pass


class McAfeeATDManager:
    def __init__(self, api_root, username, password, verify_ssl=False):
        """:param api_root: McAfee ATD server api root {string}
        :param username: McAfee ATD username {string}
        :param password: password for the user {string}
        :param verify_ssl: Verify SSL in an HTTP reqiest or not {bool}
        """
        self.api_root = api_root if api_root[-1] == "/" else api_root + "/"
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = copy.deepcopy(REQUEST_HEADERS)
        self.session.headers["VE-SDK-API"] = self.obtain_token(
            username, password, verify_ssl
        )

    @staticmethod
    def validate_report_response(report_response, error_msg="An error occurred"):
        """Function that validates the report in the response, if a txt or pdf report returns HTML code, it's an invalid report."""
        if "html" in report_response:
            # Not a JSON - return content
            msg = "The scanning was completed, but the report is not available. Please make sure that the scan was valid."
            raise McAfeeATDManagerError(
                msg
            )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:

            # Not a JSON - return content
            msg = f"{error_msg}: {error} - {error.response.content}"
            raise McAfeeATDManagerError(
                msg
            )

    @staticmethod
    def update_string_payload_data(string_payload, parameter, value):
        """Edit McAfeeATD payload string.
        :param string_payload: json string payload {string}
        :param parameter: parameter to edit.
        :param value: value to replace with {string}
        :return: updated payload {string}
        """
        # Convert to json.
        json_payload = json.loads(string_payload)
        if json_payload.get("data"):
            json_payload["data"][parameter] = value
        else:
            json_payload[parameter] = value
        return json.dumps(json_payload)

    def obtain_token(self, username, password, verify_ssl=False):
        """Obtain session auth token.
        :param username: Use {string}
        :param password: {string}
        :return:
        """
        request_url = f"{self.api_root}{LOGIN_URL}"
        headers = copy.deepcopy(REQUEST_HEADERS)
        headers["VE-SDK-API"] = base64.b64encode(
            f"{username}:{password}".encode()
        )
        headers["Accept"] = LOGIN_HEADER_TYPE
        response = requests.get(request_url, headers=headers, verify=verify_ssl)
        self.validate_response(response)
        if not response.json().get("errorMessage"):
            return base64.b64encode(
                f"{response.json()['results'].get('session')}:{response.json()['results'].get('userId')}".encode()
            )
        msg = f'Connection error accrued, Error: {response.json().get("errorMessage")}'
        raise McAfeeATDManagerError(
            msg
        )

    def submit_file(self, file_path, profile_id):
        """Submit file for analysis.
        :param file_path: the file path of the file to be submitted {sting}
        :param profile_id: Analyzer Profile ID {string} (also called VmProfileId)
        :return: result {dict}
        """
        request_url = f"{self.api_root}{SUBMIT_FILE_URL}"
        # Arrange input data.
        files = copy.deepcopy(SUBMIT_FILE_FILE_PATTERN)
        files["amas_filename"] = open(file_path, "rb")
        data = copy.deepcopy(SUBMIT_FILE_PAYLOAD)
        # Payload is a string of a dict in a dict(So the string has to be turned into a dict and back).
        data["data"] = self.update_string_payload_data(
            data["data"], "vmProfileList", profile_id
        )

        response = self.session.post(request_url, data=data, files=files)
        self.validate_response(response)
        return (
            response.json()["results"][0].get("taskId")
            if response.json().get("results")
            else None
        )

    def submit_url(self, url, profile_id):
        """Submit file for analysis.
        :param url: {sting} the URL to be submitted
        :param profile_id: {string} Analyzer Profile ID  (also called VmProfileId) (Only profiles with internet access)
        :return: {dict} result
        """
        request_url = f"{self.api_root}{SUBMIT_FILE_URL}"
        # Arrange input data.
        data = copy.deepcopy(SUBMIT_URL_PAYLOAD)
        # Payload is a string of a dict in a dict(So the string has to be turned into a dict and back).
        data["data"] = self.update_string_payload_data(
            data["data"], "vmProfileList", profile_id
        )
        data["data"] = self.update_string_payload_data(data["data"], "url", url)

        response = self.session.post(request_url, data=data)
        self.validate_response(response)
        return (
            response.json()["results"][0].get("taskId")
            if response.json().get("results")
            else None
        )

    def get_pdf_report(self, task_id):
        """Get PDF report for task id.
        :param task_id: {string} id of a submission task
        :return: {file} file content
        """
        request_url = f"{self.api_root}{GET_PDF_REPORT_URL.format(task_id)}"
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.content

    def get_json_report(self, task_id):
        """Get PDF report for task id.
        :param task_id: {string} id of a submission task
        :return: {file} file content
        """
        request_url = f"{self.api_root}{GET_JSON_REPORT_URL.format(task_id)}"
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_txt_report(self, task_id):
        """Get TXT report for task id.
        :param task_id: {string} id of a submission task
        :return: {file} file content
        """
        request_url = f"{self.api_root}{GET_TXT_REPORT_URL.format(task_id)}"
        response = self.session.get(request_url)
        self.validate_response(response)
        self.validate_report_response(response.text)
        return response.text

    def is_hash_blacklist(self, file_hash):
        """Check if hash is blacklisted.
        :param file_hash: {string} file_hash
        :return: {bool} true if blacklisted
        """
        # Validate md5.
        if len(file_hash) != 32:
            msg = f'File hash "{file_hash}" is not MD5 type.'
            raise McAfeeATDManagerError(msg)
        request_url = f"{self.api_root}{CHECK_HASH_BLACKLISTED_URL}"
        data = copy.deepcopy(CHECK_HASH_BLACKLISTED_PAYLOAD)
        # Payload is a string of a dict in a dict(So the string has to be turned into a dict and back).
        data["data"] = self.update_string_payload_data(data["data"], "md5", file_hash)
        response = self.session.post(request_url, data=data)
        self.validate_response(response)
        # "b" in a response means blacklisted.
        return bool(response.json().get("results") and response.json().get("results").get(file_hash) == "b")

    def get_task_id_status(self, task_id):
        """Get Status of single taskID
        :param task_id: {string} id of a submission task
        :return:{string}  status -> Current status of the sample. Example: waiting / analyzing / completed.
        """
        request_url = f"{self.api_root}{CHECK_TASK_STATUS_URL}"
        response = self.session.get(request_url, params={"iTaskId": task_id})
        self.validate_response(response)
        return response.json()["results"]["status"]

    def logout(self):
        """Disconnect session
        :return:
        """
        request_url = f"{self.api_root}{LOGIN_URL}"
        response = self.session.delete(request_url)
        self.validate_response(response)

    def get_analyzer_profiles(self):
        """Retrieve all analyzer profiles details
        :return: {list of dicts}
        """
        request_url = f"{self.api_root}{GET_VM_PROFILES_URL}"
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("results", [])
