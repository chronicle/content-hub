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

# ============================================================================#
# title           :LastlineManager.py
# description     :This Module contain all Lastline operations functionality
# author          :amit.levizky@siemplify.co
# date            :18-03-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
from urllib.parse import urljoin
from .exceptions import (
    LastlineAPIException,
    LastlineAuthenticationException,
    LastlinePermissionException,
    LastlineInvalidParamException,
    LastlineManyRequestsException,
)
from .consts import (
    SUCCESS_CODE,
    AUTHENTICATION_ERROR,
    PERMISSION_DENIED,
    INVALID_PARAMETER_ERROR,
    TOO_MANY_REQUESTS_ERROR,
)
from .datamodels import SubmissionTask, Analysis
from .utils import remove_empty_kwargs

from .LastlineParser import LastlineParser

import requests

HEADERS = {"Content-Type": "multipart/form-data"}

ENDPOINTS = {
    "login": "/papi/login",
    "submit_url": "/papi/analysis/submit_url",
    "submit_file": "/papi/analysis/submit_file",
    "get_progress": "/papi/analysis/get_progress",
    "get_result": "/papi/analysis/get_result",
    "search_analysis_history": "/papi/analysis/get_history",
}


class LastlineManager:
    def __init__(
        self, api_root: str, username: str, password: str, verify_ssl: bool = True
    ):
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self._obtain_session_cookie()
        self.session.headers = HEADERS

        self.parser = LastlineParser()

    def _obtain_session_cookie(self):
        """
        Obtain cookie to make API calls
        """
        request_url = self._get_full_url("login")
        response = self.session.get(
            request_url, data={"username": self.username, "password": self.password}
        )
        self.session.cookies.update(response.cookies)

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise LastlineAPIException(
                    f"{error_msg}: {error} - {error.response.content}"
                )
            raise LastlineAPIException(
                f"{error_msg}: {error} {response.json().get('message')}"
            )

    def _validate_api_errors(self, response, error_msg="An error occurred"):
        """
        In case of api with specific Lastline API errors, raise the appropriate error.
        :param response: {requests.Response} Response from the API call.
        :param error_msg: {str} Error message
        :return: raise Exception if failed to validate response
        """
        if response.json().get("success") != SUCCESS_CODE:
            self.raise_api_error(response.json(), error_msg)

    @staticmethod
    def raise_api_error(response_json, error_msg):
        """
        Raise the appropriate error
        :param response_json: {Dict} Response error dictionary {success, error_code, error}
        :param error_msg: {str} Error message
        :return: raise Exception if failed to validate response
        """
        if response_json.get("error_code") == AUTHENTICATION_ERROR:
            raise LastlineAuthenticationException(
                f"{error_msg}: {response_json.get('error')}"
            )
        elif response_json.get("error_code") == PERMISSION_DENIED:
            raise LastlinePermissionException(
                f"{error_msg}: {response_json.get('error')}"
            )
        elif response_json.get("error_code") == INVALID_PARAMETER_ERROR:
            raise LastlineInvalidParamException(
                f"{error_msg}: {response_json.get('error')}"
            )
        elif response_json.get("error_code") == TOO_MANY_REQUESTS_ERROR:
            raise LastlineManyRequestsException(
                f"{error_msg}: {response_json.get('error')}"
            )

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to the Lastline service with parameters provided at the integration configuration page on
        the Marketplace tab.
        :return: raise Exception if failed to validate response
        """
        request_url = self._get_full_url("login")
        payload = {"username": self.username, "password": self.password}

        response = self.session.get(request_url, data=payload)
        self.validate_response(response, "Unable to login")
        self._validate_api_errors(response, "Unable to login")

    def submit_url(self, url_for_analysis: str, is_get_process=False) -> SubmissionTask:
        """
        Create submission task for URL if this url submission does not exists.
        Returns the summary of the task
        should be provided as action input parameter.
        :param url_for_analysis: {str} Specify URL to analyze.
        :param is_get_process: {bool} Weather if this an status update request or submission data request
        :return: {datamodels.SubmissionTask} SubmissionTask data model
        raise Exception if failed to validate response
        """
        request_url = self._get_full_url("submit_url")
        payload = {"url": url_for_analysis}

        response = self.session.post(request_url, params=payload)
        self.validate_response(response, "Unable to submit url")
        self._validate_api_errors(response, "Unable to submit url")

        return self.parser.build_submission_task_obj(
            response, is_get_process=is_get_process
        )

    def get_progress(self, uuid: str, is_get_process=True):
        """
        Get progress for a previously submitted analysis task.
        :param uuid: {str} The unique identifier of the submitted task.
        :param is_get_process: {bool} Weather if this an status update request or submission data request
        :return: {datamodels.SubmissionTask} SubmissionTask data model
        raise Exception if failed to validate response
        """
        request_url = self._get_full_url("get_progress")
        payload = {"uuid": uuid}

        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, "Unable to get progress details on submission task"
        )
        self._validate_api_errors(
            response, "Unable to get progress details on submission task"
        )

        return self.parser.build_submission_task_obj(response, is_get_process)

    def submit_file(self, file_path: str, is_get_process=False) -> SubmissionTask:
        """
        Submit analysis task for the provided URL.
        :param file_path: {str} Specify File Path to analyze.
        :param is_get_process: {bool} Weather if this an status update request or submission data request
        :return: {datamodels.SubmissionTask} SubmissionTask data model
        raise Exception if failed to validate response
        """
        self.session.headers.pop("Content-Type")
        request_url = self._get_full_url("submit_file")
        payload = {}

        files = [("file", (open(file_path, "rb")))]

        response = self.session.post(request_url, data=payload, files=files)
        self.validate_response(response, "Unable to submit file")
        self._validate_api_errors(response, "Unable to submit file")

        return self.parser.build_submission_task_obj(
            response, is_get_process=is_get_process
        )

    def get_result(
        self, uuid: str, full_report_score: int = -1, is_get_process: bool = False
    ):
        """
        Get results for a previously submitted analysis task.
        :param uuid: {str} The unique identifier of the submitted task.
        :param is_get_process: {bool} Weather if this an status update request or submission data request
        :param full_report_score: {int}  Minimum score that causes detailed analysis reports to be served; -1 indicates
         “never return full report”; 0 indicates “return full report at all times”. If report_uuid is specified,
         this parameter is ignored.
        :return: {datamodels.SubmissionTask} SubmissionTask data model
        raise Exception if failed to validate response
        """
        request_url = self._get_full_url("get_result")
        payload = {"uuid": uuid, "full_report_score": full_report_score}

        response = self.session.get(request_url, params=payload)
        self.validate_response(response, "Unable to get results")
        self._validate_api_errors(response, "Unable to get results")

        return self.parser.build_submission_task_obj(
            response, is_get_process=is_get_process
        )

    def search_analysis_history(
        self,
        submission_type: str = None,
        start_time: str = None,
        search_in_last_x_scans: int = None,
        skip_first_x_scans: int = None,
        url: str = None,
        file_md5: str = None,
        file_sha1: str = None,
    ) -> Analysis:
        """
        Search Lastline completed analysis tasks history.
        :param submission_type: {str} submission type to search for, either URL or FileHash.
        :param start_time: {int} Time frame for which to search for completed analysis tasks
        :param search_in_last_x_scans: {int} Search for report in last x analyses executed in any run.
        :param skip_first_x_scans: {int} Skip first x scans returned by any run.
        :param url: {str} Limits the results to those with the corresponding url
        :return: {datamodels.Analysis} Analysis data model
        :param file_md5: {str} File hash in MD5 format
        :param file_sha1: {str} File hash in SHA1 format
        """
        request_url = self._get_full_url("search_analysis_history")
        payload = {
            "limit": search_in_last_x_scans,
            "limit_offset": skip_first_x_scans,
            "start_time": start_time,
            "submission_type": submission_type,
            "file_md5": file_md5,
            "file_sha1": file_sha1,
            "url": url,
        }

        response = self.session.get(request_url, params=remove_empty_kwargs(**payload))
        self.validate_response(response, "Unable to get analysis history")
        self._validate_api_errors(response, "Unable to get analysis history")

        return self.parser.build_analysis_obj(response)
