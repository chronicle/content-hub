# ==============================================================================
# title           :VirusTotalManager.py
# description     :This Module contain all VirusTotal API functions.
# author          :zivh@siemplify.co
# date            :03-28-18
# python_version  :2.7
# libraries       :
# requirements    :
# product_version : v2.0
# ==============================================================================

from __future__ import annotations
import os
from datetime import datetime

# =====================================
#              IMPORTS                #
# =====================================
import requests
from TIPCommon import SiemplifySession

from .VirusTotalParser import VirusTotalParser


# =====================================
#             CONSTANTS               #
# =====================================
FILEHASH_TYPE = "file"
URL_TYPE = "url"
DUMMY_URL_FOR_TEST = "https://www.google.co.il"

HEADERS = {
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "gzip,  VirusTotal Public API v2.0",
}

API_ROOT = "https://www.virustotal.com/vtapi/v2/{0}/{1}"

QUEUED_FOR_ANALYSIS = -2

ENTITY_REPORT_KEY = "Report"
ENTITY_STATUS_KEY = "Status"
ENTITY_TASK_ID_KEY = "Task ID"

# Scan IP messages indicators.
NO_DATA_FOUND_MESSAGE = "No Data Found"
RESOURCE_COULD_NOT_BE_FOUND_MESSAGE = "resource could not be found"
INVALID_MESSAGE = "Invalid"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# =====================================
#              CLASSES                #
# =====================================
class VirusTotalManagerError(Exception):
    """
    General Exception for VirusTotal manager
    """

    pass


class VirusTotalLimitManagerError(Exception):
    """
    Limit Reached for VirusTotal manager
    """

    pass


class VirusTotalInvalidAPIKeyManagerError(Exception):
    """
    Invalid API key exception for VirusTotal manager
    """

    pass


class ScanStatus:
    DONE = "Done"
    MISSING = "Missing"
    QUEUED = "Queued"
    FAILED = "Failed"
    FORBIDDEN = "Forbidden"
    LIMIT_REACHED = "Limit"


class VirusTotalManager:
    def __init__(self, api_key, verify_ssl=False):
        self.api_key = api_key
        self.session = SiemplifySession(sensitive_data_arr=[self.api_key])
        self.session.verify = verify_ssl
        self.session.headers.update(HEADERS)
        self.virus_total_parser = VirusTotalParser()

    #
    def validate_response(self, response, error_msg="An error occurred"):
        """
        Retrieve a report on a given url/file
        :param response: {dict} response from api call,
        :param error_msg: {string} message if response is not valid
        :return: {bool}
        """
        try:
            response.raise_for_status()

            if response.status_code == 204:
                # API limit reached
                raise VirusTotalLimitManagerError("Request rate limit exceeded")

        except requests.HTTPError as error:
            if response.status_code == 403:
                # Forbidden - no permission to resource.
                # You don't have enough privileges to make the request. You may be doing a request without providing
                # an API key or you may be making a request to a Private API without having the appropriate privileges.
                raise VirusTotalInvalidAPIKeyManagerError(
                    self.session.encode_sensitive_data(
                        "Forbidden. You don't have enough privileges to make the request. You may be doing a request "
                        "without providing an API key or you may be making a request to a Private API without having "
                        "the appropriate privileges"
                    )
                )

            # Not a JSON - return content
            raise VirusTotalManagerError(
                self.session.encode_sensitive_data(
                    f"{error_msg}: {error} - {error.response.content}"
                )
            )

        return True

    #
    def test_connectivity(self):
        """
        Ping to server to be sure that connected
        :return: {bool}
        """
        return (
            True if self.get_url_or_file_report(DUMMY_URL_FOR_TEST, URL_TYPE) else False
        )

    #
    def scan_url(self, resource):
        """
        Retrieve a report on a given url/file
        :param resource: {string} The file of the url,
        :return: {dict}
        """
        params = {"apikey": self.api_key, "url": resource}
        report_url = API_ROOT.format("url", "scan")
        response = self.session.post(report_url, params=params)
        self.validate_response(response)
        return response.json().get("scan_id")

    #
    def rescan_file(self, resource):
        """
        Retrieve a report on a given url/file
        :param resource: {string} The file of the url,
        :return: scan id {string}
        """
        params = {"apikey": self.api_key, "resource": resource}
        report_url = API_ROOT.format("file", "rescan")
        response = self.session.post(report_url, params=params)
        self.validate_response(response)
        return self.virus_total_parser.get_scan_id(response.json())

    #
    def get_url_or_file_report(self, resource, resource_type):
        """
        Retrieve a report on a given url/file
        :param resource: {string} The file of the url,
        :param resource_type: {string} indicate weather resource is url or file, can be FILEHASH_TYPE or URL_TYPE
        :return: {dict}
        """
        params = {"apikey": self.api_key, "resource": resource, "allinfo": "true"}
        report_url = API_ROOT.format(resource_type, "report")
        response = self.session.post(report_url, params=params)
        self.validate_response(response)
        response_json = response.json()

        if resource_type == FILEHASH_TYPE:
            return (
                self.virus_total_parser.build_hash_object(response_json)
                if response_json.get("response_code", 0)
                else None
            )

        return (
            self.virus_total_parser.build_url_object(response_json)
            if response_json.get("response_code", 0)
            else None
        )

    #
    def get_domain_report(self, domain):
        """
        Retrieve a report on a given domain
        :param domain: domain name
        :return: {dict} report with domain information
        """
        parameters = {"apikey": self.api_key, "domain": domain}
        report_url = API_ROOT.format("domain", "report")
        response = self.session.get(report_url, params=parameters)
        self.validate_response(response)
        return self.virus_total_parser.build_domain_object(response.json())

    #
    def get_address_report(self, ip_address):
        """
        Retrieve a report on a given ip address
        :param ip_address: {string} xx.xx.xx.xx
        :return: {dict} report with ip address information
        """
        parameters = {"apikey": self.api_key, "ip": ip_address}
        report_url = API_ROOT.format("ip-address", "report")
        response = self.session.get(report_url, params=parameters)
        self.validate_response(response)
        return self.virus_total_parser.build_ip_address_object(response.json())

    #
    def get_hash_report(self, report):
        """
        Create Hash Object from report
        :param report: {dict} response from url call,
        :return: {Hash}
        """
        return self.virus_total_parser.build_hash_object(report)

    def get_url_report(self, report):
        """
        Create URL Object from report
        :param report: {dict} response from url call,
        :return: {URL}
        """
        return self.virus_total_parser.build_url_object(report)

    #
    def upload_file(self, file_path, file_byte_array=None):
        """
        The VirusTotal API allows you to send files.
        :param file_path: {string} file full path
        :param file_byte_array: {string}
        :return: {unicode} scan_id for query the report later.
        """
        # File size limit is 32MB
        file_name = os.path.basename(file_path)
        params = {"apikey": self.api_key}

        if file_byte_array:
            files = {"file": (file_name, file_byte_array)}
        else:
            files = {"file": (file_name, open(file_path, "rb"))}

        response = self.session.post(
            API_ROOT.format("file", "scan"), files=files, params=params
        )
        self.validate_response(response)
        return self.virus_total_parser.get_scan_id(response.json())

    #
    def get_report_by_scan_id(self, scan_id):
        """
        specify a scan_id to access a specific report
        query the report until the result shows up.
        :param scan_id: scan_id (sha256-timestamp as returned by the file upload API)
        :return: {dict} scan report
        """
        report = self.get_url_or_file_report(scan_id, FILEHASH_TYPE)
        # response_code: If the requested item is still queued for analysis it will be -2.
        # If the item was indeed present and it could be retrieved it will be 1.
        return None if report.response_code == QUEUED_FOR_ANALYSIS else report

    def get_comments(self, resource):
        """
        Get comments of a given resource
        :param resource: The resource to get the comments of
        :return: {list} The comments
        """
        params = {"apikey": self.api_key, "resource": resource}
        comments_url = API_ROOT.format("comments", "get")
        response = self.session.get(comments_url, params=params)
        self.validate_response(response)
        response_json = response.json()

        return (
            [
                self.virus_total_parser.build_comment_object(comment)
                for comment in response_json.get("comments", [])
            ]
            if response_json.get("response_code", 0)
            else []
        )

    # Not refactored
    def define_resource_status(self, resource, resource_type, rescan_after_days=None):
        """
        Check if entity need to be rescanned, if entity is missing in VT or if fetch an existing report
        :param resource: {string} entity identifier - resource to search in VT
        :param resource_type: {string} hash/url
        :param rescan_after_days: {int} parameter to determine how many days after to rescan
        :return: {dict} entity details
        """
        resource_handle = {
            resource: {
                ENTITY_REPORT_KEY: {},
                ENTITY_TASK_ID_KEY: None,
                ENTITY_STATUS_KEY: None,
            }
        }
        rescan_resources = []

        is_rescan = False
        current_time = datetime.now()

        # Get report
        report = self.get_url_or_file_report(resource, resource_type)

        if report:
            try:
                report_scan_date = datetime.strptime(report.scan_date, TIME_FORMAT)
                if rescan_after_days:
                    is_rescan = (
                        current_time - report_scan_date
                    ).days >= rescan_after_days

                if is_rescan or report.response_code == QUEUED_FOR_ANALYSIS:
                    # If the resource is being scanned right now, treat it as a rescan and wait for it to finish (both
                    # tasks will finish probably at the same time)
                    rescan_resources.append(resource)
                else:
                    resource_handle[resource][ENTITY_REPORT_KEY] = report.to_json()
                    resource_handle[resource][ENTITY_STATUS_KEY] = ScanStatus.DONE

            except Exception as e:
                resource_handle[resource][ENTITY_STATUS_KEY] = ScanStatus.MISSING
                raise VirusTotalManagerError(f"Unable to fetch entity:{resource}")
        else:
            # this resource is missing - not exist in Virus Total
            resource_handle[resource][ENTITY_STATUS_KEY] = ScanStatus.MISSING

        if (
            rescan_resources
            or resource_handle[resource][ENTITY_STATUS_KEY] == ScanStatus.MISSING
        ):
            scan_id = None

            if resource_type == FILEHASH_TYPE:
                # Rescan file.
                try:
                    scan_id = self.rescan_file(resource)
                except VirusTotalInvalidAPIKeyManagerError:
                    # If we got here without errors in previous API calls - meaning the API Key is valid, but
                    # as rescan is private API then an VirusTotalInvalidAPIKeyManagerError means that we are
                    # running with public API so we can't rescan (forbidden)
                    resource_handle[resource][ENTITY_STATUS_KEY] = ScanStatus.FORBIDDEN
                    return resource_handle
                except VirusTotalLimitManagerError:
                    resource_handle[resource][
                        ENTITY_STATUS_KEY
                    ] = ScanStatus.LIMIT_REACHED
                    raise

            if resource_type == URL_TYPE:
                # rescan url
                scan_id = self.scan_url(resource)
            if scan_id:
                resource_handle[resource][ENTITY_TASK_ID_KEY] = scan_id
                resource_handle[resource][ENTITY_STATUS_KEY] = ScanStatus.QUEUED
            else:
                # this resource is missing - not exist in Virus Total
                resource_handle[resource][ENTITY_STATUS_KEY] = ScanStatus.MISSING
        return resource_handle

    #
    def is_scan_report_ready(self, task_id, resource_type):
        """
        check if scan report is still queued or ready
        :param task_id: {string} scan id
        :param resource_type: {string} hash/url
        :return: {dict} resource report of none
        """
        report = self.get_url_or_file_report(task_id, resource_type)
        return None if report.response_code == QUEUED_FOR_ANALYSIS else report
