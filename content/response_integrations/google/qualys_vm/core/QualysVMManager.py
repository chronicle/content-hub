# ============================================================================#
# title           :QualysVMManager.py
# description     :This Module contain all QualysVM operations functionality
# author          :avital@siemplify.co
# date            :02-08-2018
# python_version  :2.7
# libreries       :requests, xmltodict
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
from urllib.parse import urljoin

import requests
import xmltodict

from .QualysVMExceptions import QualysVMManagerError
from .QualysVMParser import QualysVMParser
from .UtilsManager import filter_old_alerts
from .constants import ENDPOINTS

# ============================== CONSTS ===================================== #

COMPLETED = "finished"
ERROR_STATES = ["error", "canceled", "paused"]


# ============================= CLASSES ===================================== #


class QualysVMManager:
    """
    QualysVM Manager
    """

    def __init__(
        self,
        server_address,
        username,
        password,
        use_ssl=False,
        siemplify_logger=None,
        x_request_with_header=None,
    ):
        self.server_address = server_address
        self.session = requests.Session()
        self.session.verify = use_ssl
        self.session.auth = (username, password)
        headers = {}
        if x_request_with_header:
            headers["X-Requested-With"] = x_request_with_header
        self.session.headers.update(headers)
        self.parser = QualysVMParser()
        self.logger = siemplify_logger

    def test_connectivity(self):
        """
        Test connectivity to QualysVM
        :return: {bool} True if successful, exception otherwise.
        """
        self.list_reports()
        return True

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.server_address, ENDPOINTS[url_id].format(**kwargs))

    def get_vulnerabilities(
        self, existing_ids, include_ignored, include_disabled, status_filter
    ):
        """
        Get vulnerabilities.
        :param existing_ids: {list} The list of existing ids
        :param include_ignored: {bool} If enabled, will ingest ignored detections
        :param include_disabled: {bool} If enabled, will ingest disabled detections
        :param status_filter: {str} To filter detections by status
        :return: {list} The list of filtered Detection objects
        """
        request_url = self._get_full_url("get_detections")
        payload = {
            "action": "list",
            "truncation_limit": 0,
            "include_ignored": int(include_ignored),
            "include_disabled": int(include_disabled),
            "output_format": "CSV_NO_METADATA",
        }

        if status_filter:
            payload["status"] = status_filter

        response = self.session.post(request_url, data=payload)
        self.validate_response(response, "Unable to get vulnerabilities")

        detections = self.parser.build_detections_list(
            raw_data=response.content.decode("utf-8")
        )
        filtered_alerts = filter_old_alerts(
            logger=self.logger, alerts=detections, existing_ids=existing_ids
        )
        return filtered_alerts

    def list_asset_groups(
        self,
        ids=[],
        id_min=None,
        id_max=None,
        truncation_limit=None,
        network_i1ds=[],
        unit_id=None,
        user_id=None,
        title=None,
        show_attributes="ALL",
    ):
        """
        List asset groups
        :param ids: {str} Show only asset groups with certain IDs. Multiple IDs are comma
            separated.
        :param id_min: {str} Show only asset groups with certain IDs. Multiple IDs are comma
            separated.
        :param id_max: {str} Show only asset groups that have an ID less than or equal to the
            specified ID.
        :param truncation_limit: {str} Specify the maximum number of asset group records to output. By
            default this is set to 1000 records. If you specify truncation_limit=0, the
            output is not paginated and all records are returned in a single output
        :param network_i1ds: {str} Optional and valid only when the Networks feature is enabled in
            your account) Restrict the request to certain network IDs. Multiple IDs are
            comma separated.
        :param unit_id: {str} Show only asset groups that have a business unit ID equal to the
            specified ID.
        :param user_id: {str} Show only asset groups that have a user ID equal to the specified
            ID.
        :param title: {str} Show only the asset group that has a title equal to the specified
            string - this must be an exact match.
        :param show_attributes: {str} Show attributes for each asset group along with the ID. Your
        options are: None, All or a comma-separated list of attribute names.
        Attribute names:
            - TITLE
            - OWNER
            - NETWORK_IDS
            - LAST_UPDATE
            - IP_SET
            - APPLIANCE_LIST
            - DOMAIN_LIST
            - DNS_LIST
            - NETBIOS_LIST
            - EC2_ID_LIST
            - HOST_IDS
            - USER_IDS
            - UNIT_IDS
            - BUSINESS_IMPACT
            - CVSS
        :return: {list} The found groups
        """
        url = f"{self.server_address}/api/2.0/fo/asset/group/"
        params = {
            "action": "list",
            "ids": ",".join(ids),
            "id_min": id_min,
            "id_max": id_max,
            "truncation_limit": truncation_limit,
            "network_i1ds": ",".join(network_i1ds),
            "unit_id": unit_id,
            "user_id": user_id,
            "title": title,
            "show_attributes": show_attributes,
            "output_format": "xml",
        }

        params = {k: v for k, v in params.items() if v}
        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to list asset groups")

        groups = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("ASSET_GROUP_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("ASSET_GROUP_LIST", [])
        )

        if groups:
            found_groups = groups.get("ASSET_GROUP", [])

            if isinstance(found_groups, dict):
                # If there is only one group - xml will return it as single object
                return [found_groups]

            return found_groups

        return []

    def list_vulnerabilities(
        self,
        details="All",
        ids=[],
        id_min=None,
        id_max=None,
        is_patchable=None,
        last_modified_after=None,
        last_modified_before=None,
        last_modified_by_user_after=None,
        last_modified_by_user_before=None,
        last_modified_by_service_after=None,
        last_modified_by_service_before=None,
        published_after=None,
        published_before=None,
        discovery_method=None,
        discovery_auth_types=None,
        show_pci_reasons=None,
    ):
        """
        List vulnerabilities from Qualys' KnowledgeBase
        :param details: {str} Show the requested amount of information for each vulnerability
            in the XML output. A valid value is:
            - Basic (default)
            - All
            - None
            Basic includes basic elements plus CVSS Base and Temporal scores.
            All includes all vulnerability details, including the Basic
            details.
        :param ids: {str} Used to filter the XML output to include only vulnerabilities that
            have QID numbers matching the QID numbers you specify.
        :param id_min: {str} Used to filter the XML output to show only vulnerabilities that
            have a QID number greater than or equal to a QID number you specify.
        :param id_max: {str} Used to filter the XML output to show only vulnerabilities that
            have a QID number less than or equal to a QID number you specify.
        :param is_patchable: {str} Used to filter the XML output to show only vulnerabilities that
            are patchable or not patchable. A vulnerability is considered patchable when
            a patch exists for it. When 1 is specified, only vulnerabilities that are
            patchable will be included in the output. When 0 is specified, only vulnerabilities
            that are not patchable will be included in the output. When unspecified, patchable
            and unpatchable vulnerabilities will be included in the output.
        :param last_modified_after: {str} Used to filter the XML output to show only vulnerabilities last
            modified after a certain date and time. When specified vulnerabilities last
            modified by a user or by the service will be shown. The date/time is specified
            in YYYY-MM- DD[THH:MM:SSZ] format (UTC/GMT).
        :param last_modified_before: {str} Used to filter the XML output to show only vulnerabilities last
            modified before a certain date and time. When specified vulnerabilities last
            modified by a user or by the service will be shown. The date/time is specified
            in YYYY-MM- DD[THH:MM:SSZ] format (UTC/GMT).
        :param last_modified_by_user_after: {str} Used to filter the XML output to show only vulnerabilities last
            modified by a user after a certain date and time. The date/time is specified
            in YYYY-MM- DD[THH:MM:SSZ] format (UTC/GMT).
        :param last_modified_by_user_before: {str} Used to filter the XML output to show only vulnerabilities last
            modified by a user before a certain date and time. The date/time is specified
            in YYYY-MM- DD[THH:MM:SSZ] format (UTC/GMT).
        :param last_modified_by_service_after: {str} Used to filter the XML output to show only vulnerabilities last
            modified by the service after a certain date and time. The date/time is specified
            in YYYY-MM- DD[THH:MM:SSZ] format (UTC/GMT).
        :param last_modified_by_service_before: {str} Used to filter the XML output to show only vulnerabilities last
            modified by the service before a certain date and time. The date/time is specified
            in YYYY-MM- DD[THH:MM:SSZ] format (UTC/GMT).
        :param published_after: {str} Used to filter the XML output to show only vulnerabilities published
            after a certain date and time. The date/time is specified in YYYY-MM-DD[THH:MM:SSZ]
            format (UTC/GMT).
        :param published_before: {str} Used to filter the XML output to show only vulnerabilities published
            before a certain date and time. The date/time is specified in YYYY-MM-DD[THH:MM:SSZ]
            format (UTC/GMT).
        :param discovery_method: {str} Used to filter the XML output to show only vulnerabilities
            assigned a certain discovery method. A valid value is:
            - Remote
            - Authenticated,
            - RemoteOnly
            - AuthenticatedOnly
            - RemoteAndAuthenticated.
        :param discovery_auth_types: {str} Used to filter the XML output to show only vulnerabilities
            assigned a certain discovery method. A valid value is:
            - Remote
            - Authenticated,
            - RemoteOnly
            - AuthenticatedOnly
            - RemoteAndAuthenticated.
        :param show_pci_reasons: {str} Used to filter the XML output to show only vulnerabilities having
            one or more authentication types. A valid value is:
            - Windows
            - Oracle
            - Unix
            - SNMP.
            Multiple values are entered as a comma-separated list.
        :return: {list} The found vulnerabilities
        """
        url = f"{self.server_address}/api/2.0/fo/knowledge_base/vuln/"
        params = {
            "action": "list",
            "ids": ",".join(ids),
            "id_min": id_min,
            "id_max": id_max,
            "details": details,
            "is_patchable": is_patchable,
            "last_modified_after": last_modified_after,
            "last_modified_before": last_modified_before,
            "last_modified_by_user_after": last_modified_by_user_after,
            "last_modified_by_user_before": last_modified_by_user_before,
            "last_modified_by_service_after": last_modified_by_service_after,
            "last_modified_by_service_before": last_modified_by_service_before,
            "published_after": published_after,
            "published_before": published_before,
            "discovery_method": discovery_method,
            "discovery_auth_types": discovery_auth_types,
            "show_pci_reasons": show_pci_reasons,
        }

        params = {k: v for k, v in params.items() if v}
        response = self.session.post(url, params=params)
        self.validate_response(response, "Unable to list vulnerabilities")

        vulns = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("KNOWLEDGE_BASE_VULN_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("VULN_LIST", [])
        )

        if vulns:
            found_vulns = vulns.get("VULN", [])

            if isinstance(found_vulns, dict):
                # If there is only one vuln - xml will return it as single object
                return [found_vulns]

            return found_vulns

        return []

    def list_scans(self, state=None, scan_ref=None, launched_after_datetime=None):
        """
        List scans
        :param state: {str} Show only one or more scan states. By default, the
        scan list is not restricted to certain states. A valid value is:
        - Running
        - Paused
        - Canceled
        - Finished
        - Error
        - Queued (scan job is waiting to be distributed to scanner(s)), or Loading (scanner(s) are
          finished and scan results are being loaded onto the platform).
        :param scan_ref: {str} Show only a scan with a certain scan reference code.
        When unspecified, the scan list is not restricted to a certain scan.
        - For a vulnerability scan, the format is: scan/987659876.19876
        - For a compliance scan the format is: compliance/98765456.12345
        - For a SCAP scan the format is: qscap/987659999.22222
        :param launched_after_datetime: {str} ) Show only scans launched after a certain date and
        time (optional). The date/time is specified in YYYY-MMDD[THH:MM:SSZ]
        format (UTC/GMT), like "2007-07-01" or "2007-01-25T23:12:00Z".
        When launched_after_datetime and launched_before_datetime
        are unspecified, the service selects scans launched within the
        past 30 days.
        A date/time in the future returns an empty scans list.
        :return: {list} The found scans
        """
        url = self._get_full_url("scan")
        params = {
            "action": "list",
            "state": state,
            "scan_ref": scan_ref,
            "launched_after_datetime": launched_after_datetime,
        }

        params = {k: v for k, v in params.items() if v}
        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to list scans")

        scans = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("SCAN_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("SCAN_LIST", [])
        )

        if scans:
            found_scans = scans.get("SCAN", [])

            if isinstance(found_scans, dict):
                # If there is only one scan - xml will return it as single object
                return [found_scans]

            return found_scans

        return []

    def list_ips(self, ips=[]):
        """
        List ips
        :param ips :{list} Show only certain IP addresses/ranges. One or
        more IPs/ranges may be specified. Multiple entries are
        comma separated. A host IP range is specified with a
        hyphen (for example, 10.10.10.44-10.10.10.90).
        :return: {list} The found ips / ip ranges
        """
        url = f"{self.server_address}/api/2.0/fo/asset/ip/"
        params = {"action": "list", "ips": ",".join(ips) if ips else ""}

        params = {k: v for k, v in params.items() if v}
        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to list ips")

        ips = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("IP_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("IP_SET", [])
        )

        if ips:
            found_ips = ips.get("IP", [])
            found_ips.extend(ips.get("IP_RANGE", []))

            if isinstance(found_ips, dict):
                # If there is only one scan - xml will return it as single object
                return [found_ips]

            return found_ips

        return []

    def get_host_details(self, ip):
        """
        Get host details
        :param ip :{str} The ip of the host to get details about.
        :return: {dict} The host details
        """
        url = f"{self.server_address}/api/2.0/fo/asset/host/"
        params = {
            "action": "list",
            "details": "All",
            "ips": ip,
            "show_tags": 1,
            "host_metadata": "all",
            "show_cloud_tags": 1,
            "truncation_limit": 1000,
        }

        params = {k: v for k, v in params.items() if v}
        response = self.session.get(url, params=params)
        self.validate_response(response, f"Unable to host {ip} details")

        hosts = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("HOST_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("HOST_LIST", [])
        )

        if hosts:
            return self.parser.build_host_object(hosts.get("HOST"))

        raise QualysVMManagerError(f"Host {ip} was not found")

    def get_hostname_details(self, hostname):
        """
        Get hostname details
        :param hostname :{str} The hostname of the host to get details about.
        :return: {dict} The hostname details
        """
        url = f"{self.server_address}/api/2.0/fo/asset/host/"
        filtered_hosts = []
        params = {
            "action": "list",
            "details": "All/AGs",
            "show_tags": 1,
            "host_metadata": "all",
            "show_cloud_tags": 1,
            "truncation_limit": 1000,
        }

        params = {k: v for k, v in params.items() if v}
        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to get hostname details")

        hosts = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("HOST_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("HOST_LIST", [])
        )

        warning = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("HOST_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("WARNING", [])
        )

        hosts = self.parser.filter_hostname(hosts, hostname)
        if hosts:
            if type(hosts) is list:
                filtered_hosts = filtered_hosts + hosts
            else:
                filtered_hosts.append(hosts)

        if type(warning) is not list:
            need_to_paginate = True

            error_code = warning.get("CODE")
            if error_code == "1980":
                while need_to_paginate:
                    url = warning.get("URL")
                    response = self.session.get(url)
                    self.validate_response(response, "Unable to get hostname details")

                    hosts = (
                        xmltodict.parse(response.content, dict_constructor=dict)
                        .get("HOST_LIST_OUTPUT", {})
                        .get("RESPONSE", {})
                        .get("HOST_LIST", [])
                    )

                    warning = (
                        xmltodict.parse(response.content, dict_constructor=dict)
                        .get("HOST_LIST_OUTPUT", {})
                        .get("RESPONSE", {})
                        .get("WARNING", [])
                    )
                    if type(warning) is list:
                        need_to_paginate = False

                    hosts = self.parser.filter_hostname(hosts, hostname)
                    if hosts:
                        if type(hosts) is list:
                            filtered_hosts = filtered_hosts + hosts
                        else:
                            filtered_hosts.append(hosts)

        if filtered_hosts:
            return self.parser.build_host_object(filtered_hosts)

        raise QualysVMManagerError("Hostname was not found")

    def find_hostname_ip(self, hostname):
        """
        Get hostname ip address
        :param hostname :{str} The hostname of the host to get IP address.
        :return: {str} IP Address
        """
        request_url = self._get_full_url("find_hostname_ip")
        payload = {"action": "list", "details": "Basic", "truncation_limit": 1000}

        response = self.session.post(request_url, data=payload)
        self.validate_response(response, "Unable to get hosts")
        hosts = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("HOST_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("HOST_LIST", [])
        )

        return self.parser.get_ip_for_hostname(raw_data=hosts, hostname=hostname)

    def get_detection_quid(
        self, ip_address, status, severities, include_ignored, include_disabled
    ):
        """
        Get detection QUID for an IP Address
        :param include_ignored: {bool} If the inluded detections should be ignored
        :param include_disabled: {bool} If the disabled detections should be ignored
        :param status :{str} IP Address.
        :param severities :{str} Severities to filter
        :param ip_address :{str} IP Address to use in the to get QUID for.
        :param ip_address :{str} IP Address to use in the to get QUID for.
        :return :{list} List of detection QUIDs
        """

        request_url = self._get_full_url("get_detections")
        payload = {
            "action": "list",
            "truncation_limit": 0,
            "include_ignored": int(include_ignored),
            "include_disabled": int(include_disabled),
            "severities": severities,
            "ips": ip_address,
        }

        if status:
            payload["status"] = status

        response = self.session.post(request_url, data=payload)
        self.validate_response(response, "Unable to get vulnerabilities")

        detections = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("HOST_LIST_VM_DETECTION_OUTPUT", {})
            .get("RESPONSE", {})
            .get("HOST_LIST", [])
        )

        return self.parser.get_detection_quids(raw_data=detections)

    def get_detection_details(self, detection_quids):
        """
        Get detection details for given QUIDs
        :param detection_quids: {str} Detection Quids
        :return :{list} List of EndpointDetection objects
        """
        request_url = self._get_full_url("get_detection_details")
        payload = {"action": "list", "ids": detection_quids, "details": "All"}

        response = self.session.post(request_url, data=payload)
        self.validate_response(response, "Unable to get vulnerabilities")

        detection_details = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("KNOWLEDGE_BASE_VULN_LIST_OUTPUT", {})
            .get("RESPONSE", {})
        )

        return self.parser.build_endpointdetection_object(raw_data=detection_details)

    def is_scan_completed(self, scan_ref):
        """
        Check whether a scan is completed
        :param scan_ref: {str} The scan reference
        :return: {bool} True if completed, False otherwise.
        """
        scan_info = self.list_scans(scan_ref=scan_ref)

        if not scan_info:
            raise QualysVMManagerError(f"Scan {scan_ref} was not found")

        scan_info = scan_info[0]  # list_scans returns a list

        return scan_info["STATUS"]["STATE"].lower() == COMPLETED

    def is_scan_in_error_state(self, scan_ref):
        """
        Check whether a scan is in error state (error, canceled or paused)
        :param scan_ref: {str} The scan reference
        :return: {bool} True if error state, False otherwise.
        """
        scan_info = self.list_scans(scan_ref=scan_ref)

        if not scan_info:
            raise QualysVMManagerError(f"Scan {scan_ref} was not found")

        scan_info = scan_info[0]  # list_scans returns a list

        return scan_info["STATUS"]["STATE"].lower() in ERROR_STATES

    def list_reports(
        self, report_id=None, state=None, user_login=None, expires_before_datetime=None
    ):
        """
        List reports
        :param state: {str} Specify reports with a certain state. Valid values:
            - Running
            - Finished
            - Canceled
            - Errors
        :param report_id: {str} Specifies a report ID of a report that is saved
            in the Report Share storage space
        :param user_login: {str} Specify a user login ID to get reports launched by the specified
            user login ID
        :param expires_before_datetime: {str} Specify the date and time to get only reports that expire before
            it. use YYYY-MM-DD[THH:MM:SSZ] format (UTC/GMT), like "2007-07-01" or "2007-01-25T23:12:00Z"
        :return: {list} The found reports
        """
        url = self._get_full_url("report")
        params = {
            "action": "list",
            "state": state,
            "id": report_id,
            "user_login": user_login,
            "expires_before_datetime": expires_before_datetime,
        }

        params = {k: v for k, v in params.items() if v}
        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to list reports")

        reports = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("REPORT_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("REPORT_LIST", [])
        )

        if reports:
            found_reports = reports.get("REPORT", [])

            if isinstance(found_reports, dict):
                # If there is only one report - xml will return it as single object
                return [found_reports]

            return found_reports

        return []

    def get_template_id_by_name(self, template_name):
        """
        Get template id by name
        :param template_name: {str} The template name
        :return: {str} The matching template id
        """
        url = f"{self.server_address}/msp/report_template_list.php"
        response = self.session.get(url)
        self.validate_response(response, "Unable to list templates")

        templates = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("REPORT_TEMPLATE_LIST", {})
            .get("REPORT_TEMPLATE", [])
        )

        for template in templates:
            if template["TITLE"] == template_name:
                return template["ID"]

        raise QualysVMManagerError(f"Template {template_name} was not found.")

    def add_ip(self, ip, vm_ip=True, pc_ip=False, comment="Added by Siemplify"):
        """
        Add an ip
        :param comment: {str} The comment to add to the ip
        :param pc_ip: {bool} Whether the ip is enabled for PC scans
        :param vm_ip: {bool} Whether the ip is enabled for VM scans
        :param ip: {str} The ip to add
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.server_address}/api/2.0/fo/asset/ip/"
        params = {
            "action": "add",
            "ips": ip,
            "enable_vm": 1 if vm_ip else 0,
            "enable_pc": 1 if pc_ip else 0,
            "comment": comment,
        }

        response = self.session.post(url, params=params)
        self.validate_response(response, f"Unable to add ip {ip}")

        return xmltodict.parse(response.content, dict_constructor=dict)

    def get_report(self, report_id):
        """
        Get report info by id
        :param report_id: {str} The report id
        :return: {dict} The report info
        """
        url = self._get_full_url("report")
        params = {"action": "list", "id": report_id}
        response = self.session.get(url, params=params)
        self.validate_response(response, f"Unable to get report {report_id}")

        report = (
            xmltodict.parse(response.content, dict_constructor=dict)
            .get("REPORT_LIST_OUTPUT", {})
            .get("RESPONSE", {})
            .get("REPORT_LIST", {})
            .get("REPORT")
        )

        if report:
            return report

        raise QualysVMManagerError(f"Report {report_id} doesn't exist.")

    def fetch_report(self, report_id):
        """
        Download a report
        :param report_id: {str} The id of the report to download
        :return: {str} The content of the report file
        """
        report = self.get_report(report_id)

        url = self._get_full_url("report")
        params = {"action": "fetch", "id": report_id}
        response = self.session.get(url, params=params)
        self.validate_response(response, f"Unable to fetch report {report_id}")

        return {
            "name": f"{report['TITLE']}.{report['OUTPUT_FORMAT']}",
            "content": response.content,
        }

    def launch_vm_scan(
        self,
        scan_title,
        priority=0,
        option_id=None,
        option_title=None,
        ip=None,
        asset_group_ids=None,
        asset_groups=None,
        exclude_ip_per_scan=None,
        iscanner_name="External",
        scanners_in_ag=None,
        target_from="assets",
        tag_include_selector="any",
        tag_exclude_selector="any",
        tag_set_by="id",
        tag_set_include=None,
        tag_set_exclude=None,
        use_ip_nt_range_tags=0,
        ip_network_id=0,
        runtime_http_header=None,
    ):
        """
        Launch a vm scan
        :param scan_title: {str} The scan title. This can be a maximum of 2000 characters (ascii).
        :param priority: {str}  Specify a value of 0 - 9 to set a
            processing priority level for the scan. When not specified, a
            value of 0 (no priority) is used. Valid values are:
            0 = No Priority (the default)
            1 = Emergency
            2 = Ultimate
            3 = Critical
            4 = Major
            5 = High
            6 = Standard
            7 = Medium
            8 = Minor
            9 = Low
        :param option_id: {str} The ID of the compliance option profile to be used. One of these
            parameters must be specified in a request: option_title or option_id. These
            are mutually exclusive and cannot be specified in the same request.
        :param option_title: {str} The title of the compliance option profile to be used. One of
            these parameters must be specified in a request: option_title or option_id.
            These are mutually exclusive and cannot be specified in the same request.
        :param ip: {str} The IP addresses to be scanned. You may enter individual IP addresses
            and/or ranges. Multiple entries are comma separated. One of these parameters
            is required: ip, asset_groups or asset_group_ids.
        :param asset_group_ids: {str} The IDs of asset groups containing the hosts to be scanned. Multiple
            IDs are comma separated. One of these parameters is required: ip, asset_groups
            or asset_group_ids.
        :param asset_groups: {str} The titles of asset groups containing the hosts to be scanned.
            Multiple titles are comma separated. One of these parameters is required:
            ip, asset_groups or asset_group_ids.
        :param exclude_ip_per_scan: {str} The IP addresses to be excluded from the scan when the scan target
            is specified as IP addresses (not asset tags). You may enter individual IP
            addresses and/or ranges. Multiple entries are comma separated.
        :param iscanner_name: {str} The friendly names of the scanner appliances to
            be used or "External" for external scanners. Multiple
            entries are comma separated. For an Express Lite user,
            Internal Scanning must be enabled in the user's account.
        :param scanners_in_ag: {str} Specify 1 to distribute the scan to the target asset groups' scanner
            appliances. Appliances in each asset group are tasked with scanning the IPs
            in the group. By default up to 5 appliances per group will be used and this
            can be configured for your account (please contact your Account Manager or
            Support). For an Express Lite user, Internal Scanning must be enabled in the
            user's account. Valid values: 0, 1.
        :param target_from: {str} Specify "assets" (the default) when your scan target will include
            IP addresses/ranges and/or asset groups. Specify "tags" when your scan target
            will include asset tags.
        :param tag_include_selector: {str} Select "any" (the default) to include hosts that match at least
            one of the selected tags. Select "all" to include hosts that match all of
            the selected tags.
        :param tag_exclude_selector: {str} Select "any" (the default) to exclude hosts that match at least
            one of the selected tags. Select "any" to exclude hosts that match all of
            the selected tags.
        :param tag_set_by: {str} Specify "id" (the default) to select a tag set by providing tag
            IDs. Specify "name" to select a tag set by providing tag names.
        :param tag_set_include: {str} Specify a tag set to include. Hosts that match these tags will
            be included. You identify the tag set by providing tag name or IDs. Multiple
            entries are comma separated.
        :param tag_set_exclude: {str} Specify a tag set to exclude. Hosts that match these tags will
            be excluded. You identify the tag set by providing tag name or IDs. Multiple
            entries are comma separated.
        :param use_ip_nt_range_tags: {str} Specify "0" (the default) to select from all tags (tags with any
            tag rule). Specify "1" to scan all IP addresses defined in tags. When this
            is specified, only tags with the dynamic IP address rule called "IP address
            in Network Range(s)" can be selected.
        :param ip_network_id: {str} The ID of a network used to filter the IPs/ranges specified in
            the "ip" parameter. Set to a custom network ID (note this does not filter IPs/ranges
            specified in "asset_groups" or "asset_group_ids"). Or set to "0" (the default)
            for the Global Default Network - this is used to scan hosts outside of your
            custom networks.
        :param runtime_http_header: {str} Set a custom value in order to drop defenses (such as logging,
            IPs, etc) when an authorized scan is being run. The value you enter will be
            used in the "Qualys-Scan:" header that will be set for many CGI and web application
            fingerprinting checks. Some discovery and web server fingerprinting checks
            will not use this header.
        :return: {str} The scan ref
        """
        url = self._get_full_url("scan")
        data = {
            "scan_title": scan_title,
            "priority": priority,
            "option_id": option_id,
            "option_title": option_title,
            "iscanner_name": iscanner_name,
            "scanners_in_ag": scanners_in_ag,
            "target_from": target_from,
            "runtime_http_header": runtime_http_header,
        }

        if target_from == "tags":
            data.update(
                {
                    "tag_include_selector": tag_include_selector,
                    "tag_exclude_selector": tag_exclude_selector,
                    "tag_set_by": tag_set_by,
                    "tag_set_include": tag_set_include,
                    "tag_set_exclude": tag_set_exclude,
                    "use_ip_nt_range_tags": use_ip_nt_range_tags,
                }
            )

        elif target_from == "assets":
            data.update(
                {
                    "ip": ip,
                    "asset_group_ids": asset_group_ids,
                    "asset_groups": asset_groups,
                    "exclude_ip_per_scan": exclude_ip_per_scan,
                    "ip_network_id": ip_network_id,
                }
            )

            data = {k: v for k, v in data.items() if v}
        response = self.session.post(url, params={"action": "launch"}, data=data)
        self.validate_response(response, "Unable to launch vm scan")

        try:
            items = (
                xmltodict.parse(response.content, dict_constructor=dict)
                .get("SIMPLE_RETURN", {})
                .get("RESPONSE", {})
                .get("ITEM_LIST", {})
                .get("ITEM", [])
            )

            if items:
                return items[1].get("VALUE")
        except Exception as e:  # pylint: disable=broad-exception-caught
            parsed_content = xmltodict.parse(response.content, dict_constructor=dict)
            text = (
                parsed_content.get("SIMPLE_RETURN", {}).get("RESPONSE", {}).get("TEXT")
            )
            if text:
                raise QualysVMManagerError(f"Unable to perform scan: {text}") from e

        raise QualysVMManagerError(f"Unable to perform scan: {response.content}")

    def get_vm_scan_results(self, scan_ref):
        url = self._get_full_url("scan")
        data = {
            "scan_ref": scan_ref,
            "mode": "extended",
            "output_format": "json_extended",
        }

        response = self.session.post(url, params={"action": "fetch"}, data=data)
        self.validate_response(response, "Unable to get vm scan results")

        try:
            return response.json()
        except Exception:
            # Response is not json - an error occurred
            try:
                results = xmltodict.parse(response.content, dict_constructor=dict)
            except Exception:
                # Response is not xml as well - critical exception - raise
                raise QualysVMManagerError(
                    f"Unable to get vm scan {scan_ref} results. Response: {response.content}"
                )

            # Check if scan is complete
            if results["SIMPLE_RETURN"]["RESPONSE"]["CODE"] == "15003":
                raise QualysVMManagerError(
                    f"Vm scan {scan_ref} doesn't exist or is not completed."
                )

            raise QualysVMManagerError(
                f"Unable to get vm scan {scan_ref} results. Error: {results['SIMPLE_RETURN']['RESPONSE']['TEXT']}"
            )

    def get_pc_scan_results(self, scan_ref):
        url = f"{self.server_address}/api/2.0/fo/scan/compliance/"
        data = {"scan_ref": scan_ref}

        response = self.session.post(url, params={"action": "fetch"}, data=data)
        self.validate_response(response, "Unable to get pc scan results")

        return xmltodict.parse(response.content, dict_constructor=dict)

    def launch_pc_scan(
        self,
        scan_title,
        priority=0,
        option_id=None,
        option_title=None,
        ip=None,
        asset_group_ids=None,
        asset_groups=None,
        exclude_ip_per_scan=None,
        iscanner_name="External",
        scanners_in_ag=None,
        target_from="assets",
        tag_include_selector="any",
        tag_exclude_selector="any",
        tag_set_by="id",
        tag_set_include=None,
        tag_set_exclude=None,
        use_ip_nt_range_tags=0,
        ip_network_id=0,
        runtime_http_header=None,
    ):
        """
        Launch a pc scan
        :param scan_title: {str} The scan title. This can be a maximum of 2000 characters (ascii).
        :param priority: {str}  Specify a value of 0 - 9 to set a
            processing priority level for the scan. When not specified, a
            value of 0 (no priority) is used. Valid values are:
            0 = No Priority (the default)
            1 = Emergency
            2 = Ultimate
            3 = Critical
            4 = Major
            5 = High
            6 = Standard
            7 = Medium
            8 = Minor
            9 = Low
        :param option_id: {str} The ID of the compliance option profile to be used. One of these
            parameters must be specified in a request: option_title or option_id. These
            are mutually exclusive and cannot be specified in the same request.
        :param option_title: {str} The title of the compliance option profile to be used. One of
            these parameters must be specified in a request: option_title or option_id.
            These are mutually exclusive and cannot be specified in the same request.
        :param ip: {str} The IP addresses to be scanned. You may enter individual IP addresses
            and/or ranges. Multiple entries are comma separated. One of these parameters
            is required: ip, asset_groups or asset_group_ids.
        :param asset_group_ids: {str} The IDs of asset groups containing the hosts to be scanned. Multiple
            IDs are comma separated. One of these parameters is required: ip, asset_groups
            or asset_group_ids.
        :param asset_groups: {str} The titles of asset groups containing the hosts to be scanned.
            Multiple titles are comma separated. One of these parameters is required:
            ip, asset_groups or asset_group_ids.
        :param exclude_ip_per_scan: {str} The IP addresses to be excluded from the scan when the scan target
            is specified as IP addresses (not asset tags). You may enter individual IP
            addresses and/or ranges. Multiple entries are comma separated.
        :param iscanner_name: {str} The friendly names of the scanner appliances to
            be used or "External" for external scanners. Multiple
            entries are comma separated. For an Express Lite user,
            Internal Scanning must be enabled in the user's account.
        :param scanners_in_ag: {str} Specify 1 to distribute the scan to the target asset groups' scanner
            appliances. Appliances in each asset group are tasked with scanning the IPs
            in the group. By default up to 5 appliances per group will be used and this
            can be configured for your account (please contact your Account Manager or
            Support). For an Express Lite user, Internal Scanning must be enabled in the
            user's account. Valid values: 0, 1.
        :param target_from: {str} Specify "assets" (the default) when your scan target will include
            IP addresses/ranges and/or asset groups. Specify "tags" when your scan target
            will include asset tags.
        :param tag_include_selector: {str} Select "any" (the default) to include hosts that match at least
            one of the selected tags. Select "all" to include hosts that match all of
            the selected tags.
        :param tag_exclude_selector: {str} Select "any" (the default) to exclude hosts that match at least
            one of the selected tags. Select "any" to exclude hosts that match all of
            the selected tags.
        :param tag_set_by: {str} Specify "id" (the default) to select a tag set by providing tag
            IDs. Specify "name" to select a tag set by providing tag names.
        :param tag_set_include: {str} Specify a tag set to include. Hosts that match these tags will
            be included. You identify the tag set by providing tag name or IDs. Multiple
            entries are comma separated.
        :param tag_set_exclude: {str} Specify a tag set to exclude. Hosts that match these tags will
            be excluded. You identify the tag set by providing tag name or IDs. Multiple
            entries are comma separated.
        :param use_ip_nt_range_tags: {str} Specify "0" (the default) to select from all tags (tags with any
            tag rule). Specify "1" to scan all IP addresses defined in tags. When this
            is specified, only tags with the dynamic IP address rule called "IP address
            in Network Range(s)" can be selected.
        :param ip_network_id: {str} The ID of a network used to filter the IPs/ranges specified in
            the "ip" parameter. Set to a custom network ID (note this does not filter IPs/ranges
            specified in "asset_groups" or "asset_group_ids"). Or set to "0" (the default)
            for the Global Default Network - this is used to scan hosts outside of your
            custom networks.
        :param runtime_http_header: {str} Set a custom value in order to drop defenses (such as logging,
            IPs, etc) when an authorized scan is being run. The value you enter will be
            used in the "Qualys-Scan:" header that will be set for many CGI and web application
            fingerprinting checks. Some discovery and web server fingerprinting checks
            will not use this header.
        :return: {str} The scan ref
        """
        url = f"{self.server_address}/api/2.0/fo/scan/compliance"
        data = {
            "scan_title": scan_title,
            "priority": priority,
            "option_id": option_id,
            "option_title": option_title,
            "iscanner_name": iscanner_name,
            "scanners_in_ag": scanners_in_ag,
            "target_from": target_from,
            "runtime_http_header": runtime_http_header,
        }

        if target_from == "tags":
            data.update(
                {
                    "tag_include_selector": tag_include_selector,
                    "tag_exclude_selector": tag_exclude_selector,
                    "tag_set_by": tag_set_by,
                    "tag_set_include": tag_set_include,
                    "tag_set_exclude": tag_set_exclude,
                    "use_ip_nt_range_tags": use_ip_nt_range_tags,
                }
            )

        elif target_from == "assets":
            data.update(
                {
                    "ip": ip,
                    "asset_group_ids": asset_group_ids,
                    "asset_groups": asset_groups,
                    "exclude_ip_per_scan": exclude_ip_per_scan,
                    "ip_network_id": ip_network_id,
                }
            )

            data = {k: v for k, v in data.items() if v}
        response = self.session.post(url, params={"action": "launch"}, data=data)
        self.validate_response(response, "Unable to launch pc scan")

        try:
            items = (
                xmltodict.parse(response.content, dict_constructor=dict)
                .get("SIMPLE_RETURN", {})
                .get("RESPONSE", {})
                .get("ITEM_LIST", {})
                .get("ITEM", [])
            )

            if items:
                return items[1].get("VALUE")
        except Exception as e:  # pylint: disable=broad-exception-caught
            parsed_content = xmltodict.parse(response.content, dict_constructor=dict)
            text = (
                parsed_content.get("SIMPLE_RETURN", {}).get("RESPONSE", {}).get("TEXT")
            )
            if text:
                raise QualysVMManagerError(f"Unable to perform scan: {text}") from e

        raise QualysVMManagerError(f"Unable to perform scan: {response.content}")

    def launch_patch_report(
        self,
        report_title,
        template_id,
        output_format="pdf",
        hide_header=False,
        ips=None,
        asset_group_ids=None,
        recipient_group_id=None,
        pdf_password=None,
        recipient_group=None,
    ):
        """
        Launch a patch report
        :param report_title: {str} A user-defined report title. The title may have a maximum of 128
            characters. For a PCI compliance report, the report title is provided by Qualys
            and cannot be changed.
        :param template_id: {str} The template ID of the report you want to launch.
        :param output_format: {str} One output format may be specified. When output_format=pdf is specified,
            the Secure PDF Distribution may be used. Valid values:
            - pdf
            - online
            - csv
        :param hide_header: {str} (Valid for CSV format report only). Specify hide_header=1 to omit
            the header information from the report. By default this information is included.
        :param ips: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple IPs/ranges are comma separated. When
            specified, hosts defined in the report template are not included in the report.
            See also "Using Asset Tags."
        :param asset_group_ids: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple asset group IDs are comma separated.
            When specified, hosts defined in the report template are not included in the
            report. Looking for asset group IDs? Use the asset_group_list.php function
            (see the API v1 User Guide).
        :param recipient_group_id: {str} Specify users who will receive the email notification when the report
            is complete (i.e. supply a distribution group ID). Where do I find this ID?
            Log in to your Qualys account, go to Users > Distribution Groups and select
            Info for a group in the list.
        :param pdf_password: {str} (Optional; Required for secure PDF distribution) The password
            to be used for encryption. Requirements: - the password must have a minimum
            of 8 characters (ascii), and a maximum of 32 characters - the password must
            contain alpha and numeric characters - the password cannot match the password
            for the user's Qualys account. - the password must follow the password security
            guidelines defined for your subscription (log in and go to Subscription Setup > Security
            Options).
        :param recipient_group: {str} (Optional; Optional for secure PDF distribution) The report recipients
            in the form of one or more distribution groups, as defined using the Qualys
            UI. Multiple distribution groups are comma separated. A maximum of 50 distribution
            groups may be entered.
        :return: {str} The report id
        """
        url = self._get_full_url("report")
        data = {
            "action": "launch",
            "report_type": "Patch",
            "hide_header": hide_header,
            "report_title": report_title,
            "template_id": template_id,
            "output_format": output_format,
            "recipient_group_id": recipient_group_id,
            "pdf_password": pdf_password,
            "recipient_group": recipient_group,
            "ips": ips,
            "asset_group_ids": asset_group_ids,
        }

        data = {k: v for k, v in data.items() if v}
        response = self.session.post(url, data=data)

        self.validate_response(response, "Unable to launch patch report")

        try:
            return (
                xmltodict.parse(response.content, dict_constructor=dict)
                .get("SIMPLE_RETURN", {})
                .get("RESPONSE", {})
                .get("ITEM_LIST", {})
                .get("ITEM", {})
                .get("VALUE")
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            parsed_content = xmltodict.parse(response.content, dict_constructor=dict)
            text = (
                parsed_content.get("SIMPLE_RETURN", {}).get("RESPONSE", {}).get("TEXT")
            )
            if text:
                raise QualysVMManagerError(
                    f"Unable to launch patch report: {text}"
                ) from e

        raise QualysVMManagerError(f"Unable to launch patch report: {response.content}")

    def launch_remediation_report(
        self,
        report_title,
        template_id,
        output_format="pdf",
        hide_header=False,
        ips=None,
        asset_group_ids=None,
        recipient_group_id=None,
        pdf_password=None,
        recipient_group=None,
        assignee_type="User",
    ):
        """
        Launch a remediation report
        :param report_title: {str} A user-defined report title. The title may have a maximum of 128
            characters. For a PCI compliance report, the report title is provided by Qualys
            and cannot be changed.
        :param template_id: {str} The template ID of the report you want to launch.
        :param output_format: {str} One output format may be specified. When output_format=pdf is specified,
            the Secure PDF Distribution may be used. Valid values:
            - pdf
            - mht
            - csv
            - html
        :param hide_header: {str} (Valid for CSV format report only). Specify hide_header=1 to omit
            the header information from the report. By default this information is included.
        :param ips: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple IPs/ranges are comma separated. When
            specified, hosts defined in the report template are not included in the report.
            See also "Using Asset Tags."
        :param asset_group_ids: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple asset group IDs are comma separated.
            When specified, hosts defined in the report template are not included in the
            report. Looking for asset group IDs? Use the asset_group_list.php function
            (see the API v1 User Guide).
        :param recipient_group_id: {str} Specify users who will receive the email notification when the report
            is complete (i.e. supply a distribution group ID). Where do I find this ID?
            Log in to your Qualys account, go to Users > Distribution Groups and select
            Info for a group in the list.
        :param pdf_password: {str} (Optional; Required for secure PDF distribution) The password
            to be used for encryption. Requirements: - the password must have a minimum
            of 8 characters (ascii), and a maximum of 32 characters - the password must
            contain alpha and numeric characters - the password cannot match the password
            for the user's Qualys account. - the password must follow the password security
            guidelines defined for your subscription (log in and go to Subscription Setup > Security
            Options).
        :param recipient_group: {str} (Optional; Optional for secure PDF distribution) The report recipients
            in the form of one or more distribution groups, as defined using the Qualys
            UI. Multiple distribution groups are comma separated. A maximum of 50 distribution
            groups may be entered.
        :param assignee_type: {str} Specifies whether the report will include
            tickets assigned to the current user (User is set by default),
            or all tickets in the user account. By default tickets assigned
            to the current user are included.
        :return: {str} The report id
        """
        url = self._get_full_url("report")
        data = {
            "action": "launch",
            "report_type": "Remediation",
            "hide_header": hide_header,
            "report_title": report_title,
            "template_id": template_id,
            "output_format": output_format,
            "recipient_group_id": recipient_group_id,
            "pdf_password": pdf_password,
            "recipient_group": recipient_group,
            "assignee_type": assignee_type,
            "ips": ips,
            "asset_group_ids": asset_group_ids,
        }

        data = {k: v for k, v in data.items() if v}
        response = self.session.post(url, data=data)

        self.validate_response(response, "Unable to launch patch report")

        try:
            return (
                xmltodict.parse(response.content, dict_constructor=dict)
                .get("SIMPLE_RETURN", {})
                .get("RESPONSE", {})
                .get("ITEM_LIST", {})
                .get("ITEM", {})
                .get("VALUE")
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            parsed_content = xmltodict.parse(response.content, dict_constructor=dict)
            text = (
                parsed_content.get("SIMPLE_RETURN", {}).get("RESPONSE", {}).get("TEXT")
            )
            if text:
                raise QualysVMManagerError(
                    f"Unable to launch patch report: {text}"
                ) from e

        raise QualysVMManagerError(f"Unable to launch patch report: {response.content}")

    def launch_compliance_report(
        self,
        report_title,
        template_id,
        output_format="pdf",
        hide_header=False,
        ips=None,
        asset_group_ids=None,
        recipient_group_id=None,
        pdf_password=None,
        recipient_group=None,
        report_refs=None,
    ):
        """
        Launch a compliance report
        :param report_title: {str} A user-defined report title. The title may have a maximum of 128
            characters. For a PCI compliance report, the report title is provided by Qualys
            and cannot be changed.
        :param template_id: {str} The template ID of the report you want to launch.
        :param output_format: {str} One output format may be specified. When output_format=pdf is specified,
            the Secure PDF Distribution may be used. Valid values:
            - pdf
            - mht
            - html
        :param hide_header: {str} (Valid for CSV format report only). Specify hide_header=1 to omit
            the header information from the report. By default this information is included.
        :param ips: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple IPs/ranges are comma separated. When
            specified, hosts defined in the report template are not included in the report.
            See also "Using Asset Tags."
        :param asset_group_ids: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple asset group IDs are comma separated.
            When specified, hosts defined in the report template are not included in the
            report. Looking for asset group IDs? Use the asset_group_list.php function
            (see the API v1 User Guide).
        :param recipient_group_id: {str} Specify users who will receive the email notification when the report
            is complete (i.e. supply a distribution group ID). Where do I find this ID?
            Log in to your Qualys account, go to Users > Distribution Groups and select
            Info for a group in the list.
        :param pdf_password: {str} (Optional; Required for secure PDF distribution) The password
            to be used for encryption. Requirements: - the password must have a minimum
            of 8 characters (ascii), and a maximum of 32 characters - the password must
            contain alpha and numeric characters - the password cannot match the password
            for the user's Qualys account. - the password must follow the password security
            guidelines defined for your subscription (log in and go to Subscription Setup > Security
            Options).
        :param recipient_group: {str} (Optional; Optional for secure PDF distribution) The report recipients
            in the form of one or more distribution groups, as defined using the Qualys
            UI. Multiple distribution groups are comma separated. A maximum of 50 distribution
            groups may be entered.
        :param report_refs: {str} (Required for PCI compliance report) For a PCI compliance
            report, either the technical or executive report, this
            parameter specifies the scan reference to include. A scan
            reference starts with the string "scan/" followed by a
            reference ID number. The scan reference must be for a
            scan that was run using the PCI Options profile. Only one
            scan reference may be specified.
            Required: PCI Executive Report, PCI Technical Report
            Invalid: Qualys Top 20 Report, SANS Top 20 Report
        :return: {str} The report id
        """
        url = self._get_full_url("report")
        data = {
            "action": "launch",
            "report_type": "Compliance",
            "hide_header": hide_header,
            "report_title": report_title,
            "template_id": template_id,
            "output_format": output_format,
            "recipient_group_id": recipient_group_id,
            "pdf_password": pdf_password,
            "recipient_group": recipient_group,
            "report_refs": report_refs,
            "ips": ips,
            "asset_group_ids": asset_group_ids,
        }

        data = {k: v for k, v in data.items() if v}
        response = self.session.post(url, data=data)

        self.validate_response(response, "Unable to launch compliance report")

        try:
            return (
                xmltodict.parse(response.content, dict_constructor=dict)
                .get("SIMPLE_RETURN", {})
                .get("RESPONSE", {})
                .get("ITEM_LIST", {})
                .get("ITEM", {})
                .get("VALUE")
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            parsed_content = xmltodict.parse(response.content, dict_constructor=dict)
            text = (
                parsed_content.get("SIMPLE_RETURN", {}).get("RESPONSE", {}).get("TEXT")
            )
            if text:
                raise QualysVMManagerError(
                    f"Unable to launch patch report: {text}"
                ) from e

        raise QualysVMManagerError(
            f"Unable to launch compliance report: {response.content}"
        )

    def launch_scan_report(
        self,
        report_title,
        template_id,
        output_format="pdf",
        hide_header=False,
        ips=None,
        asset_group_ids=None,
        recipient_group_id=None,
        pdf_password=None,
        recipient_group=None,
        report_refs=None,
    ):
        """
        Launch a scan report
        :param report_title: {str} A user-defined report title. The title may have a maximum of 128
            characters. For a PCI compliance report, the report title is provided by Qualys
            and cannot be changed.
        :param template_id: {str} The template ID of the report you want to launch.
        :param output_format: {str} One output format may be specified. When output_format=pdf is specified,
            the Secure PDF Distribution may be used. Valid values:
            - pdf
            - mht
            - html
        :param hide_header: {str} (Valid for CSV format report only). Specify hide_header=1 to omit
            the header information from the report. By default this information is included.
        :param ips: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple IPs/ranges are comma separated. When
            specified, hosts defined in the report template are not included in the report.
            See also "Using Asset Tags."
        :param asset_group_ids: {str} Specify IPs/ranges to change (override) the report target, as defined
            in the patch report template. Multiple asset group IDs are comma separated.
            When specified, hosts defined in the report template are not included in the
            report. Looking for asset group IDs? Use the asset_group_list.php function
            (see the API v1 User Guide).
        :param recipient_group_id: {str} Specify users who will receive the email notification when the report
            is complete (i.e. supply a distribution group ID). Where do I find this ID?
            Log in to your Qualys account, go to Users > Distribution Groups and select
            Info for a group in the list.
        :param pdf_password: {str} (Optional; Required for secure PDF distribution) The password
            to be used for encryption. Requirements: - the password must have a minimum
            of 8 characters (ascii), and a maximum of 32 characters - the password must
            contain alpha and numeric characters - the password cannot match the password
            for the user's Qualys account. - the password must follow the password security
            guidelines defined for your subscription (log in and go to Subscription Setup > Security
            Options).
        :param recipient_group: {str} (Optional; Optional for secure PDF distribution) The report recipients
            in the form of one or more distribution groups, as defined using the Qualys
            UI. Multiple distribution groups are comma separated. A maximum of 50 distribution
            groups may be entered.
        :param report_refs: {str} (Required for PCI compliance report) For a PCI compliance
            report, either the technical or executive report, this
            parameter specifies the scan reference to include. A scan
            reference starts with the string "scan/" followed by a
            reference ID number. The scan reference must be for a
            scan that was run using the PCI Options profile. Only one
            scan reference may be specified.
            Required: PCI Executive Report, PCI Technical Report
            Invalid: Qualys Top 20 Report, SANS Top 20 Report
        :return: {str} The report id
        """
        url = self._get_full_url("report")
        data = {
            "action": "launch",
            "report_type": "Scan",
            "hide_header": hide_header,
            "report_title": report_title,
            "template_id": template_id,
            "output_format": output_format,
            "recipient_group_id": recipient_group_id,
            "pdf_password": pdf_password,
            "recipient_group": recipient_group,
            "report_refs": report_refs,
            "ips": ips,
            "asset_group_ids": asset_group_ids,
        }

        data = {k: v for k, v in data.items() if v}
        response = self.session.post(url, data=data)

        self.validate_response(response, "Unable to launch scan report")

        try:
            return (
                xmltodict.parse(response.content, dict_constructor=dict)
                .get("SIMPLE_RETURN", {})
                .get("RESPONSE", {})
                .get("ITEM_LIST", {})
                .get("ITEM", {})
                .get("VALUE")
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            parsed_content = xmltodict.parse(response.content, dict_constructor=dict)
            text = (
                parsed_content.get("SIMPLE_RETURN", {}).get("RESPONSE", {}).get("TEXT")
            )
            if text:
                raise QualysVMManagerError(
                    f"Unable to launch patch report: {text}"
                ) from e

        raise QualysVMManagerError(f"Unable to launch scan report: {response.content}")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if response.status_code == 409:
                raise QualysVMManagerError("API rate limit exceeded.")

            try:
                content = xmltodict.parse(response.content, dict_constructor=dict)
                text = content["SIMPLE_RETURN"]["RESPONSE"]["TEXT"]

            except:
                # Not error message
                raise QualysVMManagerError(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise QualysVMManagerError(f"{error_msg}: {error} - {text}")
