# ============================================================================#
# title           :CiscoThreatGridManager.py
# description     :This Module contain all Cisco Threat Grid operations functionality
# author          :avital@siemplify.co
# date            :13-06-2018
# python_version  :2.7
# libreries       : requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests

# ============================== CONSTS ===================================== #
CROWDFALCON_BASE_URL = "https://falconapi.crowdstrike.com"
DATETIME_FORMAT = "YYYY-MM-DDTHH:MM:SSZ"
FAILED_STATE = "fail"
WAITING_STATE = "wait"
SUCCESS_STATE = "succ"
TO_PROCESS = "to_process"
NO_RESULTS = "no_results"
DESCENDING_ORDER = "desc"
SUBMITTED_AT = "submitted_at"
LIMIT = 10
DNS_PORT = 53
DNS_PROTOCOL = "DNS"
DNS_WORKSTATION = "workstation"
INTERNAL_IPS = ["224.0.0.252", "169.254.255.255", "255.255.255.255", "239.255.255.250"]
TIME_SERVER = "time.windows.com"
PCAP_DOWNLOAD_LINK = "{}/api/v2/samples/{}/network.pcap?api_key={}"
HTML_REPORT_DOWNLOAD_LINK = "{}/api/v2/samples/{}/report.html?api_key={}"
SCREENSHOT_DOWNLOAD_LINK = "{}/api/v2/samples/{}/screenshot.png?api_key={}"

# ============================= CLASSES ===================================== #


class CiscoThreatGridManagerError(Exception):
    """
    General Exception for Cisco Threat Grid manager
    """

    pass


class CiscoThreatGridManager:
    """
    Cisco Threat Grid Manager
    """

    def __init__(self, api_root, api_key, use_ssl=False):
        self.session = requests.Session()
        self.session.verify = use_ssl
        self.api_root = api_root
        self.api_key = api_key

    def test_connectivity(self):
        """
        Test connectivity to Cisco Threat Grid
        :return:
        """
        url = f"{self.api_root}/api/v2/samples"
        response = self.session.get(
            url, params={"api_key": self.api_key, "user_only": True}
        )
        self.validate_response(response, "Unable to connect to Cisco Threat Grid")
        return True

    def analyze_sample(
        self,
        file_path,
        file_content,
        vm=None,
        network_exit=None,
        private=False,
        tags=[],
        playbook=None,
    ):
        """
        Upload a file for analysis
        :param file_path: {str} The sample file path
        :param file_content: {file} The sample file content
        :param vm: {str} The vm to run the analysis on.
            List of VMs:
            win7-x64: Windows 7 64bit
            win7-x64-2: Windows 7 64bit Profile 2
            win7-x64-jp: Windows 7 64bit Japanese (Not available on Threat Grid appliances)
            win7-x64-kr:Windows 7 64bit Korean (Only available on Threat Grid appliances licensed for this VM)
            win10: Windows 10 - Added as beta (Not available on Threat Grid appliances)
        :param network_exit: {str} Any outgoing network traffic that is
            generated during the analysis to appear to exit from the
             Network Exit Location. The current list of exit endpoints
             can be obtained by querying /api/v3/configuration/network-exits.
        :param private: {bool} if present, and set to any value but "false"
            the sample will be marked private
        :param tags: {list} A list of tags applied to this sample
        :param playbook: {str} Name of a playbook to apply to this sample run.
            List of Playbooks:
            none: Explicitly disables playbooks
            default: Default Playbook
            alt_tab_programs: Conduct Active Window Change
            open_word_embedded_object: Open Embedded Object in Word Document
            press_enter: Dialogue OK
            visit_site: Visit Website Using Internet Explorer
            close_file: Close Active Window
            run_dialog_box_ie: Click Run on Internet Explorer Download Dialog Box
            open_attachment_msg: Open Outlook Email Attachment
            run_dialog_box_dde: Accept Microsoft Office Dialog Boxes to Open Dynamic Data Exchange Content
        :return: {str} The id of the sample submission
        """
        files = {"sample": file_content}
        payload = {
            "vm": vm,
            "network_exit": network_exit,
            "private": private,
            "tags": ",".join(tags),
            "playbook": playbook,
            "api_key": self.api_key,
        }

        payload = {key: value for key, value in list(payload.items()) if value}

        response = self.session.post(
            f"{self.api_root}/api/v2/samples",
            data=payload,
            headers={},  # headers must be empty for multipart for data
            files=files,
        )

        self.validate_response(response, f"Unable to upload sample {file_path}")
        return response.json()["data"]["id"]

    def get_sample_state(self, sample_id):
        """
        Get the current state of a sample submission
        :param sample_id: {str} The sample submission id
        :return: {str} The state of the submission
        """
        response = self.session.get(
            f"{self.api_root}/api/v2/samples/{sample_id}/state",
            params={"api_key": self.api_key},
        )
        self.validate_response(response, f"Unable to get state of sample {sample_id}")
        return response.json()["data"]["state"]

    def is_sample_completed(self, sample_id):
        """
        Check whether a sample submission has completed or not
        :param sample_id: {str} The sample submission id
        :return: {bool} True if complete, False otherwise.
        """
        state = self.get_sample_state(sample_id)

        # If the sample submission has failed - gather the warnings
        # and raise a proper exception
        if state == FAILED_STATE:
            warnings = self.get_sample_warnings(sample_id)
            raise CiscoThreatGridManagerError(
                "Analysis on sample {} has failed:\n{}".format(
                    sample_id, "\n".join(warnings)
                )
            )

        return self.get_sample_state(sample_id) == SUCCESS_STATE

    def get_sample_warnings(self, sample_id):
        """
        Get the warnings of a sample submission
        :param sample_id: {str} The sample submission id
        :return: {list} List of the available warnings and errors of a
            submission.
        """
        response = self.session.get(
            f"{self.api_root}/api/v2/samples/{sample_id}/warnings.json",
            params={"api_key": self.api_key},
        )
        self.validate_response(response, f"Unable to get state of sample {sample_id}")

        warnings = []
        for warning in response.json()["data"]:
            warnings.append(warning["title"])

        return warnings

    def get_sample_report(self, sample_id):
        """
        Get the html report of a submission
        :param sample_id: {str} The sample submission id
        :return: {str} The content of the html report
        """
        response = self.session.get(
            HTML_REPORT_DOWNLOAD_LINK.format(self.api_root, sample_id, self.api_key)
        )
        self.validate_response(response, f"Unable to get report for sample {sample_id}")

        return response.content

    def get_sample_pcap(self, sample_id):
        """
        Get the network pcap of a sample submission
        :param sample_id: {str} The sample submission id
        :return: {stR} The content of the pcap file
        """
        response = self.session.get(
            PCAP_DOWNLOAD_LINK.format(self.api_root, sample_id, self.api_key)
        )
        self.validate_response(response, f"Unable to get report for sample {sample_id}")

        return response.content

    def get_sample_screenshot(self, sample_id):
        """
        Get the screenshot of a submission
        :param sample_id: {str} The sample submission id
        :return: {str} The content of the screenshot
        """
        response = self.session.get(
            SCREENSHOT_DOWNLOAD_LINK.format(self.api_root, sample_id, self.api_key)
        )
        self.validate_response(response, f"Unable to get report for sample {sample_id}")

        return response.content

    def get_sample_ioc(self, sample_id, ioc):
        """
        Get ioc details of s submission
        :param sample_id: {str} The sample submission id
        :param ioc: {str} The ioc identifier to get the details about
        :return: {dict} The ioc details
        """
        response = self.session.get(
            f"{self.api_root}/api/v2/samples/{sample_id}/analysis/iocs/{ioc}",
            params={"api_key": self.api_key},
        )
        self.validate_response(response, f"Unable to get ioc {ioc}")

        return response.json()["data"]

    def get_sample_threat(self, sample_id):
        """
        Get the threat info of a sample submission
        :param sample_id: {str} The sample submission id
        :return: {dict} The threat info
        """
        response = self.session.get(
            f"{self.api_root}/api/v2/samples/{sample_id}/threat",
            params={"api_key": self.api_key},
        )
        self.validate_response(response, f"Unable to get sample threat {sample_id}")

        threat = response.json()["data"]

        iocs = []
        # Replace the ioc identifiers with actual ioc details
        for ioc in threat["bis"]:
            iocs.append(self.get_sample_ioc(sample_id, ioc))

        threat["bis"] = iocs
        return threat

    def get_submission_state(
        self,
        query,
        term=None,
        limit=LIMIT,
        sort_by=SUBMITTED_AT,
        sort_order=DESCENDING_ORDER,
    ):
        """
        Get the state of the request from Cisco ThreatGrid.
        :param query: {str} Request query (File hash for example).
        :param term: {str} Entity type: domain/process/url/path.
        :param limit: {int} results limit.
        :return: {str} Status of the request.
        :param sort_order: {str} results will be sorted by this parameter. Default: submitted_at
        :param sort_by: {str} desc: Descending order - the default asc: Ascending order.
        """
        response = self.session.get(
            f"{self.api_root}/api/v2/search/submissions",
            params={
                "api_key": self.api_key,
                "q": query,
                "term": term,
                "limit": limit,
                "offset": 0,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )

        self.validate_response(response, "Unable to get submissions status")

        response_json = response.json().get("data", {}).get("items", [])

        if not response_json:
            return NO_RESULTS

        for submission in response_json:
            if submission.get("item", {}).get("state", "") == WAITING_STATE:
                return WAITING_STATE

        return TO_PROCESS

    def get_submissions(
        self,
        query,
        term=None,
        limit=LIMIT,
        sort_by=SUBMITTED_AT,
        sort_order=DESCENDING_ORDER,
    ):
        """
        Get submissions by term and query
        :param query: {str} The query to search by
        :param term: {str} The term of the search. Available terms:
            behaviour, domain, mutant, path, process, registry_key,
            sample, url.
        :param limit: {int} The amount of submissions to fetch in each page
        :param sort_order: {str} results will be sorted by this parameter. Default: submitted_at
        :param sort_by: {str} desc: Descending order - the default asc: Ascending order.
        :return: {list} The submissions (only successful ones)
        """

        response = self.session.get(
            f"{self.api_root}/api/v2/search/submissions",
            params={
                "api_key": self.api_key,
                "q": query,
                "term": term,
                "limit": limit,
                "offset": 0,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        self.validate_response(response, "Unable to get submissions")

        submissions = [
            submission
            for submission in response.json()["data"]["items"]
            if submission["item"]["state"] == SUCCESS_STATE
        ]

        return submissions

    def get_associated_network(self, filehash):
        """
        Get ips and domain that are associated to a given hash
        :param filehash: {str} The file hash
        :return: {dict} The ips and domains
        """
        submissions = self.get_submissions(filehash, "path")
        sample_ids = [submission["item"]["sample"] for submission in submissions]
        network_streams = []

        for sample_id in sample_ids:
            network_streams.extend(self.get_network_streams_by_id(sample_id))

        ips = set()
        domains = set()

        for stream in network_streams:
            dst_port = stream["dst_port"]
            current_ip = stream["dst"]
            current_ip_segmented = current_ip.split(".")
            two_octets = current_ip_segmented[0] + current_ip_segmented[1]

            # Extract ips
            if current_ip not in INTERNAL_IPS and two_octets != "17216":
                ips.add(current_ip)

            # Extract domains
            if dst_port == DNS_PORT and stream["protocol"] == DNS_PROTOCOL:
                option = stream["decoded"]

                for domain_data in list(option.values()):
                    current_domain = domain_data["query"]["query_data"]

                    if current_domain != DNS_WORKSTATION:
                        if current_domain != TIME_SERVER:
                            domains.add(current_domain)

        return {"ips": list(ips), "domains": list(domains)}

    def get_network_streams_by_id(self, sample_id):
        """
        Get network streams of a given sample
        :param sample_id: {str} The sample id
        :return: {list} The network streams
        """
        response = self.session.get(
            f"{self.api_root}/api/v2/samples/{sample_id}/analysis/network_streams",
            params={"api_key": self.api_key, "offset": 0},
        )
        self.validate_response(response, "Unable to get submissions")

        return list(response.json()["data"]["items"].values())

    @staticmethod
    def get_max_threat_score(submissions):
        """
        Get the max threat score of given submissions
        :param submissions: {list} List of submissions
        :return: {int} The max threat score
        """
        max_score = 0
        for submission in submissions:
            try:
                if submission["item"]["analysis"]["threat_score"] > max_score:
                    max_score = submission["item"]["analysis"]["threat_score"]
            except:
                # Threat score is not available in submission - skip it
                pass

        return max_score

    @staticmethod
    def create_threat_table(threat):
        """
        Create a human readable threat table
        :param threat: {dict} The threat info of a sample
        :return: {list} THe table
        """
        iocs = []
        for ioc in threat["bis"]:
            iocs.append(
                {
                    "Title": ioc["title"],
                    "Description": ioc["description"],
                    "Severity": ioc["severity"],
                    "Confidence": ioc["confidence"],
                }
            )

        return iocs

    @staticmethod
    def create_submissions_table(submissions):
        """
        Create a human readable submissions table
        :param threat: {list} The submissions
        :return: {list} The table
        """
        submissions_table = []
        for submission in submissions:
            submissions_table.append(
                {
                    "Name": submission["item"]["filename"],
                    "SHA256": submission["item"]["sha256"],
                    "MD5": submission["item"]["md5"],
                    "Score": submission["item"]["analysis"]["threat_score"],
                    "Indicators": len(submission["item"]["analysis"]["behaviors"]),
                    "Submitted": submission["item"]["submitted_at"],
                }
            )

        return submissions_table

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
            if response.json().get("error") and response.json()["error"].get("message"):
                raise CiscoThreatGridManagerError(
                    f"{error_msg}: {response.json()['error']['message']} {error.response.content}"
                )

            raise CiscoThreatGridManagerError(
                f"{error_msg}: {error} {error.response.content}"
            )
