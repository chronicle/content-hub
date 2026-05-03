# ==============================================================================
# title           :JoeSandboxManager.py
# description     :This Module contain all Joe Sandbox operations functionality
# author          :zivh@siemplify.co
# date            :06-04-18
# python_version  :2.7
# libraries       :
# requirements    : jbxapi
# product_version :v2
# doc             : https://jbxcloud.joesecurity.org/userguide?sphinxurl=usage/webapi.html
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests

from urllib.parse import urljoin

# =====================================
#             CONSTANTS               #
# =====================================
DOWNLOAD_URL = "/analysis/{webid}/0/html"
ACCEPT_TAC = "1"
FINISHED_STATUS = "finished"
REPORT_WEB_LINK = "https://jbxcloud.joesecurity.org/analysis/{0}/0/html"
STATUSES = ["malicious", "suspicious"]


# =====================================
#              CLASSES                #
# =====================================


class JoeSandboxManagerError(Exception):
    """
    General Exception for Joe Sandbox manager
    """

    pass


class JoeSandboxLimitManagerError(Exception):
    """
    Limit Reached Exception for JoeSandbox manager
    """

    pass


class JoeSandboxManager:
    """
    Responsible for all Joe Sandbox operations functionality
    """
    def __init__(self, api_root, api_key, use_ssl=False):
        """
        JoeSandboxManager constructor.

        Args:
            api_root (str): JoeSandbox api root.
            api_key (str): JoeSandbox api key.
            use_ssl (bool): Enable or disable checking SSL certificates.
                            Defaults to False.
        """
        self.api_root = api_root + '/' if not api_root.endswith('/') else api_root
        self.api_key = api_key
        # Joe Sandbox Cloud requires accepting the Terms and Conditions.
        self.session = requests.Session()
        self.session.verify = use_ssl

    def get_full_url(self, endpoint):
        """
        This static method combines the API root URL and endpoint
        to create a complete URL string.

        Args:
          endpoint (str): The API endpoint .

        Returns:
          str: The complete URL string constructed by joining the API root and endpoint.
        """

        return urljoin(self.api_root, endpoint)

    def test_connectivity(self):
        """
        Check if Joe Sandbox is online or in maintenance mode.
        :return: {dict} Online is True if the Joe Sandbox servers are running or False if they are in maintenance mode.
        """
        params = {"apikey": self.api_key}
        url = self.get_full_url("api/v2/server/online")
        response = self.session.post(url, data=params)
        self.validate_response(response)
        if response.json()["data"]["online"]:
            return True
        return False

    def analyze(self, sample, comments=""):
        """
        Submit a sample and returns the associated webids for the samples.
        :param sample: {file} The sample to submit. Needs to be a file-like object.
        :param comments: {string} Comments to store with sample entry.
        :return: {dict} Dictionary of system identifier and associated webids.
        """
        url = self.get_full_url("api/v2/analysis/submit")
        res = self.session.post(url, data={
                                    "apikey": self.api_key,
                                    "comments": comments,
                                    "accept-tac": ACCEPT_TAC
                                },
                                files={"sample": sample})

        self.validate_response(res)
        return res.json()["data"]["webids"][0]

    def is_analysis_completed(self, webid):
        """
        Checks for analysis status.
        The status field is one of submitted, running, finished.
        :param webid: {int/string} Report ID to draw from.
        :return: {boolean} True if analysis finished.
        """
        params = {"apikey": self.api_key, "webid": webid}
        url = self.get_full_url("api/v2/analysis/info")
        response = self.session.post(url, data=params)
        self.validate_response(response)
        return response.json()["data"]["status"] == FINISHED_STATUS

    def get_analysis_info(self, webid):
        """
        Get analysis info
        The status field is one of submitted, running, finished.
        :param webid: {int/string} Report ID to draw from.
        :return: {dict} Dictionary of analysis and status.
        """
        params = {"apikey": self.api_key, "webid": webid}
        url = self.get_full_url("api/v2/analysis/info")
        response = self.session.post(url, data=params)
        self.validate_response(response)
        return response.json().get("data", {})

    def download_report(self, webid, resource="html"):
        """
        Retrieves the specified report for the analyzed item, referenced by webid.
        :param webid: {int/string} The id of the analysis.
        :param resource: {string} The resource type to download. Available resource types include:
        html, xml, json, jsonfixed, lighthtml, lightxml, lightjson, lightjsonfixed, executive, classhtml, classxml, clusterxml, irxml, irjson, irjsonfixed, openioc, maec, misp, graphreports, pdf
        :return: {string} report data base on the selected resource type
        """
        resource = resource.lower()
        params = {"apikey": self.api_key, "webid": webid, "type": resource}
        url = self.get_full_url("api/v2/analysis/download")
        data = self.session.post(url, data=params, stream=True)
        self.validate_response(data)
        return data.content

    def get_all_analysis(self):
        """
        List all analyses.
        :return: {list of dicts} all analyses
        """
        params = {"apikey": self.api_key}
        url = self.get_full_url("api/v2/analysis/list")
        response = self.session.post(url, data=params)
        self.validate_response(response)
        return response.json().get("data", [])

    def search(self, query):
        """
        Lists the webids of the analyses that match the given query.
        :param query: {string} MD5, SHA1, SHA256, filename, cookbook name, comment, url and report id
        :return: {list of dicts} matching webid
        """
        params = {"apikey": self.api_key, "q": query}
        url = self.get_full_url("api/v2/analysis/search")
        res = self.session.post(url, data=params)
        return res.json().get("data", [])

    @staticmethod
    def is_detection_suspicious(analysis_info):
        """
        The detection field is one of unknown, clean, suspicious, malicious.
        :param analysis_info: {dict} Dictionary of analysis and status.
        :return: {boolean} true/false
        """
        for detection in analysis_info.get("runs"):
            if detection.get("detection") in STATUSES:
                return True
        return False

    @staticmethod
    def validate_response(response):
        """
        Check if request response is ok
        """
        try:
            if (
                "number of allowed submissions (20) per day have been "
                "reached".encode("utf-8")
                in response.content
            ):
                raise JoeSandboxLimitManagerError(response.content)
            response.raise_for_status()
        except requests.HTTPError as e:
            raise JoeSandboxManagerError(
                f"An error occurred. ERROR: {e}. {response.content}"
            )
