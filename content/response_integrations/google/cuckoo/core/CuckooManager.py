# ============================================================================#
# title           :CuckooManager.py
# description     :This Module contain all Cuckoo operations functionality
# author          :avital@siemplify.co
# date            :27-02-2018
# python_version  :2.7
# libreries       : requests, json
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import os
import base64
from functools import reduce

# ============================== CONSTS ===================================== #

COMPLETED_STATUSES = ["completed", "failure", "reported"]
FAILURE_STATUS = "failure"
REPORTED_STATUS = "reported"
RETRY_TIMES = 3
CA_CERTIFICATE_FILE_PATH = "cacert.pem"


# ============================= CLASSES ===================================== #
class CuckooManagerError(Exception):
    """
    General Exception for Cuckoo manager
    """

    pass


class CuckooManager:
    """
    Cuckoo manager
    """

    def __init__(
        self,
        server_address,
        web_interface_address,
        ca_certificate_file,
        verify_ssl,
        api_token,
    ):
        self.server_address = server_address
        self.web_interface_address = web_interface_address
        self.session = requests.Session()
        self.api_token = api_token
        if ca_certificate_file:
            try:
                file_content = base64.b64decode(ca_certificate_file)
                with open(CA_CERTIFICATE_FILE_PATH, "w+") as f:
                    f.write(file_content.decode("utf-8"))

            except Exception as e:
                raise CuckooManagerError(e)

        if verify_ssl and ca_certificate_file:
            verify = CA_CERTIFICATE_FILE_PATH

        elif verify_ssl and not ca_certificate_file:
            verify = True
        else:
            verify = False

        self.verify = verify

        # will sleep for (sec): {backoff factor} * (2 ** ({number of total retries} - 1))
        # [0.0s, 20s, 40s, etc]
        retries = Retry(total=RETRY_TIMES, backoff_factor=10, status_forcelist=[404])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def test_connectivity(self):
        """
        Test connectivity to Cuckoo instance
        :return: {bool} true if connection successful, exception otherwise
        """
        try:
            url = f"{self.server_address}/cuckoo/status"

            headers = {}
            if self.api_token:
                headers = {"Authorization": f"Bearer {self.api_token}"}

            response = requests.get(url, verify=self.verify, headers=headers)
            response.raise_for_status()

            return True

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to connect to {self.server_address}: {error} {error.response.content}"
            )
        except Exception as error:
            raise CuckooManagerError(
                f"Unable to connect to {self.server_address}: {error} {error}"
            )

    def submit_url(self, suspicious_url):
        """
        Submit a url for analysis
        :param suspicious_url: The url to submit
        :return: {int} The newly created task's id
        """
        try:
            url = f"{self.server_address}/tasks/create/url"

            headers = {}
            if self.api_token:
                headers = {"Authorization": f"Bearer {self.api_token}"}

            response = requests.post(
                url, data={"url": suspicious_url}, verify=self.verify, headers=headers
            )
            response.raise_for_status()

            return response.json()["task_id"]

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to submit {suspicious_url}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to submit {suspicious_url}: {error} {error}"
            )

    def submit_file(self, file_path):
        """
        Submit a file to analysis
        :param file_path: The path of the file to submit
        :return: {int} The newly created task's id
        """
        try:
            with open(file_path, "rb") as sample:
                files = {"file": (os.path.basename(file_path), sample.read())}
                url = f"{self.server_address}/tasks/create/file"

                headers = {}
                if self.api_token:
                    headers = {"Authorization": f"Bearer {self.api_token}"}

                response = requests.post(
                    url, files=files, verify=self.verify, headers=headers
                )
                response.raise_for_status()

                return response.json()["task_id"]

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to submit {file_path}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(f"Unable to submit {file_path}: {error} {error}")

    def submit_file_in_memory(self, filename, file_content):
        """
        Submit a file to analysis from memory
        :param filename: {str} The name of the file to submit
        :param file_content: {str} The content of the file to submit
        :return: {int} The newly created task's id
        """
        try:
            files = {"file": (filename, file_content)}
            url = f"{self.server_address}/tasks/create/file"

            headers = {}
            if self.api_token:
                headers = {"Authorization": f"Bearer {self.api_token}"}

            response = requests.post(
                url, files=files, verify=self.verify, headers=headers
            )
            response.raise_for_status()

            return response.json()["task_id"]

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to submit {filename}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(f"Unable to submit {filename}: {error} {error}")

    def is_task_completed(self, task_id):
        """
        Checks if task is completed
        :param task_id: The task's id
        :return: {bool} true if completed, false otherwise.
        """
        try:
            status = self.get_task_status(task_id)["task"]["status"]
            return status in COMPLETED_STATUSES

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error}"
            )

    def is_task_failed(self, task_id):
        """
        CHeck if task has failed
        :param task_id: The task's id
        :return: {bool} true if failed, false otherwise
        """
        try:
            status = self.get_task_status(task_id)["task"]["status"]
            return status == FAILURE_STATUS

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error}"
            )

    def is_task_reported(self, task_id):
        """
        Check if task has reported
        :param task_id: The task's id
        :return: {bool} true if reported, false otherwise
        """
        try:
            status = self.get_task_status(task_id)["task"]["status"]
            return status == REPORTED_STATUS

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error}"
            )

    def get_task_status(self, task_id):
        """
        Get tasks' status
        :param task_id: The task's id
        :return: {json} The task's status report
        """
        try:
            url = f"{self.server_address}/tasks/view/{task_id}"

            headers = {}
            if self.api_token:
                headers = {"Authorization": f"Bearer {self.api_token}"}

            response = requests.get(url, verify=self.verify, headers=headers)

            response.raise_for_status()

            return response.json()

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error}"
            )

    def cancel_task(self, task_id):
        """
        Cancel a task by ID
        :param task_id: The ID of the task to cancel
        :return: {JSON} Cancellation status (i.e {u'status': u'OK'})
        """
        try:
            url = f"{self.server_address}/tasks/delete/{task_id}"

            headers = {}
            if self.api_token:
                headers = {"Authorization": f"Bearer {self.api_token}"}

            response = requests.get(url, verify=self.verify, headers=headers)

            response.raise_for_status()

            # Cancellation status (i.e: {u'status': u'OK'})
            return response.json()

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to check status of task {task_id}: {error} {error}"
            )

    def get_tar_report(self, task_id):
        """
        Get a full report of a task (tar.bz2 format). Contains cuckoo logs,
        analysis reports, screenshots, etc.
        :param task_id: The task's id
        :return: {str} Content of the tar.bz2 report
        """
        try:
            url = f"{self.server_address}/tasks/report/{task_id}/all"

            headers = {}
            if self.api_token:
                headers = {"Authorization": f"Bearer {self.api_token}"}

            response = requests.get(url, verify=self.verify, headers=headers)

            response.raise_for_status()

            return response.content

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to get zip report of task {task_id}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to get zip report of task {task_id}: {error} {error}"
            )

    def get_report(self, task_id):
        """
        Get json report of a task
        :param task_id: The task's id
        :return: {json} The task's JSON report
        """
        try:
            url = f"{self.server_address}/tasks/report/{task_id}/json"

            headers = {}
            if self.api_token:
                headers = {"Authorization": f"Bearer {self.api_token}"}

            response = requests.get(url, verify=self.verify, headers=headers)

            response.raise_for_status()

            return response.json()

        except requests.HTTPError as error:
            raise CuckooManagerError(
                f"Unable to get report of task {task_id}: {error} {error.response.content}"
            )

        except Exception as error:
            raise CuckooManagerError(
                f"Unable to get report of task {task_id}: {error} {error}"
            )

    def construct_csv(self, results):
        """
        Constructs a csv from results
        :param results: The results to add to the csv (results are list of flat dicts)
        :return: {list} csv formatted list
        """
        csv_output = []
        headers = reduce(set.union, list(map(set, list(map(dict.keys, results)))))

        csv_output.append(",".join(map(str, headers)))

        for result in results:
            csv_output.append(
                ",".join(
                    [
                        s.replace(",", " ")
                        for s in map(
                            str,
                            [str(result.get(h, None)).encode("utf-8") for h in headers],
                        )
                    ]
                )
            )

        return csv_output

    def construct_report_url(self, task_id):
        """
        Get report GUI URL.
        :param task_id: {string} The ID of the task that needed to be fetched.
        :return: {string} Report URL.
        """
        return f"{self.web_interface_address}/analysis/{task_id}/summary/"


#
