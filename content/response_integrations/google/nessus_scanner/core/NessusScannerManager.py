# coding=utf-8
# ==============================================================================
# title           :NessusScannerManager.py
# description     :This Module contain all Nessus functionality
# author          :zivh@siemplify.co
# date            :03-15-18
# python_version  :2.7
# libraries       :
# requirements    :access to WAN
# product_version :1.0.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================

from __future__ import annotations
import requests
import time


# =====================================
#             CONSTANTS               #
# =====================================
LOCAL_HOST = ""
LOCAL_ACCESS_KEY = ""
LOCAL_SECRET_KEY = ""
RUNNING_SCAN_STATUS = ["pending", "running", "completed"]

CLI_FOLDER_ID = 100
READY_STATUS = "ready"
COMPLETED_STATUS = "completed"
RUNNING_STATUS = "running"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

# =====================================
#               CLASS                 #
# =====================================


class NessusScannerError(Exception):
    """
    General Exception for NessusScanner manager
    """

    pass


class NessusScanner:

    def __init__(self, access_key, secret_key, api_root, verify_ssl=False):
        self.api_root = api_root
        self.session = requests.Session()
        self.session.verify = verify_ssl

        key_value = f"accessKey={access_key}; secretKey={secret_key}"
        HEADERS.update({"X-ApiKeys": key_value})
        self.session.headers.update(HEADERS)

    def test_connectivity(self):
        """
        Returns the server status
        :return: True if ready, else False
        """
        response = self.session.get(f"{self.api_root}/server/status")
        self.validate_error(response)
        return response.json()["status"] == READY_STATUS

    def get_scan_templates(self):
        """
        Get list of all templates
        :return: {list}
        """
        response = self.session.get(f"{self.api_root}/editor/policy/templates")
        self.validate_error(response)
        return response.json()["templates"]

    def get_scan_templates_csv(self):
        """
        Get scan templates in csv format
        :return: {list} {template_title, template_name, template_id}
        """
        csv_output = ["Title, Name, UUID"]
        scan_templates = self.get_scan_templates()
        for template in scan_templates:
            csv_output.append(
                f"{template['title']}, {template['name']}, {template['uuid']}"
            )
        return csv_output

    def get_scan_template_uuid_by_title(self, template_title):
        """
        Get scan template(policy) id by template name
        :param template_title: {string} scan policy
        :return: {string} scan policy uuid
        """
        scan_templates = self.get_scan_templates()
        for template in scan_templates:
            if template_title in list(template.values()):
                return template["uuid"]

        raise NessusScannerError(f'"{template_title}" template was not found.')

    def create_scan(self, scan_name, test_targets, description, template_uuid):
        """
        Create new scan and return 'true' if succeed
        :param scan_name: {string} display scan name
        :param test_targets: {list} targets (ip addresses or domains. example: 192.168.1.1, test.com)
        :param template_uuid: {string} template(policy) identifier
        :param description:  {string} short description
        :return: {dict} scan details
        """
        settings = {
            "name": scan_name,
            "folder_id": CLI_FOLDER_ID,
            "text_targets": test_targets,
            "description": description,
        }
        url = f"{self.api_root}/scans"
        response = self.session.post(
            url, json={"uuid": template_uuid, "settings": settings}
        )
        self.validate_error(response)

        return response.json()["scan"]

    def get_scans(self):
        """
        return all available scans
        :return: {list}
        """
        response = self.session.get(f"{self.api_root}/scans")
        self.validate_error(response)
        return response.json()["scans"]

    def get_scans_name_csv(self):
        """
        Get scans in csv format
        :return: {list} {name, scan_status}
        """
        csv_output = ["Name, Status"]
        scans = self.get_scans()
        for scan in scans:
            csv_output.append(f"{scan.get('name')}, {scan.get('status')}")
        return csv_output

    def get_scan_details(self, scan_name):
        """
        return specific scan data
        :param scan_name: {string} scan displayed name
        :return: {dict} scan information
        """
        scan_id = None
        scans = self.get_scans()
        # Check if scan already exist
        for scan in scans:
            if scan_name.upper() == scan["name"].upper():
                scan_id = scan["id"]
                break

        if scan_id:
            response = self.session.get(f"{self.api_root}/scans/{scan_id}")
            self.validate_error(response)
            return response.json()

        raise NessusScannerError(f"Error: Scan named '{scan_name}' not found.")

    def download_scan(self, scan_name):
        """
        Export scan and then download it
        :param scan_name: {string} scan displayed name
        :return: {string} file data
        """
        scan_id = self.get_scan_details(scan_name)["info"]["object_id"]
        if scan_id:
            # Export scan
            url = f"{self.api_root}/scans/{scan_id}/export"
            response = self.session.post(
                url, json={"format": "html", "chapters": "vuln_by_host"}
            )
            self.validate_error(response)
            file_id = response.json()["file"]
            # Check export status - should be ready when done.
            status = self.check_export_status(scan_id, file_id)

            # When export file is done, scan can be downloaded.
            if status == READY_STATUS:
                return self.download_exported_scan(scan_id, file_id)

    def check_export_status(self, scan_id, file_id):
        """
        Export scan and return export status
        :param scan_id: {string} scan identifier
        :param file_id: {string} file identifier
        :return: {string} export file status (ready when done)
        """
        url = f"{self.api_root}/scans/{scan_id}/export/{file_id}/status"
        status_res = self.session.get(url)
        self.validate_error(status_res)

        while status_res.json()["status"] != READY_STATUS:
            status_res = self.session.get(url)
            time.sleep(2)
        return status_res.json()["status"]

    def download_exported_scan(self, scan_id, file_id):
        """
        Download scan
        :param scan_id: {string} scan identifier
        :param file_id: {string} file identifier
        :return: {string} file data
        """
        file_request = self.session.get(
            f"{self.api_root}/scans/{scan_id}/export/{file_id}/download"
        )
        self.validate_error(file_request)
        return file_request.content

    def launch_scan_by_id(self, scan_id):
        """
        Run scan
        :param scan_id: {string} scan identifier
        :return: {json}
        """
        response = self.session.post(f"{self.api_root}/scans/{scan_id}/launch")
        self.validate_error(response)
        return response.json()

    def launch_scan_and_wait(self, scan_name):
        """
        Run scan and check for status
        :param scan_name: {string} scan displayed name
        :return: {json}
        """
        scan_details = self.get_scan_details(scan_name)
        scan_after_launch = {}
        # Check if scan already running - Can't launch scan that already running
        if scan_details["info"]["status"] == RUNNING_STATUS:
            scan_status = scan_details["info"]["status"]
        else:
            scan_id = scan_details["info"]["object_id"]
            scan = self.launch_scan_by_id(scan_id)
            # Check for scan launch status
            scan_after_launch = self.get_scan_details(scan_name)
            scan_status = scan_after_launch["info"]["status"]

        # Wait until scan status is done
        while scan_status != COMPLETED_STATUS:
            scan_after_launch = self.get_scan_details(scan_name)
            scan_status = scan_after_launch["info"]["status"]
            if scan_status not in RUNNING_SCAN_STATUS:
                raise NessusScannerError(f"Scan status is: {scan_status}")
            time.sleep(2)
        return scan_after_launch

    def validate_error(self, response):
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise NessusScannerError(f"{e}. {response.content}")


if __name__ == "__main__":

    # nessus_manager = NessusScanner(LOCAL_ACCESS_KEY, LOCAL_SECRET_KEY, LOCAL_HOST)

    # conn = nessus_manager.test_connectivity()
    #
    # templates = nessus_manager.get_scan_templates_csv()
    # my_template_uuid = nessus_manager.get_scan_template_uuid_by_title('Advanced Scan')
    #
    # my_new_scan = nessus_manager.create_scan('publ test', 'IP_ADDRESS', 'auto test desc', my_template_uuid)

    # scan_details = nessus_manager.get_scan_details('Machine_Name')

    # my_file = nessus_manager.download_scan('Nessus - Nil')

    #
    # scan_id = scan_details['info']['object_id']
    # launch = nessus_manager.launch_scan_by_id(scan_id)
    # launch_wait = nessus_manager.launch_scan_and_wait('Machine_Name')

    print("")
