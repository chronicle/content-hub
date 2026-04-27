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
import requests
import datetime
import time
import copy
from functools import reduce


# ============================== CONSTS ===================================== #

FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

JSON_HEADERS = {"Content-Type": "application/json"}

FLOW_SEARCH_DATA = {
    "searchDisplayName": None,
    "searchType": "flowAnalysis",
    "savedByUser": False,
    "user": None,
    "searchContext": {
        "flowAnalysisFilter": {
            "name": None,
            "description": "",
            "absolute": {"from": None, "to": None},
            "domainId": None,
            "connection": {
                "applications": {"includes": [], "excludes": []},
                "byteRates": [],
                "bytes": [],
                "deviceIds": {"includes": [], "excludes": []},
                "packetRates": [],
                "packets": [],
                "tcpConnections": [],
                "urls": {"includes": [], "excludes": []},
                "portProtocols": {"includes": [], "excludes": []},
            },
            "object": {
                "byteRates": [],
                "bytes": [],
                "deviceIds": {"includes": [], "excludes": []},
                "devices": {"includes": [], "excludes": []},
                "hostGroups": {"includes": [], "excludes": []},
                "ipAddresses": {"includes": ["10.66.244.141"], "excludes": []},
                "orientation": "either",
                "packetRates": [],
                "packets": [],
                "portProtocols": {"includes": [], "excludes": []},
                "processHashes": {"includes": [], "excludes": []},
                "processNames": {"includes": [], "excludes": []},
                "ratios": [],
                "trustSecIds": {"includes": [], "excludes": []},
                "trustSecNames": {"includes": [], "excludes": []},
                "users": {"includes": [], "excludes": []},
            },
            "peer": {
                "byteRates": [],
                "bytes": [],
                "deviceIds": {"includes": [], "excludes": []},
                "devices": {"includes": [], "excludes": []},
                "hostGroups": {"includes": [], "excludes": []},
                "ipAddresses": {"includes": [], "excludes": []},
                "packetRates": [],
                "packets": [],
                "portProtocols": {"includes": [], "excludes": []},
                "processHashes": {"includes": [], "excludes": []},
                "processNames": {"includes": [], "excludes": []},
                "ratios": [],
                "trustSecIds": {"includes": [], "excludes": []},
                "trustSecNames": {"includes": [], "excludes": []},
                "users": {"includes": [], "excludes": []},
            },
            "relativeSecondsFromCurrent": None,
            "searchDisplayName": None,
            "advanced": {
                "direction": "",
                "maxRows": 0,
                "excludeBpsPps": False,
                "excludeOthers": False,
                "orderBy": "TOTAL_BYTES",
                "defaultColumns": True,
                "performanceOption": "Standard",
            },
        }
    },
}

ALERT_SEARCH_DATA = {
    "domainId": None,
    "searchDisplayName": None,
    "searchType": "alarmDetail",
    "searchContext": {
        "alarmStartDateTime": None,
        "alarmEndDateTime": None,
        "ipAddress": None,
    },
}

EVENTS_SEARCH_DATA = {
    "domainId": None,
    "searchDisplayName": None,
    "searchType": "securityEventDetail",
    "searchContext": {
        "ipAddress": None,
        "startActiveTime": None,
        "alarmCategory": None,
    },
}


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
        try:
            self.server_address = server_address
            self.username = username
            self.password = password
            self.verify = verify_ssl

            url = f"{server_address}/token/v2/authenticate"

            response = requests.post(
                url=url,
                data={"username": username, "password": password},
                headers=FORM_HEADERS,
                verify=self.verify,
            )

            response.raise_for_status()

            # Store the received cookie
            self.cookie = response.cookies

        except requests.HTTPError as error:
            raise StealthwatchManagerError(
                f"Unable to connect to Stealthwatch: {error} {error.response.content}"
            )

        except Exception as error:
            raise StealthwatchManagerError(
                f"Unable to connect to Stealthwatch: {error} {error}"
            )

    def test_connectivity(self):
        """
        Test connectivity to StealthWatch instance
        :return: True if connection is successfull, exception otherwise.
        """
        # Try to fetch given domain's id
        url = f"{self.server_address}/smc/rest/product/info"

        response = requests.get(
            url=url, headers=JSON_HEADERS, cookies=self.cookie, verify=self.verify
        )

        response.raise_for_status()

        return True

    def get_domain_id_by_name(self, domain_name):
        """
        Get doamin ID by name
        :param domain_name: {str} The domain's name
        :return: {int} The domain id
        """
        domains = self.get_domains()

        for domain in domains:
            if domain["domainName"].lower() == domain_name.lower():
                return domain["id"]

    def search_flows(
        self,
        domain_id,
        start_time,
        end_time,
        limit=None,
        source_ips=None,
        destination_ips=None,
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
        data["user"] = self.username
        data["searchDisplayName"] = search_name
        data["searchContext"]["flowAnalysisFilter"]["name"] = search_name
        data["searchContext"]["flowAnalysisFilter"]["domainId"] = domain_id
        data["searchContext"]["flowAnalysisFilter"]["object"]["ipAddresses"][
            "includes"
        ] = source_ips
        data["searchContext"]["flowAnalysisFilter"]["peer"]["ipAddresses"][
            "includes"
        ] = destination_ips
        data["searchContext"]["flowAnalysisFilter"]["searchDisplayName"] = search_name
        data["searchContext"]["flowAnalysisFilter"]["absolute"]["from"] = start_time
        data["searchContext"]["flowAnalysisFilter"]["absolute"]["to"] = end_time

        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches"

        # Start search
        response = requests.post(
            url=url,
            json=data,
            cookies=self.cookie,
            headers=JSON_HEADERS,
            verify=self.verify,
        )

        response.raise_for_status()

        # The search id
        search_id = response.json()["id"]

        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches/{search_id}/jobs"

        response = requests.post(
            url=url,
            headers=JSON_HEADERS,
            json={},
            cookies=self.cookie,
            verify=self.verify,
        )

        response.raise_for_status()

        # The id of the job of the new search
        job_id = response.json()["id"]

        # Wait for job to complete and return results
        return self.get_search_results(domain_id, search_id, job_id, limit)

    def search_alerts(self, domain_id, ip, start_time, end_time, limit=None):
        """
        Run an alert search
        :param domain_id: {int} The domain id
        :param ip: {str} The host's ip
        :param start_time: {str} The start time to search from (isoformat)
        :param end_time: {str} The end time to search from (isoformat)
        :param limit: {int} The results limit
        :return: {JSON} Alert search results.
        """

        search_name = f"Alert Search {datetime.datetime.now().isoformat()}"

        # Construct the search data
        data = copy.deepcopy(ALERT_SEARCH_DATA)
        data["searchDisplayName"] = search_name
        data["domainId"] = domain_id
        data["searchContext"]["ipAddress"] = ip
        data["searchContext"]["alarmStartDateTime"] = start_time
        data["searchContext"]["alarmEndDateTime"] = end_time

        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches"

        # Start search
        response = requests.post(
            url=url,
            json=data,
            cookies=self.cookie,
            headers=JSON_HEADERS,
            verify=self.verify,
        )

        response.raise_for_status()

        # The search id
        search_id = response.json()["id"]

        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches/{search_id}/jobs"

        response = requests.post(
            url=url,
            headers=JSON_HEADERS,
            json={},
            cookies=self.cookie,
            verify=self.verify,
        )

        response.raise_for_status()

        # The id of the job of the new search
        job_id = response.json()["id"]

        # Wait for job to complete and return results
        return self.get_search_results(domain_id, search_id, job_id, limit)

    def search_events(self, domain_id, alert_id, start_time, ip, limit=None):
        """
        Run a events search
        :param domain_id: {int} The domain id
        :param alert_id: {str} The id of the alert that owns the events
        :param ip: {str} The host's ip
        :param limit: {int} Results limit
        :return: {JSON} Events search results.
        """

        search_name = f"Event Search {datetime.datetime.now().isoformat()}"

        # Construct the search data
        data = copy.deepcopy(EVENTS_SEARCH_DATA)
        data["searchDisplayName"] = search_name
        data["domainId"] = domain_id
        data["searchContext"]["ipAddress"] = ip
        data["searchContext"]["startActiveTime"] = str(start_time)
        data["searchContext"]["alarmCategory"] = str(alert_id)

        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches"

        # Start search
        response = requests.post(
            url=url,
            json=data,
            cookies=self.cookie,
            headers=JSON_HEADERS,
            verify=self.verify,
        )

        response.raise_for_status()

        # The search id
        search_id = response.json()["id"]

        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches/{search_id}/jobs"

        response = requests.post(
            url=url,
            headers=JSON_HEADERS,
            json={},
            cookies=self.cookie,
            verify=self.verify,
        )

        response.raise_for_status()

        # The id of the job of the new search
        job_id = response.json()["id"]

        # Wait for job to complete and return results
        return self.get_search_results(domain_id, search_id, job_id, limit)

    def get_search_results(self, domain_id, search_id, job_id, limit=None):
        """
        Get search results
        :param domain_id: {int} The domain id
        :param search_id: {int} The search id
        :param job_id: {int} The job id
        :param limit: {int} Results limit
        :return: {JSON} Search results (list of dicts)
        """
        # Fetch job status
        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches/{search_id}/jobstatus/{job_id}"

        response = requests.get(
            url=url, headers=JSON_HEADERS, cookies=self.cookie, verify=self.verify
        )

        response.raise_for_status()

        # Wait for search to complete
        while not response.json()["percentComplete"] == 100:
            time.sleep(1)
            response = requests.get(
                url=url, headers=JSON_HEADERS, cookies=self.cookie, verify=self.verify
            )

            response.raise_for_status()

        # Fetch search results
        url = f"{self.server_address}/smc/rest/domains/{domain_id}/searches/{search_id}/jobs/{job_id}/results"

        response = requests.get(
            url=url,
            headers=JSON_HEADERS,
            params={"resultsPerPage": 1000},
            cookies=self.cookie,
            verify=self.verify,
        )

        results = response.json()["page"]["content"]
        pages_num = response.json()["page"]["totalPages"]

        for page in range(1, pages_num + 1):
            response = requests.get(
                url=url,
                params={"page": page, "resultsPerPage": 1000},
                headers=JSON_HEADERS,
                cookies=self.cookie,
                verify=self.verify,
            )

            results.extend(response.json()["page"]["content"])

            if limit and len(results) >= limit:
                return results[:limit]

        return results

    def get_domains(self):
        """
        Get all domains that are configured in the system.
        :return: {JSON} All domains
        """
        url = f"{self.server_address}/smc/rest/system/domains"
        response = requests.get(
            url=url, headers=JSON_HEADERS, cookies=self.cookie, verify=self.verify
        )

        response.raise_for_status()

        return response.json()

    def get_domain_id_by_ip(self, ip):
        """
        Get domain id by an ip
        :param ip: {str} The ip address
        :return: {int} The id of the domain that owns the host.
        """
        domains = self.get_domains()

        for domain in domains:
            url = f"{self.server_address}/smc/rest/domains/{domain['id']}/hosts"
            response = requests.get(
                url=url, headers=JSON_HEADERS, cookies=self.cookie, verify=self.verify
            )

            response.raise_for_status()

            # Search for the ip in the found domain hosts
            for result in response.json():
                if result["ipAddress"] == ip:
                    return result["domainId"]

        for domain in domains:
            url = f"{self.server_address}/smc/rest/domains/{domain['id']}/hosts/{ip}"
            response = requests.get(
                url=url, headers=JSON_HEADERS, cookies=self.cookie, verify=self.verify
            )

            if response.ok:
                return domain["id"]

    def filter_flow_results(self, results):
        """
        Filter results to resemble Stealthwatch Web results table
        :param results: {list} flow search results
        :return: {list} Filtered results
        """
        filtered_results = []
        for result in results:
            filtered_result = {}
            filtered_result["Start Time"] = result["firstActiveTime"]
            filtered_result["End Time"] = result["lastActiveTime"]
            filtered_result["Duration"] = "{}h {}m {}s".format(
                *self.convert_millis_to_human(result["activeDuration"])
            )
            filtered_result["Source Address"] = result["object"]["ipAddress"]
            filtered_result["Source Hostname"] = result["object"].get("name")
            filtered_result["Source Host Group"] = " | ".join(
                [group["name"] for group in result["object"]["hostGroups"]]
            )
            filtered_result["Source Port"] = result["object"]["portProtocol"]["port"]
            filtered_result["Source Protocol"] = result["object"]["portProtocol"][
                "protocol"
            ]
            filtered_result["Source Transfer Bytes"] = result["object"]["transferBytes"]
            filtered_result["Destination Address"] = result["peer"]["ipAddress"]
            filtered_result["Destination Hostname"] = result["peer"].get("name")
            filtered_result["Destination Host Group"] = " | ".join(
                [group["name"] for group in result["peer"]["hostGroups"]]
            )
            filtered_result["Destination Port"] = result["peer"]["portProtocol"]["port"]
            filtered_result["Destination Protocol"] = result["peer"]["portProtocol"][
                "protocol"
            ]
            filtered_result["Destination Transfer Bytes"] = result["peer"][
                "transferBytes"
            ]
            filtered_result["Connection Transfer Bytes"] = result["connection"][
                "transferBytes"
            ]

            filtered_results.append(filtered_result)

        return filtered_results

    def filter_event_results(self, results):
        """
        Filter results to resemble Stealthwatch Web results table
        :param results: {list} events search results
        :return: {list} Filtered results
        """
        filtered_results = []
        for result in results:
            filtered_result = {}
            filtered_result["First Active"] = result["firstActiveTime"]
            filtered_result["Last Time"] = result["lastActiveTime"]
            filtered_result["Duration"] = "{}h {}m {}s".format(
                *self.convert_millis_to_human(result["duration"])
            )
            filtered_result["Source Address"] = result["sourceIpAddress"]
            filtered_result["Source Hostname"] = result.get("sourceName")
            filtered_result["Source Host Groups"] = " | ".join(
                [group["name"] for group in result["sourceHostGroups"]]
            )
            filtered_result["Target Address"] = result["targetIpAddress"]
            filtered_result["Target Host Groups"] = " | ".join(
                [group["name"] for group in result["targetHostGroups"]]
            )
            filtered_result["Concern Index"] = result["ciPoints"]
            filtered_result["Security Events"] = " | ".join(
                [
                    f"{event['name']}-{event['hitCount']}"
                    for event in result["detailDisplays"]
                ]
            )

            filtered_results.append(filtered_result)

        return filtered_results

    def convert_millis_to_human(self, millis):
        """
        Convert milliseconds to human readable format (hours, minutes and seconds)
        :param millis: {int} Time in milliseconds.
        :return: {tuple} Hours, minutes and seconds.
        """
        seconds = (millis / 1000) % 60
        minutes = (millis / (1000 * 60)) % 60
        hours = (millis / (1000 * 60 * 60)) % 24
        return hours, minutes, seconds

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
