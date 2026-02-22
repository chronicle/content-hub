# ==============================================================================
# title           :CyberXManager.py
# description     :This Module contain all Active Directory operations functionality
# author          :victor@siemplify.co
# date            :14-11-18
# python_version  :2.7
# ==============================================================================
# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import urllib.parse
import copy

# =====================================
#             CONSTANTS               #
# =====================================
# Payloads amd Headers.
HEADERS = {"Authorization": "Token"}

# URLs
GET_DEVICES_URL = "/api/v1/devices"
GET_DEVICE_CONNECTIONS_URL = "/api/v1/devices/{0}/connections"  # {0} - Device ID.
GET_DEVICES_VULNERABILITIES_REPORT_URL = "/api/v1/reports/vulnerabilities/devices"
GET_ALERTS_URL = "/api/v1/alerts"
GET_EVENTS_URL = "/api/v1/events"


# =====================================
#              CLASSES                #
# =====================================
class CyberXManagerError(Exception):
    pass


class CyberXManager:
    def __init__(self, api_root, access_token, verify_ssl=False):
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Authorization"] = access_token

    @staticmethod
    def validate_response(response):
        """
        Validate HTTP response and raise informative Exception.
        :param response: HTTP response object.
        :return: {void}
        """
        try:
            response.raise_for_status()
        except Exception as err:
            raise CyberXManagerError(f"Error:{err}, Content:{response.content}")

    @staticmethod
    def get_vulnerability_report_by_address(reports, ip_address):
        """
        Get vulnerability report for specific IP address.(Method is static in purpose to not call get all reports
        every time.)
        :param reports: {list} list of report objects.
        :param ip_address: {string} Target IP address.
        :return: {dict} Report object.
        """
        for report in reports:
            if ip_address in report.get("ipAddresses"):
                return report
        raise CyberXManagerError(f'Error: Not found report for address "{ip_address}"')

    @staticmethod
    def get_vulnerability_report_by_host(reports, host_name):
        """
        Get vulnerability report for specific IP address.(Method is static in purpose to not call get all reports
        every time.)
        :param reports: {list} list of report objects.
        :param host_name: {string} Target IP address.
        :return: {dict} Report object.
        """
        for report in reports:
            if host_name.lower() == report.get("name").lower():
                return report
        raise CyberXManagerError(f'Error: Not found report for host name "{host_name}"')

    def get_all_devices(self):
        """
        Get list of all devices object that are detected by XSense.
        :return: {list} List of devices objects.
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_DEVICES_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_device_by_ip_address(self, ip_address):
        """
        Get device object by it's IP address.
        :param ip_address: {string} Target device IP address.
        :return: {dict} Device object.
        """
        devices = self.get_all_devices()
        for device in devices:
            if ip_address in device.get("ipAddress"):
                return device
        raise CyberXManagerError(f'Error, No device with ip "{ip_address}" was found.')

    def get_device_by_host_name(self, host_name):
        """
        Get device object by it's host name.
        :param host_name: {string} Target host name.
        :return: {dict} Device object.
        """
        devices = self.get_all_devices()
        for device in devices:
            if host_name.lower() == device.get("name").lower():
                return device
        raise CyberXManagerError(
            f'Error, No device with host name "{host_name}" was found.'
        )

    def get_device_id_by_address(self, ip_address):
        """
        Get device ID by it's IP address.
        :param ip_address: {string} Target IP address.
        :return: {string} Device ID.
        """
        device_information = self.get_device_by_ip_address(ip_address)
        if device_information.get("id"):
            return device_information.get("id")
        raise CyberXManagerError(
            f'Error: No ID found for device with address "{ip_address}"'
        )

    def get_device_id_by_host_name(self, host_name):
        """
        Get device ID by host name.
        :param host_name: {string} Target host name.
        :return: {string} Device ID.
        """
        device_information = self.get_device_by_host_name(host_name)
        if device_information.get("id"):
            return device_information.get("id")
        raise CyberXManagerError(
            f'Error: No ID found for device for host "{host_name}"'
        )

    def get_device_connections(self, device_id):
        """
        Get list of connections from device.
        :param device_id: {string} Target device ID.
        :return: {list} List of connection objects.
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_DEVICE_CONNECTIONS_URL.format(device_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_devices_vulnerability_reports(self):
        """
        Get list of report objects.
        :return: {list} List of Report objects.
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_DEVICES_VULNERABILITIES_REPORT_URL
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_alerts(self):
        """
        Fetch list of all alerts detected by XSense.
        :return: {list} List of alerts objects.
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_ALERTS_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_events(self):
        """
        Fetch list of events reported to the event log.
        :return: {list} List of events objects.
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_EVENTS_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()


#
