# ============================================================================#
# title           :StealthwatchManager.py
# description     :This Module contain all Protectwise operations functionality
# author          :avital@siemplify.co
# date            :22-02-2018
# python_version  :2.7
# libreries       :
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations

import copy
import datetime
import time

import requests

# ============================== CONSTS ===================================== #

FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

JSON_HEADERS = {"Content-Type": "application/json"}

FLOW_RESULTS_LIMIT = 5000
FLOW_SEARCH_DATA = {
    "searchName": None,
    "startTime": None,
    "endTime": None,
    "subject": {"ipAddresses": {"includes": [], "excludes": []}},
    "peer": {"ipAddresses": {"includes": [], "excludes": []}},
    "orientation": "either",
    "maxRows": FLOW_RESULTS_LIMIT,
    "excludeBpsPps": False,
    "excludeOthers": False,
    "excludeCounts": False,
    "defaultColumns": True,
}

EVENTS_SEARCH_DATA = {"timeRange": {"from": None, "to": None}}

COMPLETED_SEARCH_STATUS = "COMPLETED"
ERROR_SEARCH_STATUS = "FAILED"

# ============================= CLASSES ===================================== #


class StealthwatchManagerError(Exception):
    """
    General Exception for Stealthwatch manager
    """

    pass


class StealthwatchManager:
    def __init__(self, server_address, username, password, verify_ssl=False):
        """
        Connect to Stealthwatch server
        """
        self.server_address = server_address
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers = FORM_HEADERS
        self.session.cookies = self.authenticate(username, password)
        self.session.headers = JSON_HEADERS
        self.session.headers["Cookie"] = (
            f"stealthwatch.jwt={self.session.cookies.get_dict().get('stealthwatch.jwt')}"
        )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            # Not a JSON - return content
            raise StealthwatchManagerError(f"{error_msg}: {error} - {error.response.content}")

    def authenticate(self, username, password):
        url = f"{self.server_address}/token/v2/authenticate"

        response = self.session.post(url=url, data={"username": username, "password": password})

        self.validate_response(response, "Unable to connect to Stealthwatch")

        # Store the received cookie
        return response.cookies

    def test_connectivity(self):
        """
        Test connectivity to StealthWatch instance
        :return: True if connection is successfull, exception otherwise.
        """
        self.get_domains()
        return True

    def get_domain_id_by_name(self, domain_name):
        """
        Get doamin ID by name
        :param domain_name: {str} The domain's name
        :return: {int} The domain id
        """
        domains = self.get_domains()

        for domain in domains:
            if domain.get("displayName", "").lower() == domain_name.lower():
                return domain.get("id")

    def search_flows(
        self,
        domain_id,
        start_time,
        end_time,
        source_ips=None,
        destination_ips=None,
        limit=FLOW_RESULTS_LIMIT,
    ):
        """
        Run a flow search
        :param domain_id: {int} The domain id
        :param start_time: {str} The start time to search from (isoformat)
        :param end_time: {str} The end time to search from (isoformat)
        :param source_ips: {list} Source ips to filter in search
        :param destination_ips: {list} Destination ips to filter in search
        :return: {JSON} Flow search results.
        """
        if not source_ips:
            source_ips = []

        if not destination_ips:
            destination_ips = []

        search_name = f"Flow Search {datetime.datetime.now().isoformat()}"

        # Construct the search data
        data = copy.deepcopy(FLOW_SEARCH_DATA)

        data["subject"]["ipAddresses"]["includes"] = source_ips
        data["peer"]["ipAddresses"]["includes"] = destination_ips
        data["searchName"] = search_name
        data["startTime"] = start_time
        data["endTime"] = end_time
        data["maxRows"] = limit

        url = f"{self.server_address}/sw-reporting/v1/tenants/{domain_id}/flow-reports/top-hosts/queries"

        # Start search
        response = self.session.post(url, json=data)
        self.validate_response(response, "Unable to search flows")

        # The search id
        return response.json().get("data", {}).get("queryId")

    def search_events(self, domain_id, start_time, end_time, src_ip=None, dst_ip=None):
        """
        Search for events by an ip
        :param domain_id: {int} The domain id
        :param start_time: {str} The start time of events to filter by (%Y-%m-%dT%H:%M:00.000%z)
        :param end_time: {str} The end time of events to filter by (%Y-%m-%dT%H:%M:00.000%z)
        :param src_ip: {str} The source host's ip
        :param dst_ip: {str} The dest host's ip
        :return: {JSON} Events search results.
        """
        # Construct the search data
        data = copy.deepcopy(EVENTS_SEARCH_DATA)
        if src_ip or dst_ip:
            data["hosts"] = []

        if src_ip:
            data["hosts"].append({"ipAddress": src_ip, "type": "source"})
        if dst_ip:
            data["hosts"].append({"ipAddress": dst_ip, "type": "target"})

        data["timeRange"]["from"] = start_time
        data["timeRange"]["to"] = end_time

        url = f"{self.server_address}/sw-reporting/v1/tenants/{domain_id}/security-events/queries"

        # Start search
        response = self.session.post(url, json=data)
        self.validate_response(response, "Unable to search events")

        # The search id
        return response.json().get("data", {}).get("queryId")

    def get_events_search_results(self, domain_id, search_id, limit=None):
        """
        Get results of an events search
        :param domain_id: {Str} The domain id
        :param search_id: {stR} THe search id
        :return: {list} The search results
        """
        url = f"{self.server_address}/sw-reporting/v1/tenants/{domain_id}/security-events/queries/{search_id}"

        while not self.is_search_completed(url, search_id):
            if self.is_search_error(url, search_id):
                raise StealthwatchManagerError(f"Search {search_id} has failed.")
            time.sleep(1)

        results_url = f"{self.server_address}/sw-reporting/v1/tenants/{domain_id}/security-events/results/{search_id}"

        return self.get_search_results(results_url, search_id, limit)

    def get_flows_search_results(self, domain_id, search_id, limit=None):
        """
        Get results of an events search
        :param domain_id: {Str} The domain id
        :param search_id: {stR} THe search id
        :return: {list} The search results
        """
        url = f"{self.server_address}/sw-reporting/v1/tenants/{domain_id}/flow-reports/top-hosts/queries/{search_id}"

        while not self.is_search_completed(url, search_id):
            if self.is_search_error(url, search_id):
                raise StealthwatchManagerError(f"Search {search_id} has failed.")
            time.sleep(1)

        results_url = f"{self.server_address}/sw-reporting/v1/tenants/{domain_id}/flow-reports/top-hosts/results/{search_id}"

        return self.get_search_results(results_url, search_id, limit)

    def get_search_status(self, url, search_id):
        """
        Get the current status of a search job
        :param url: {str} The url to query the status from
        :param search_id: {str} The id of the search
        :return:
        """
        response = self.session.get(url)
        self.validate_response(response, f"Unable to get search {search_id} status")

        # The id of the job of the new search
        return response.json().get("data", {})["status"]

    def is_search_completed(self, url, search_id):
        """
        Check whether a search is completed
        :param url: {str} The url to query about the search
        :param search_id: {str} The id of the search
        :return: {bool} True if completed, False otherwise
        """
        status = self.get_search_status(url, search_id)
        return status == COMPLETED_SEARCH_STATUS

    def is_search_error(self, url, search_id):
        """
        Check whether a search has failed
        :param url: {str} The url to query about the search
        :param search_id: {str} The id of the search
        :return: {bool} True if failed, False otherwise
        """
        status = self.get_search_status(url, search_id)
        return status == ERROR_SEARCH_STATUS

    def get_search_results(self, url, search_id, limit=None):
        """
        Get search results
        :param url: {str} The url of the endpoint to fetch results from
        :param search_id: {int} The search id
        :param limit: {int} Results limit
        :return: {JSON} Search results (list of dicts)
        """
        response = self.session.get(url)
        self.validate_response(response, f"Unable to get results for search {search_id}")

        if limit:
            return response.json().get("data", {}).get("results", [])[:limit]

        return response.json().get("data", {}).get("results", [])

    def get_domains(self):
        """
        Get all domains that are configured in the system.
        :return: {JSON} All domains
        """
        url = f"{self.server_address}/sw-reporting/v1/tenants"
        response = self.session.get(url)
        self.validate_response(response, "Unable to get domains")

        return response.json().get("data", [])

    def get_domain_id_by_ip(self, ip):
        """
        Get domain id by an ip
        :param ip: {str} The ip address
        :return: {int} The id of the domain that owns the host.
        """
        domains = self.get_domains()

        for domain in domains:
            url = f"{self.server_address}/smc/rest/domains/{domain['id']}/hosts"
            response = self.session.get(url)
            self.validate_response(response, "Unable to get domain id for ip")

            # Search for the ip in the found domain hosts
            for result in response.json():
                if result["ipAddress"] == ip:
                    return result["domainId"]

        # If the domain ID was not found by the search above, try a direct
        # search. Once a domain with the ip was found - return its ID
        for domain in domains:
            url = f"{self.server_address}/smc/rest/domains/{domain['id']}/hosts/{ip}"
            response = self.session.get(url)

            if response.ok:
                return domain["id"]

        raise StealthwatchManagerError("Unable to get domain id for ip")
