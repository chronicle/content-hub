# ============================================================================#
# title           :AlienVaultManager.py
# description     :This Module contain all AlienVault operations functionality
# author          :avital@siemplify.co
# date            :07-03-2018
# python_version  :2.7
# libreries       :requests, copy, base64, bs4
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
import base64
import urllib.parse
import copy
import urllib.parse
from simplejson.scanner import JSONDecodeError
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from functools import reduce


# ============================== CONSTS ===================================== #

ITEMS_PER_PAGE = 500

ASSETS_DATA = {
    "sEcho": "1",
    "iColumns": "9",
    "iDisplayStart": "0",
    "iDisplayLength": str(ITEMS_PER_PAGE),
    "mDataProp_0": "0",
    "mDataProp_1": "1",
    "mDataProp_2": "2",
    "mDataProp_3": "3",
    "mDataProp_4": "4",
    "mDataProp_5": "5",
    "mDataProp_6": "6",
    "mDataProp_7": "7",
    "mDataProp_8": "8",
    "iSortCol_0": "1",
    "sSortDir_0": "asc",
    "iSortingCols": "1",
    "bSortable_0": "false",
    "bSortable_1": "true",
    "bSortable_2": "true",
    "bSortable_3": "false",
    "bSortable_4": "true",
    "bSortable_5": "true",
    "bSortable_6": "true",
    "bSortable_7": "true",
    "bSortable_8": "false",
}

ASSET_DATA = {
    "asset_id": None,
    "asset_type": "asset",
    "sEcho": "1",
    "iColumns": "9",
    "iDisplayStart": "0",
    "iDisplayLength": str(ITEMS_PER_PAGE),
    "mDataProp_0": "0",
    "mDataProp_1": "1",
    "mDataProp_2": "2",
    "mDataProp_3": "3",
    "mDataProp_4": "4",
    "mDataProp_5": "5",
    "mDataProp_6": "6",
    "mDataProp_7": "7",
    "mDataProp_8": "8",
    "iSortCol_0": "1",
    "sSortDir_0": "asc",
    "iSortingCols": "1",
    "bSortable_0": "false",
    "bSortable_1": "true",
    "bSortable_2": "true",
    "bSortable_3": "false",
    "bSortable_4": "true",
    "bSortable_5": "true",
    "bSortable_6": "true",
    "bSortable_7": "true",
    "bSortable_8": "false",
}

ALARM_DATA = {
    "sEcho": "1",
    "iColumns": "11",
    "iDisplayStart": "0",
    "iDisplayLength": str(ITEMS_PER_PAGE),
    "mDataProp_0": "0",
    "mDataProp_1": "1",
    "mDataProp_2": "2",
    "mDataProp_3": "3",
    "mDataProp_4": "4",
    "mDataProp_5": "5",
    "mDataProp_6": "6",
    "mDataProp_7": "7",
    "mDataProp_8": "8",
    "mDataProp_9": "9",
    "mDataProp_10": "10",
    "iSortCol_0": "1",
    "sSortDir_0": "asc",
    "iSortingCols": "1",
    "bSortable_0": "false",
    "bSortable_1": "true",
    "bSortable_2": "true",
    "bSortable_3": "false",
    "bSortable_4": "true",
    "bSortable_5": "true",
    "bSortable_6": "true",
    "bSortable_7": "false",
    "bSortable_8": "true",
    "bSortable_9": "true",
    "bSortable_10": "false",
}

# URLs.
GET_ENVIRONMENT_VULNERABILITY_REPORT_URL = (
    "ossim/vulnmeter/index.php?m_opt=environment&sm_opt=vulnerabilities&h_opt=overview"
)
EVENTS_ID_SPLITTER = r"/ossim/forensics/base_qry_alert.php?submit="
GET_LAST_PCAP_URL = "ossim/pcap/index.php?m_opt=environment&sm_opt=traffic_capture"
PCAP_FILE_DOWNLOAD_URL = "ossim/pcap/download.php?scan_name={scan_name}&sensor_ip={sensor_ip}"  # {scan_name}- PCAP file name,  {sensor_ip} - Sensor IP
VULN_FILE_DOWNLOAD_URL = "ossim/vulnmeter/{0}"  # {0}- File URL.

# Consts
PCAP_FILE_INDICATOR = "pcap File"
MAX_RETRIES = 5


# ============================= CLASSES ===================================== #
class AlienVaultManagerError(Exception):
    """
    General Exception for AlienVault manager
    """

    pass


class AlienVaultManager:
    def __init__(self, server_address, username, password, use_ssl=False):
        """
        Connect to AlienVault SIEM
        """
        self.server_address = (
            server_address if server_address.endswith("/") else server_address + "/"
        )
        self.session = requests.Session()
        self.session.verify = use_ssl
        http_adapter = HTTPAdapter(
            max_retries=Retry(total=MAX_RETRIES, backoff_factor=1)
        )
        self.session.mount("http://", http_adapter)
        self.session.mount("https://", http_adapter)

        url = f"{server_address}/ossim/session/login.php"

        response = self.session.post(
            url=url,
            data={
                "user": username,
                "passu": password,
                "pass": base64.b64encode(password.encode()),
            },
        )

        self.validate_response(response, "Unable to connect")

        # Fetch and save token
        try:
            self.token = self.get_token()
        except JSONDecodeError:
            raise AlienVaultManagerError("Unable to get token. Check your credentials.")

    def get_token(self):
        """
        Obtain token from AlienVault SIEM to gain access (the token is not used
        but this action is needed to access the data in the SIEM)
        :return {str} The obtained token
        """
        url = f"{self.server_address}/ossim/session/token.php"

        response = self.session.post(url=url, data={"f_name": "asset_filter_value"})

        self.validate_response(response, "Unable to get token")

        return response.json()["data"]

    def get_assets(self):
        """
        Get all assets
        :return: {JSON} Assets information (list of dicts)
        """
        url = f"{self.server_address}/ossim/av_asset/asset/providers/load_assets_result.php"

        response = self.session.post(url=url, data=ASSETS_DATA)

        self.validate_response(response, "Unable to get assets")
        raw_assets = response.json()["aaData"]

        # Parse raw assets
        assets = []
        for asset in raw_assets:
            assets.append(self.parse_asset_info(asset))

        data = copy.deepcopy(ASSETS_DATA)

        # Handle paging
        while len(response.json()["aaData"]) == ITEMS_PER_PAGE:
            data["sEcho"] = str(int(data["sEcho"]) + 1)
            data["iDisplayStart"] = str(int(data["iDisplayStart"]) + ITEMS_PER_PAGE)

            response = self.session.post(url=url, data=data)

            self.validate_response(response, "Unable to get assets")
            raw_assets = response.json()["aaData"]

            # Parse raw assets
            for asset in raw_assets:
                assets.append(self.parse_asset_info(asset))

        return assets

    def get_asset_id_by_ip(self, ip):
        """
        Get assets id by ip address
        :param ip: {str} The ip address
        :return: {str} the asset's id
        """
        assets = self.get_assets()
        for asset in assets:
            # Search for the ip in the assets
            if ip == asset["Ip"]:
                return asset["Id"]  # Return asset id

    def get_asset_id_by_hostname(self, hostname):
        """
        Get assets id by hostname
        :param hostname: {str} The hostname
        :return: {str} the asset's id
        """
        assets = self.get_assets()
        for asset in assets:
            # Search for the hostname in the assets
            if hostname.lower() == asset["Hostname"].lower():
                return asset["Id"]  # Return asset id

    def get_asset_vulnerabilities(self, asset_id):
        """
        Get vulnerabilities by asset's id
        :param asset_id: {str} The asset's id
        :return: {JSON} List of vulnerabilities (list of dicts)
        """
        url = f"{self.server_address}/ossim/av_asset/common/providers/dt_vulnerabilities.php"

        data = copy.deepcopy(ASSET_DATA)
        data["asset_id"] = asset_id

        response = self.session.post(url=url, data=data)

        self.validate_response(response, "Unable to get vulnerabilities")

        raw_vulnerabilities = response.json()["aaData"]

        # Parse raw vulnerabilities
        vulnerabilities = []
        for vulnerability in raw_vulnerabilities:
            vulnerabilities.append(self.parse_vuln_info(vulnerability))

        while len(response.json()["aaData"]) == ITEMS_PER_PAGE:
            # Handle paging
            data["sEcho"] = str(int(data["sEcho"]) + 1)
            data["iDisplayStart"] = str(int(data["iDisplayStart"]) + ITEMS_PER_PAGE)

            response = self.session.post(url=url, data=data)

            self.validate_response(response, "Unable to get vulnerabilities")
            raw_vulnerabilities = response.json()["aaData"]

            # Parse raw vulnerabilities
            for vulnerability in raw_vulnerabilities:
                vulnerabilities.append(self.parse_vuln_info(vulnerability))

        return vulnerabilities

    def get_asset_info(self, asset_id):
        """
        Get asset information
        :param asset_id: {str} The asset's id
        :return: {json} The asset's info (dict)
        """
        url = (
            f"{self.server_address}/ossim/av_asset/common/providers/get_asset_info.php"
        )

        response = self.session.post(
            url=url, data={"asset_id": asset_id, "asset_type": "asset"}
        )

        self.validate_response(response, f"Unable to get asset info for {asset_id}")

        return response.json()

    def get_alarms(self, date_from=None, date_to=None):
        """
        Get alarms from AlienVault SIEM
        :param date_from: {str} Oldest alarm date YYYY-MM-DD (both date_from and date_to must be specified together)
        :param date_to: {str} Earliest alarm date YYYY-MM-DD (both date_from and date_to must be specified together)
        :return: {list} List of the found alarms
        """
        url = f"{self.server_address}/ossim/alarm/providers/alarm_console_ajax.php"

        data = copy.deepcopy(ALARM_DATA)

        params = {
            "hide_closed": 1,
            "intent": 0,
            "order": 1,
            "torder": "desc",
            "num_events_op": "less",
            "max_risk": 5,
            "min_risk": 0,
            "otx_activity": 0,
            "beep": 0,
            "no_resolv": 0,
            "date_from": date_from,
            "date_to": date_to,
        }

        params = {k: v for k, v in list(params.items()) if v}

        response = self.session.post(url=url, params=params, data=data)

        self.validate_response(response, "Unable to get alarms")

        raw_alarms = response.json()["aaData"]

        # Parse raw assets
        alarms = []
        for alarm in raw_alarms:
            alarms.append(self.parse_alarm_info(alarm))

        # Handle paging
        while len(response.json()["aaData"]) == ITEMS_PER_PAGE:
            data["sEcho"] = str(int(data["sEcho"]) + 1)
            data["iDisplayStart"] = str(int(data["iDisplayStart"]) + ITEMS_PER_PAGE)

            response = self.session.post(url=url, data=data, params=params)

            self.validate_response(response, "Unable to get alarms")

            raw_alarms = response.json()["aaData"]

            # Parse raw assets
            for alarm in raw_alarms:
                alarms.append(self.parse_alarm_info(alarm))

        return alarms

    def get_events_ids(self, alarm_id):
        """
        Get the events ids of a given alarm (by alarm id)
        :param alarm_id: {str} The alarm id
        :return: {list} The found event ids
        """
        url = f"{self.server_address}/ossim/alarm/views/alarm_events.php"

        data = {
            "backlog_id": alarm_id,
            "event_id": "",
            "show_all": 2,
            "hide": "directive",
            "from": 0,
            "box": 1,
        }

        response = self.session.post(url=url, data=data)

        self.validate_response(response, f"Unable to get event ids for {alarm_id}")

        events_table_content = response.content
        soup = BeautifulSoup(events_table_content, "lxml")

        event_ids = set()
        for html_chunk in soup.findAll("a", {"class": "greybox"}):
            event_ids.add(
                urllib.parse.unquote(
                    html_chunk.attrs["href"].split(EVENTS_ID_SPLITTER)[1].split("&")[0]
                )
            )

        return list(event_ids)

    @staticmethod
    def get_event_general_info(soup):
        """
        Parse general info of the event from the event's HTML page
        :param soup: {BeautifulSoup} BeautifulSoup object of the html page
        :return: {dict} The found info
        """
        event_info = {}
        try:
            # Get event general info
            for table in soup.findAll("table", {"class": "siem_table"}):
                for data in table.findAll("tr"):
                    if data.th:
                        event_info[data.th.text] = (
                            data.td.text.strip()
                            .replace("&nbsp;", "")
                            .replace("\n", "")
                            .replace("N/A", "")
                            if data.td
                            else None
                        )
        except Exception:
            # Can't collect event general info
            pass

        return event_info

    @staticmethod
    def get_sensor_and_category_info(soup):
        """
        Parse sensor and category info of the event from the event's HTML page
        :param soup: {BeautifulSoup} BeautifulSoup object of the html page
        :return: {dict} The found info
        """
        event_info = {}
        try:
            # Get AlienVault Sensor and Sub-category
            event_info.update(
                {
                    k.text: v.text
                    for k, v in zip(
                        soup.select(".siem_table > th"), soup.select(".siem_table > td")
                    )
                }
            )
        except Exception:
            # Can't collect AlienVault Sensor and Sub-category
            pass
        return event_info

    @staticmethod
    def get_destination_info(soup):
        """
        Parse destination info of the event from the event's HTML page
        :param soup: {BeautifulSoup} BeautifulSoup object of the html page
        :return: {dict} The found info
        """
        event_info = {}
        try:
            # Get event's destination info
            for pane in soup.findAll("div", {"class": "siem_detail_column_right"}):
                for table in pane.findAll("div", {"class": "siem_detail_content"}):
                    for data in table.findAll("div", {"class": "content_l"}):
                        event_info[f"Destination {data.text.split(':')[0]}"] = (
                            data.text.split(":")[1]
                            .strip()
                            .replace("&nbsp;", "")
                            .replace("\n", "")
                            .replace("N/A", "")
                        )

                    for data in table.findAll("div", {"class": "content_r"}):
                        event_info[f"Destination {data.text.split(':')[0]}"] = (
                            data.text.split(":")[1]
                            .strip()
                            .replace("&nbsp;", "")
                            .replace("\n", "")
                            .replace("N/A", "")
                        )

                for table in pane.findAll("table", {"class": "siem_table"}):
                    for data in table.findAll("tr"):
                        if data.th:
                            event_info[data.th.text] = (
                                data.td.text.strip()
                                .replace("&nbsp;", "")
                                .replace("\n", "")
                                .replace("N/A", "")
                                if data.td
                                else None
                            )
        except Exception:
            # Can't collect event's destination info
            pass

        return event_info

    @staticmethod
    def get_source_info(soup):
        """
        Parse source info of the event from the event's HTML page
        :param soup: {BeautifulSoup} BeautifulSoup object of the html page
        :return: {dict} The found info
        """
        event_info = {}
        try:
            # Get event's source info
            for pane in soup.findAll("div", {"class": "siem_detail_column_left"}):
                for table in pane.findAll("div", {"class": "siem_detail_content"}):
                    for data in table.findAll("div", {"class": "content_l"}):
                        event_info[f"Source {data.text.split(':')[0]}"] = (
                            data.text.split(":")[1]
                            .strip()
                            .replace("&nbsp;", "")
                            .replace("\n", "")
                            .replace("N/A", "")
                        )
                for data in table.findAll("div", {"class": "content_r"}):
                    event_info[f"Source {data.text.split(':')[0]}"] = (
                        data.text.split(":")[1]
                        .strip()
                        .replace("&nbsp;", "")
                        .replace("\n", "")
                        .replace("N/A", "")
                    )

                for table in pane.findAll("table", {"class": "siem_table"}):
                    for data in table.findAll("tr"):
                        if data.th:
                            event_info[data.th.text] = (
                                data.td.text.strip()
                                .replace("&nbsp;", "")
                                .replace("\n", "")
                                .replace("N/A", "")
                                if data.td
                                else None
                            )
        except Exception:
            # Can't collect event's source info
            pass

        return event_info

    @staticmethod
    def get_addresses_info(soup):
        """
        Parse source and destination addresses info of the event from
        the event's HTML page
        :param soup: {BeautifulSoup} BeautifulSoup object of the html page
        :return: {dict} The found info
        """
        event_info = {}
        try:
            # Get source and destination addresses
            for table in soup.findAll("table", {"class": "siem_table"}):
                for index, header in enumerate(table.findAll("th", {"class": "autow"})):
                    event_info[f"{header.text} Address"] = (
                        table.findAll("td", {"class": "center"})[index]
                        .text.strip()
                        .replace("&nbsp;", "")
                        .replace("\n", "")
                        .replace("N/A", "")
                    )
        except Exception:
            # Can't collect source and destination addresses
            pass

        return event_info

    @staticmethod
    def get_risk_and_priority_info(soup):
        """
        Parse risk and priority info of the event from the event's HTML page
        :param soup: {BeautifulSoup} BeautifulSoup object of the html page
        :return: {dict} The found info
        """
        event_info = {}
        try:
            # Get event risk and priority info
            for detail_section in soup.findAll("div", {"class": "siem_detail_section"}):
                if detail_section.find("div", "siem_left"):
                    event_info[detail_section.find("div", "siem_left").text] = (
                        detail_section.find("div", "siem_right")
                        .div.attrs["id"]
                        .split(";")[0]
                        .strip()
                        .replace("&nbsp;", "")
                        .replace("\n", "")
                        .replace("N/A", "")
                    )
        except Exception:
            # Can't collect event risk and priority info
            pass

        return event_info

    def get_event_info(self, event_id):
        """
        Get event information by id
        :param event_id: {str} The event's id
        :return: {dict} The event info
        """
        url = f"{self.server_address}/ossim/forensics/base_qry_alert.php"

        params = {"pag": "", "noheader": "", "submit": event_id}

        response = self.session.get(url=url, params=params)

        self.validate_response(response, f"Unable to get event info for {event_id}")

        event_page = response.content
        soup = BeautifulSoup(event_page, "lxml")

        event = {
            "Name": soup.find("div", {"class": "siem_title"})
            .text.strip()
            .replace("&nbsp;", "")
            .replace("\n", "")
            .replace("N/A", "")
        }

        event.update(self.get_event_general_info(soup))
        event.update(self.get_sensor_and_category_info(soup))
        event.update(self.get_destination_info(soup))
        event.update(self.get_source_info(soup))
        event.update(self.get_risk_and_priority_info(soup))
        event.update(self.get_addresses_info(soup))

        return event

    @staticmethod
    def parse_asset_info(asset_data):
        """
        Parse asset info to human readable dict
        :param asset_data: {dict} The asset data
        :return: {dict} Human readable asset data
        """
        return {
            "Id": asset_data.get("DT_RowId"),
            "Hostname": asset_data.get("1"),
            "Ip": asset_data.get("2"),
            "Device Type": asset_data.get("3"),
            "OS": asset_data.get("4"),
            "Asset Value": asset_data.get("5"),
            "Vuln Scan Scheduled": asset_data.get("6"),
            "HIDS Status": asset_data.get("7"),
        }

    @staticmethod
    def parse_alarm_info(alarm_data):
        """
        Parse alarm info to human readable dict
        :param alarm_data: {dict} The alarm data
        :return: {dict} Human readable alarm data
        """

        parsed_alarm = {
            "Id": alarm_data.get("DT_RowId"),
            "Intent": (
                BeautifulSoup(alarm_data.get("4"), "lxml")
                .contents[-1]
                .text.replace("\xa0", "")
                if BeautifulSoup(alarm_data.get("4"), "lxml").contents[-1]
                else None
            ),
            "Method": alarm_data.get("5"),
            "Date": BeautifulSoup(
                alarm_data.get("1"), "lxml"
            ).text,  # Sometimes come as "8 hours", "32 min"
            "Risk": (
                BeautifulSoup(alarm_data.get("6"), "lxml")
                .text.split("(")[-1]
                .split(")")[0]
                if BeautifulSoup(alarm_data.get("6"), "lxml")
                else None
            ),
        }

        try:
            # Get the source data form the id attr (the data is html)
            source_data = (
                BeautifulSoup(alarm_data.get("8"), "lxml").div.attrs["id"].split(";")
            )

            # Sometimes the source data comes as (address,hostname,id)
            # and sometimes as (ip,hostname) only
            if len(source_data) == 3:
                parsed_alarm["Source"] = {
                    "Id": source_data[2],
                    "Address": source_data[0],
                    "Hostname": source_data[1],
                }

            else:
                parsed_alarm["Source"] = {"Address": source_data[0]}

        except Exception:
            pass

        try:
            # Get the destination data form the id attr (the data is html)
            destination_data = (
                BeautifulSoup(alarm_data.get("9"), "lxml").div.attrs["id"].split(";")
            )

            # Sometimes the destination data comes as (address,hostname,id)
            # and sometimes as (ip,hostname) only
            if len(destination_data) == 3:
                parsed_alarm["Destination"] = {
                    "Id": destination_data[2],
                    "Address": destination_data[0],
                    "Hostname": destination_data[1],
                }

            else:
                parsed_alarm["Destination"] = {"Address": destination_data[0]}

        except Exception:
            pass

        return parsed_alarm

    @staticmethod
    def parse_vuln_info(vuln_data):
        """
        Parse vulnerability info to human readable dict
        :param asset_data: {list} The vulnerability data
        :return: {dict} Human readable asset data
        """
        return {
            "Scan Time": vuln_data[0],
            "Asset": vuln_data[1],
            "Vulnerability": vuln_data[2],
            "Id": vuln_data[3],
            "Service": vuln_data[4],
            "Severity": vuln_data[5],
        }

    @staticmethod
    def validate_response(res, error_msg="An error occurred"):
        """
        Validate a response
        :param res: {requests.Response} The response to validate
        """
        try:
            res.raise_for_status()

        except requests.HTTPError as error:
            raise AlienVaultManagerError(
                f"{error_msg}: {error} {error.response.content}"
            )

    @staticmethod
    def construct_csv(results):
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
                            [result.get(h, None) for h in headers],
                        )
                    ]
                )
            )

        return csv_output

    @staticmethod
    def fetch_pcap_url_parameters(url):
        """
        Fetch parameters from URL.
        :param url: URL {string}
        :return: key/value dict {dict}
        """
        result_dict = {}
        try:
            params_section = url.split("?")[1]
            params_and_values = params_section.split("&")
            for pair in params_and_values:
                result_dict[pair.split("=")[0]] = pair.split("=")[1]
        except Exception as err:
            raise AlienVaultManagerError(f"Error parsing pcap URL, Error: {str(err)}")

        return result_dict

    def get_last_pcap_files(self):
        """
        Get last pcap files download links.
        :return: list of dicts when each dict represent a file {list}
        """
        result_list = []
        request_url = urllib.parse.urljoin(self.server_address, GET_LAST_PCAP_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        soup = BeautifulSoup(response.content, "lxml")
        # Get target table.
        tables = soup.findAll("table", {"class": "table_list"})
        for table in tables:
            # Run on table rows when each one represent a file.
            rows = table.findAll("tr")
            for row in rows:
                # Fetch elements when each one is a file's property.
                elements = row.findAll("td")
                if elements:
                    file_data = {}
                    file_data["creation_time"] = elements[0].text
                    file_data["duration"] = elements[1].text
                    file_data["user"] = elements[2].txt
                    # Fetch PCAP file link.
                    pcap_link = elements[3].findAll("a")[1].get("href")
                    # Parse PCAP link and ass to file dict.
                    file_data.update(self.fetch_pcap_url_parameters(pcap_link))
                    # Add download URL.
                    file_data["download_link"] = urllib.parse.urljoin(
                        self.server_address,
                        PCAP_FILE_DOWNLOAD_URL.format(
                            scan_name=file_data.get("scan_name"),
                            sensor_ip=file_data.get("sensor_ip"),
                        ),
                    )

                    result_list.append(file_data)

        return result_list

    def get_vulnerability_reports(self):
        """
        Get vulnerability reports.
        :return: list of dicts when each dict represent report {list}
        """
        result_list = []
        request_url = urllib.parse.urljoin(
            self.server_address, GET_ENVIRONMENT_VULNERABILITY_REPORT_URL
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        soup = BeautifulSoup(response.content, "lxml")
        tables = soup.findAll("table", {"class": "table_list"})
        for table in tables:
            # Run on table rows when each one represent a file.
            rows = table.findAll("tr")
            for row in rows[:-1]:
                # Fetch elements when each one is a file's property.
                elements = row.findAll("td")
                if len(elements) > 4:
                    report_data = {}
                    report_data["Address"] = elements[0].text
                    report_data["creation_time"] = elements[1].text
                    # Fetch report file link.
                    if len(elements[4].findAll("a")) > 1:
                        report_url = elements[4].findAll("a")[2].get("href")
                        report_data["download_link"] = urllib.parse.urljoin(
                            self.server_address,
                            VULN_FILE_DOWNLOAD_URL.format(report_url),
                        )

                    result_list.append(report_data)

        return result_list

    def download_pcap_file(self, scan_name, sensor_ip):
        """
        Download pcap file content.
        :param scan_name: pcap file name {string}
        :param sensor_ip: AV sensor ip address {string}
        :return: pcap file content {byte array}
        """
        request_url = urllib.parse.urljoin(
            self.server_address,
            PCAP_FILE_DOWNLOAD_URL.format(scan_name=scan_name, sensor_ip=sensor_ip),
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.content

    def download_file_from_link(self, link):
        """
        Get file content from download link.
        :param link: file download link {string}
        :return: target file content {byte array}
        """
        response = self.session.get(link)
        self.validate_response(response)
        return response.content

    def get_event_pcap(self, event_id):
        """
        Get event pcap if exists
        :param event_id: {str} The event's id
        :return: {str} The event pcap content
        """
        url = f"{self.server_address}/ossim/forensics/base_qry_alert.php"

        params = {"pag": "", "noheader": "", "submit": event_id}

        response = self.session.get(url=url, params=params)

        self.validate_response(response, f"Unable to get event PCAP for {event_id}")

        event_page = response.content
        soup = BeautifulSoup(event_page, "lxml")

        pcap_divs = soup.findAll("div", {"class": "siem_detail_subsection_payload"})

        for div in pcap_divs:
            if PCAP_FILE_INDICATOR in div.text:
                url = f"{self.server_address}/ossim/forensics/{div.find('a')['href']}"
                response = self.session.get(url=url)
                self.validate_response(response)
                return response.content
