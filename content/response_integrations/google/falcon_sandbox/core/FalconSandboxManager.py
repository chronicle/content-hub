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
# title           :FalconSandboxManager.py
# description     :This Module contain all Falcon Sandbox operations functionality
# author          :avital@siemplify.co
# date            :28-03-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests


# ============================== CONSTS ===================================== #
FALCON_API_ROOT_V2 = "https://www.hybrid-analysis.com/api/v2"

HEADERS = {"User-Agent": "FalconFalcon Sandbox", "api-key": None}
COMPLETED_STATUS = "SUCCESS"
ERROR_STATUS = "ERROR"
IN_QUEUE_STATUS = "IN_QUEUE"
IN_PROGRESS_STATUS = "IN_PROGRESS"
ENVIRONMENTS = {
    "100": "Windows 7 32 bit",
    "110": "Windows 7 32 bit (HWP Support)",
    "120": "Windows 7 64 bit",
    "200": "Android Static Analysis",
    "300": "Linux (Ubuntu 16.04, 64 bit)",
}


# ============================= CLASSES ===================================== #
class FalconSandboxManagerError(Exception):
    """
    General Exception for Falcon Sandbox manager
    """

    pass


class FalconSandboxInvalidCredsError(Exception):
    """
    Invalid creds for Falcon Sandbox manager
    """

    pass


class FalconSandboxAnalysisReportError(Exception):
    """
    Analysis report doesn't exist error
    """

    pass


class FalconSandboxManager:

    def __init__(self, server_address, api_key):
        self.server_address = server_address
        self.api_key = api_key
        self.headers = HEADERS
        self.headers["api-key"] = api_key

    def test_connectivity(self):
        """
        Test connectivity to Falcon Sandbox
        :return: {bool} True if connection successful, False otherwise.
        """
        url = f"{self.server_address}/key/current"
        response = requests.get(url, headers=self.headers)
        self.validate_response(response)
        return True

    def submit_file(self, file_path, environment_id):
        """
        Submit a file for analysis
        :param file_path: {str} The path of the file to analyze
        :param environment_id:Environment ID. Available environments ID:
            300: 'Linux (Ubuntu 16.04, 64 bit)',
            200: 'Android Static Analysis',
            120: 'Windows 7 64 bit',
            110: 'Windows 7 32 bit (HWP Support)',
            100: 'Windows 7 32 bit'
        :return: {tuple} The new job's id, The hash of the uploaded file
        """
        files = {"file": open(file_path, "rb")}
        url = f"{self.server_address}/submit/file"
        response = requests.post(
            url,
            data={"environment_id": environment_id},
            files=files,
            headers=self.headers,
        )

        self.validate_response(response)
        return response.json()["job_id"], response.json()["sha256"]

    def submit_file_by_url(self, url_to_analyze, environment_id):
        """
        Submit a file by url for analysis
        :param url_to_analyze: {str} The url to the file to analyze
        :param environment_id:Environment ID. Available environments ID:
            300: 'Linux (Ubuntu 16.04, 64 bit)',
            200: 'Android Static Analysis',
            120: 'Windows 7 64 bit',
            110: 'Windows 7 32 bit (HWP Support)',
            100: 'Windows 7 32 bit'
        :return: {str} The new job's id
        """
        url = f"{self.server_address}/submit/url"
        response = requests.post(
            url,
            data={"environment_id": environment_id, "url": url_to_analyze},
            headers=self.headers,
        )
        self.validate_response(response)
        return response.json()["job_id"], response.json()["sha256"]

    def submit_url(self, url_to_scan, env_id):
        """
        Submit a url for analysis
        :param url_to_scan: {str} The url to analyze
        :param env_id: {int} Environment ID. Available environments ID:
            300: 'Linux (Ubuntu 16.04, 64 bit)',
            200: 'Android Static Analysis',
            120: 'Windows 7 64 bit',
            110: 'Windows 7 32 bit (HWP Support)',
            100: 'Windows 7 32 bit'
        :return: {str} The new job's id
        """
        request_url = f"{self.server_address}/submit/url"
        response = requests.post(
            request_url,
            data={"url": url_to_scan, "environment_id": env_id},
            headers=self.headers,
        )
        self.validate_response(response)
        return response.json()["job_id"], response.json()["sha256"]

    def get_job_state(self, job_id):
        """
        Get job state.
        :param job_id: {str} The job's id
        :return: {dict} The state of the job.
        """
        url = f"{self.server_address}/report/{job_id}/state"
        response = requests.get(url, headers=self.headers)
        self.validate_response(response)
        response_json = response.json()
        return {
            "is_job_completed": response_json.get("state")
            not in [IN_QUEUE_STATUS, IN_PROGRESS_STATUS],
            "is_success": (response_json.get("state") == COMPLETED_STATUS),
            "response": response_json,
        }

    def is_job_completed(self, job_id):
        """
        Check if a given job has completed.
        :param job_id: {str} The job's id
        :return: {bool} True if completed or error, False otherwise.
        """
        state = self.get_job_state(job_id)
        return state["is_job_completed"]

    def get_report(self, job_id, type="misp"):
        """
        Download a report for a given job
        :param job_id: {str} The job's id
        :param type: {str} The report file type. Available types:
            xml, json, pdf, html, pcap, maec, stix, misp, misp-json, openioc,
            bin, crt, memory.
            For details visit:
                https://www.hybrid-analysis.com/docs/api/v2#/Report/get_report__id__file__type_
        :return: {tuple} The file name of the report, the report content
        """
        url = f"{self.server_address}/report/{job_id}/file/{type}"
        response = requests.get(url, headers=self.headers)
        self.validate_response(response)
        return response.headers["Vx-Filename"], response.content

    def get_report_by_hash(self, hash, env_id, type="misp"):
        """
        Download a report for a given hash and environment id
        :param hash: {str} The hash
        :param env_id: {str} The env id
        :param type: {str} The report file type. Available types:
            xml, json, pdf, html, pcap, maec, stix, misp, misp-json, openioc,
            bin, crt, memory.
            For details visit:
                https://www.hybrid-analysis.com/docs/api/v2#/Sandbox_Report/get_report__id__report__type_
        :return:{tuple} The file name of the report, the report content
        """
        url = f"{self.server_address}/report/{hash}:{env_id}/report/{type}"
        response = requests.get(url, headers=self.headers)
        self.validate_response(response)
        return response.headers["Vx-Filename"], response.content

    def get_report_by_job_id(self, job_id, type="misp"):
        """
        Download a report for a given job id
        :param job_id: {str} The job id
        :param type: {str} The report file type. Available types:
            xml, json, pdf, html, pcap, maec, stix, misp, misp-json, openioc,
            bin, crt, memory.
            For details visit:
                https://www.hybrid-analysis.com/docs/api/v2#/Sandbox_Report/get_report__id__report__type_
        :return:{tuple} The file name of the report, the report content
        """
        url = f"{self.server_address}/report/{job_id}/report/{type}"
        response = requests.get(url, headers=self.headers)
        self.validate_response(response)
        return response.headers["Vx-Filename"], response.content

    def get_scan_info_multiple_scans(self, filehash, environment_id):
        """
        Get the scan info of a given hash
        :param filehash: {str} hash
        :param environment_id:Environment ID. Available environments ID:
            300: 'Linux (Ubuntu 16.04, 64 bit)',
            200: 'Android Static Analysis',
            120: 'Windows 7 64 bit',
            110: 'Windows 7 32 bit (HWP Support)',
            100: 'Windows 7 32 bit'
        :return:{json} The scan info
        """
        url = f"{self.server_address}/report/summary"
        response = requests.post(
            url,
            data={"hashes[]": [f"{filehash}:{environment_id}"]},
            headers=self.headers,
        )

        return response

    def get_scan_info_single_scan(self, filehash, environment_id):
        """
        Request information for a single scan
        :param filehash: {str} hash
        :param environment_id:Environment ID. Available environments ID:
            300: 'Linux (Ubuntu 16.04, 64 bit)',
            200: 'Android Static Analysis',
            120: 'Windows 7 64 bit',
            110: 'Windows 7 32 bit (HWP Support)',
            100: 'Windows 7 32 bit'
        :return:{json} The scan info
        """
        url = f"{self.server_address}/report/{filehash}:{environment_id}/summary"
        response = requests.get(url, headers=self.headers)

        return response

    def get_scan_info(self, filehash, environment_id):

        try:
            # Firstly we try to query info for all the scans -> if no scans found it raises 404
            response_multiple_scans = self.get_scan_info_multiple_scans(
                filehash, environment_id
            )
            self.validate_response(response_multiple_scans)

            return {
                "scanned_element": "original",
                "scan_info": response_multiple_scans.json(),
            }
        except Exception:
            try:
                # If we couldn't get information about multiple scans we try to query a single
                response = self.get_scan_info_single_scan(filehash, environment_id)
                self.validate_response(response)
                return {"scanned_element": "original", "scan_info": response.json()}
            except FalconSandboxAnalysisReportError:
                # If the single scan doesn't exist we will try to get information of the child
                return {
                    "scanned_element": "child",
                    "scan_info": self.get_child_scan_info(
                        response.json().get("related_id")[0]
                    ),
                }

    def get_child_scan_info(self, job_id):
        """
        Request for scan info about the files's child
        :param job_id: {str} The ID of the job to get the info for
        :return:{Response} The scan info as Response
        """
        url = f"{self.server_address}/report/{job_id}/summary"
        response = requests.get(url, headers=self.headers)

        self.validate_response(response)
        return response.json()

    def get_scan_info_by_job_id(self, job_ids):
        """
        Get the scan info of a given job
        :param job_id: {str} The ID of the job to get the info for
        :return:{json} The scan info
        """
        url = f"{self.server_address}/report/summary"
        response = requests.post(url, data={"hashes[]": job_ids}, headers=self.headers)
        self.validate_response(response)
        return response.json()

    def search(
        self,
        filename=None,
        filetype=None,
        filetype_desc=None,
        verdict=None,
        av_detect=None,
        vx_family=None,
        tag=None,
        port=None,
        host=None,
        domain=None,
        url=None,
        similar_to=None,
        context=None,
    ):
        """
        Search for an existing analysis
        :param filename: {str} Filename e.g. invoice.exe
        :param filetype: {str} Filetype e.g. docx
        :param filetype_desc: {str} Filetype description e.g. PE32 executable
        :param verdict: {int} Verdict e.g. 1 (available: 1 'whitelisted', 2 'no verdict', 3 'no specific threat', 4 'suspicious', 5 'malicious')
        :param av_detect: {str} AV Multiscan range e.g. 50-70 (min 0, max 100)
        :param vx_family: {str} AV Family Substring e.g. nemucod
        :param tag: {str} Hashtag e.g. ransomware
        :param port: {int} Port e.g. 8080
        :param host: {str} Host e.g. 192.168.0.1
        :param domain: {str} Domain e.g. checkip.dyndns.org
        :param url: {str} HTTP Request Substring e.g. google
        :param similar_to: {str} Similar Samples e.g. <sha256>
        :param context: {str} Sample Context e.g. <sha256>
        :return: {list} List of found results, in the following format:
            {
              "verdict": "string",
              "av_detect": "string",
              "threat_score": 0,
              "vx_family": "string",
              "job_id": "string",
              "sha256": "string",
              "environment_id": "string",
              "analysis_start_time": "2018-03-28T14:10:20.608Z",
              "submit_name": "string",
              "environment_description": "string",
              "size": 0,
              "type": "string",
              "type_short": "string"
            }
        """
        search_terms = {
            "filename": filename,
            "filetype": filetype,
            "filetype_desc": filetype_desc,
            "verdict": verdict,
            "av_detect": av_detect,
            "vx_family": vx_family,
            "tag": tag,
            "port": port,
            "host": host,
            "domain": domain,
            "url": url,
            "similar_to": similar_to,
            "context": context,
        }

        # Remove None values (since / to) to prevent exception from the server
        search_terms = {
            key: value for key, value in list(search_terms.items()) if value
        }

        request_url = f"{self.server_address}/search/terms"
        response = requests.post(request_url, data=search_terms, headers=self.headers)
        self.validate_response(response)
        return response.json()["result"]

    @staticmethod
    def validate_response(response):
        try:
            if response.status_code == 403:
                raise FalconSandboxInvalidCredsError(
                    "No permission to access endpoint. Please validate the api key and its permissions."
                )
            if (
                response.status_code == 410
                and "does not have an associated analysis report"
                in response.json().get("message")
            ):
                raise FalconSandboxAnalysisReportError(
                    "Analysis report for the parent file wasn't found."
                )
            response.raise_for_status()

        except FalconSandboxAnalysisReportError:
            raise

        except FalconSandboxInvalidCredsError:
            raise

        except Exception as e:
            try:
                response.json()
            except:
                raise FalconSandboxManagerError(f"{e}\n{response.content}")

            raise FalconSandboxManagerError(
                f"{e}\n{response.json()['message']}\n{response.content}"
            )

    @staticmethod
    def get_environment_id_by_name(name):
        for env_id, env_name in list(ENVIRONMENTS.items()):
            if env_name == name:
                return env_id

        raise FalconSandboxManagerError(f"Environment {name} is not recognized.")
