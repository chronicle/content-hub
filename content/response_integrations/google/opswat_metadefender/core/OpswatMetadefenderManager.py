# ==============================================================================
# title           :OpswatMetadefenderManager.py
# description     :This Module contain all Opswat Metadefender operations functionality
# author          :org@siemplify.co
# date            :12-17-17
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
from urllib.parse import urljoin
from copy import deepcopy
import datetime

# =====================================
#             CONSTANTS               #
# =====================================
OPSWAT_API_RROT = "http://<server_addr>/metascan_rest/"
OPSWAT_API_KEY_INFO_URL_SUFFIX = "apikey"
# {0} for file hash
OPSWAT_HASH_RESULTS_URL_SUFFIX = "hash/{0}"
OPSWAT_SCAN_HASH_URL_SUFFIX = "file"
# {0} for scan_id
OPSWAT_SCAN_RESULTS_URL_SUFFIX = "file/{0}"
SCAN_HEADERS = {"filename": ""}
SCAN_TIMEOUT = 100  # seconds


# =====================================
#              CLASSES                #
# =====================================
class OpswatMetadefenderManagerError(Exception):
    """
    General Exception for Opswat Metadefender manager
    """

    pass


class OpswatMetadefenderManager:
    """
    Responsible for all Opswat Metadefender operations functionality
    """

    def __init__(self, api_root, api_key=None, verify_ssl=False):
        self.api_root = api_root if api_root.endswith("/") else api_root + "/"
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.headers = {}
        if api_key:
            self.headers.update({"apikey": self.api_key})

    def test_conectivity(self):
        """
        Test connection to sever
        :return: {boolean}
        """
        url = urljoin(self.api_root, OPSWAT_API_KEY_INFO_URL_SUFFIX)
        req = requests.get(url, headers=self.headers, verify=self.verify_ssl)
        if req.ok:
            return True
        return False

    def find_hash_reputation(self, file_hash):
        """
        Retrieve hash details and old scan results from Opswat
        :param file_hash: {string}
        :return: {dict} Hash reputation details
        """
        url = urljoin(self.api_root, OPSWAT_HASH_RESULTS_URL_SUFFIX)
        url = url.format(file_hash)
        req = requests.get(url, headers=self.headers, verify=self.verify_ssl)
        if "data_id" in req.json():
            return req.json()
        else:
            return None

    def scan_file(self, file_content, file_name=None):
        """
        Upload file to scan on Opswat Metadefender
        :param file_content: {byteArray} File byte-array (binary data)
        :param file_name: {stirng} The uploaded file name
        :return: {string} Scan Job ID
        """
        headers = deepcopy(self.headers)
        if file_name:
            headers["filename"] = file_name
        url = urljoin(self.api_root, OPSWAT_SCAN_HASH_URL_SUFFIX)
        req = requests.post(
            url, headers=headers, data=file_content, verify=self.verify_ssl
        )
        return req.json()["data_id"]

    def wait_for_scan_results(self, scan_id, timeout=SCAN_TIMEOUT):
        """
        Wait for file scan complete results
        :param scan_id: {string} Scan Job ID
        :param timeout: {int} The timeout for waiting (In Seconds)
        :return: {dict} Scan details
        """
        url = urljoin(self.api_root, OPSWAT_SCAN_RESULTS_URL_SUFFIX)
        url = url.format(scan_id)
        req = requests.get(url, headers=self.headers, verify=self.verify_ssl)
        timestamp = datetime.datetime.now()
        # Run with timeout checking
        while datetime.datetime.now() - datetime.timedelta(seconds=timeout) < timestamp:
            report = req.json()
            if report["scan_results"]["progress_percentage"] == 100:
                return report
            # Refetch scan results
            req = requests.get(url)
        return None

    def report_to_csv(self, report):
        """
        Convers Scan details report to CSV Format
        :param report: {dict} Scan details report
        :return: {stirng} Scan Results in CSV format
        """
        csv = []
        if "scan_results" not in report or "scan_details" not in report["scan_results"]:
            raise OpswatMetadefenderManagerError(
                "Report not in currect format, cannot convert to csv"
            )
        if not report["scan_results"]["scan_details"]:
            raise OpswatMetadefenderManagerError("Report has no scan results")
        columns = "Source,Result,Detected"
        csv.append(columns)
        for engine, scan_result in list(report["scan_results"]["scan_details"].items()):
            source = engine
            result = scan_result["threat_found"] or "None"
            detected = "True" if scan_result["scan_result_i"] == 1 else "False"
            csv_entry = ",".join([source, result, detected])
            csv.append(csv_entry)
        return csv
