# ============================================================================#
# title           :Rapid7Manager.py
# description     :This Module contain all Rapid7 operations functionality
# author          :zivh@siemplify.co
# date            :25-03-2019
# python_version  :2.7 (except 2.7.13 - ctypes bug)
# libreries       :requests
# requirments     :
# product_version :
# ============================================================================#


# ============================= IMPORTS ===================================== #
from __future__ import annotations
import arrow
import requests

from .Rapid7Parser import Rapid7Parser
from TIPCommon import filter_old_alerts
from .UtilsManager import filter_processed_assets
from .constants import (
    GET_ASSETS_URL,
    GET_ASSET_VULNERABILITIES,
    GET_VULNERABILITY_DETAILS,
)


# ============================== CONSTS ===================================== #

DEFAULT_PAGE_SIZE = 100
MATCH_ANY = "any"
MATCH_ALL = "all"
COMPLETED_SCAN_STATUS = "finished"
FAILED_SCANS_STATUSES = ["aborted", "stopped", "error", "paused"]

# ============================= CLASSES ===================================== #


class Rapid7ManagerError(Exception):
    """
    General Exception for GSuite manager
    """

    pass


class Rapid7Manager:

    def __init__(self, api_root, username, password, verify_ssl=False, siemplify=None):
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.api_root = api_root.rstrip("/")
        self.session.auth = (username, password)
        self.parser = Rapid7Parser()
        self.siemplify = siemplify

    def test_connectivity(self):
        """
        discovering the available resources in this API
        :return:
        """
        res = self.session.get(self.api_root)
        return self.validate_response(res)

    def _paginate_results(
        self,
        url,
        method,
        params=None,
        data=None,
        err_msg="Unable to fetch resources",
        limit=None,
        limit_results=True,
    ):
        page_number = 0

        if not params:
            params = {}

        params.update(
            {
                "page": page_number,
                "size": min(DEFAULT_PAGE_SIZE, limit or DEFAULT_PAGE_SIZE),
                "sort": "id,desc"
            }
        )

        res = self.session.request(method, url, params=params, json=data)
        self.validate_response(res, err_msg)

        total_resources = res.json()["page"]["totalResources"]
        resources = res.json().get("resources", [])

        while len(resources) < total_resources:
            if limit and limit_results and len(resources) >= limit:
                break

            page_number += 1

            params.update({"page": page_number, "size": DEFAULT_PAGE_SIZE})

            res = self.session.request(method, url, params=params, json=data)
            self.validate_response(res, err_msg)

            resources.extend(res.json().get("resources", []))

        return resources[:limit] if limit and limit_results else resources

    def get_assets(self, assets_list, limit):
        """
        Get all assets
        :param assets_list: {list} List of existing assets.
        :param limit: {int} The max amount of assets to return.
        :return: {list, list} List of Asset objects, Updated assets list
        """
        url = GET_ASSETS_URL.format(api_root=self.api_root)
        resources = self._paginate_results(
            url,
            "GET",
            err_msg="Unable to get assets",
            limit=DEFAULT_PAGE_SIZE,
            limit_results=False,
        )
        assets = [self.parser.build_asset_object(res) for res in resources]
        filtered_assets = filter_processed_assets(
            logger=self.siemplify.LOGGER, assets=assets, assets_list=assets_list
        )
        for asset in filtered_assets:
            asset_json = next(
                (
                    item
                    for item in assets_list
                    if item.get("asset_id", None) == asset.id
                ),
                None,
            )
            if not asset_json:
                assets_list.append(
                    {
                        "asset_id": asset.id,
                        "ip": asset.ip,
                        "vulnerabilities": [],
                        "processed": False,
                    }
                )
        return filtered_assets[:limit], assets_list

    def get_asset_vulnerabilities(self, asset_id, existing_ids):
        """
        Get asset vulnerabilities
        :param asset_id: {str} Asset id.
        :param existing_ids: {list} The list of existing ids
        :return: {list} List of Vulnerability objects
        """
        url = GET_ASSET_VULNERABILITIES.format(
            api_root=self.api_root, asset_id=asset_id
        )
        resources = self._paginate_results(
            url,
            "GET",
            err_msg="Unable to get asset vulnerabilities",
            limit=DEFAULT_PAGE_SIZE,
            limit_results=False,
        )
        vulnerabilities = [
            self.parser.build_vulnerability_object(res) for res in resources
        ]
        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=vulnerabilities,
            existing_ids=existing_ids,
            id_key="id",
        )

        return filtered_alerts

    def get_vulnerability_details(self, vulnerability_id):
        """
        Get vulnerability details
        :param vulnerability_id: {str} Vulnerability id.
        :return: {VulnerabilityDetails}
        """
        url = GET_VULNERABILITY_DETAILS.format(
            api_root=self.api_root, vulnerability_id=vulnerability_id
        )
        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_vulnerability_details_object(response.json())

    def list_assets(self, limit=None):
        """
        Returns all assets for which you have access.
        :param limit: {int} The max amount of assets to list.
        :return: {list of dicts - asset info}
        """
        url = f"{self.api_root}/assets"
        return self._paginate_results(
            url, "GET", err_msg="Unable to list assets", limit=limit
        )

    def search_assets(self, filters=None, match_all_filters=False, limit=None):
        """
        Returns all assets for which you have access that match the given
        search criteria.
        :param filters: {list} Filters used to match assets. See Search
            Criteria for more information on the structure and format.
        :param match_all_filters: Whether to match all the gievn filters or
            just any of them.
        :return: {list} The found assets
        """
        url = f"{self.api_root}/assets/search"

        # Operator to determine how to match filters. "all" requires that all
        # filters match for an asset to be included. "any" requires only one
        # filter to match for an asset to be included.
        match = "any"
        if match_all_filters:
            match = "all"

        # e.g. Assets running ssh
        # filters = [{ "field": "service-name", "operator": "contains", "value": "ssh"}, {}]
        if not filters:
            filters = []

        data = {"filters": filters, "match": match}

        return self._paginate_results(
            url, "POST", err_msg="Unable to search assets", data=data, limit=limit
        )

    def get_asset_by_hostname(self, hostname):
        """
        Get an asset by hostname
        :param hostname: {str} The asset's hostname
        :return: {dict} The found asset
        """
        assets = self.search_assets(
            filters=[
                {
                    "field": "host-name",
                    "operator": "is",  # maybe should be contains?
                    "value": hostname,
                }
            ],
            limit=1,
        )

        if assets:
            return assets[0]

        raise Rapid7ManagerError(f"Asset {hostname} was not found.")

    def get_asset_by_ip(self, ip):
        """
        Get an asset by ip address
        :param ip: {str} The ip address of the asset
        :return: {dict} The found asset
        """
        assets = self.search_assets(
            filters=[{"field": "ip-address", "operator": "is", "value": ip}], limit=1
        )

        if assets:
            return assets[0]

        raise Rapid7ManagerError(f"Asset {ip} was not found.")

    def list_scans(self, active=False, limit=None, start_time=None):
        """
        Returns all scans.
        :param active: {boolean} Return running scans or past scans
        :param limit: {int} The max amount of scans to list.
        :param start_time: {datetime} Fetch only scans that started after
            given time
        :return: {list of dicts - scan info}
        """
        url = f"{self.api_root}/scans"

        active = str(active).lower()
        params = {"active": active}

        scans = self._paginate_results(
            url, "GET", err_msg="Unable to list scans", params=params, limit=limit
        )

        if start_time:
            return [
                scan for scan in scans if arrow.get(scan.get("startTime")) > start_time
            ]

        return scans

    def get_scan_id_by_name(self, scan_name):
        """
        Get scan ID by the scan name
        :param scan_name: {str} The name of the scan
        :return: {int} The ID of the scan
        """
        scans = self.list_scans()

        for scan in scans:
            if scan.get("scanName").lower() == scan_name.lower():
                return scan.get("id")

        raise Rapid7ManagerError(f"Scan {scan_name} was not found.")

    def get_template_id_by_name(self, template_name):
        """
        Get template ID by the template name
        :param template_name: {str} The name of the template
        :return: {int} The ID of the template
        """
        templates = self.list_scan_templates()

        for template in templates:
            if template.get("name").lower() == template_name.lower():
                return template.get("id")

        raise Rapid7ManagerError(f"Template {template_name} was not found.")

    def get_site_id_by_name(self, site_name):
        """
        Get site ID by the site name
        :param site_name: {str} The name of the site
        :return: {int} The ID of the site
        """
        sites = self.list_sites()

        for site in sites:
            if site.get("name").lower() == site_name.lower():
                return site.get("id")

        raise Rapid7ManagerError(f"Site {site_name} was not found.")

    def get_engine_id_by_name(self, engine_name, site_id=None):
        """
        Get engine ID by the engine name
        :param engine_name: {str} The name of the site
        :param site_id: {str} The ID of the site to which engines should be
            assign to.
        :return: {int} The ID of the engine
        """
        if site_id:
            engines = self.list_scan_engines_by_site(site_id)
        else:
            engines = self.list_scan_engines()

        for engine in engines:
            if engine.get("name").lower() == engine_name.lower():
                return engine.get("id")

        if site_id:
            raise Rapid7ManagerError(
                f"Engine {engine_name} was not found or isn't assigned to site {site_id}"
            )

        raise Rapid7ManagerError(f"Engine {engine_name} was not found.")

    def get_scan_by_id(self, scan_id):
        """
        Returns a scan info by ID.
        :param scan_id: {int} The ID of the scan.
        :return: {dict} The matching scan info
        """
        url = f"{self.api_root}/scans/{scan_id}"
        res = self.session.get(url)
        self.validate_response(res, f"Unable to get scan {scan_id} results.")

        return res.json()

    def list_scan_templates(self):
        """
        Returns all scan templates.
        :return: {list} The found scan template
        """
        url = f"{self.api_root}/scan_templates"
        res = self.session.get(url)

        self.validate_response(res, "Unable to list scan templates")
        return res.json().get("resources")

    def list_scan_engines(self):
        """
        Returns scan engines available to use for scanning.
        :return: {list} The found scan engines
        """
        url = f"{self.api_root}/scan_engines"
        res = self.session.get(url)
        self.validate_response(res, "Unable to list scan engines")
        return res.json().get("resources", [])

    def list_scan_engines_by_site(self, site_id):
        """
        Returns scan engines available to use for scanning.
        :return: {list} The found scan engines
        """
        url = f"{self.api_root}/sites/{site_id}/scan_engine"
        res = self.session.get(url)
        self.validate_response(res, f"Unable to list scan engines for site {site_id}")
        return res.json().get("resources", [])

    def list_sites(self, limit=None):
        """
        Retrieves a paged resource of accessible sites.
        :param limit: {int} The max amount of sites to list.
        :return: {list} The found sites
        """
        url = f"{self.api_root}/sites"

        return self._paginate_results(
            url, "GET", err_msg="Unable to list sites", limit=limit
        )

    def list_asset_groups(self, group_type=None, name=None, limit=None):
        """
        List the asset groups
        :param group_type: {str} The type of the asset group
        :param name: {str} A search pattern for the name of the asset group.
            Searches are case-insensitive contains.
        :return: {list} The found asset groups' details
        """
        url = f"{self.api_root}/asset_groups"

        params = {"type": group_type, "name": name}

        return self._paginate_results(
            url=url,
            method="GET",
            params=params,
            err_msg="Unable to list asset groups",
            limit=limit,
        )

    def launch_scan(self, site_name, engine_name, name, hosts, scan_template_name):
        """
        Starts a scan for the specified site.
        :param site_name: {int} The name of the site.
        :param engine_name: {int} The name of the scan engine.
        :param hosts: {list} The hosts that should be included as
            a part of the scan. This should be a mixture of IP addresses and
            hostnames as a String array.
        :param name: {string} The user-driven scan name for the scan
        :param scan_template_name: {string} The name of the scan template
        :return: {int} The ID of the new scan
        """
        site_id = self.get_site_id_by_name(site_name)
        engine_id = self.get_engine_id_by_name(engine_name)
        scan_template_id = self.get_template_id_by_name(scan_template_name)

        url = f"{self.api_root}/sites/{site_id}/scans"

        payload = {
            "engineId": engine_id,
            "hosts": hosts,
            "name": name,
            "templateId": scan_template_id,
        }

        res = self.session.post(url, json=payload)
        self.validate_response(res, "Unable to launch scan")
        return res.json().get("id")

    def is_scan_completed(self, scan_id):
        scan = self.get_scan_by_id(scan_id)

        if scan.get("status") in FAILED_SCANS_STATUSES:
            raise Rapid7ManagerError(f"Scan failed with status {scan.get('status')}")
        return scan.get("status") == COMPLETED_SCAN_STATUS

    def list_vulnerabilities(self, limit=None):
        """
        Returns all vulnerabilities that can be assessed during a scan
        :param limit: {int} The max number of vulnerabilities to list.
        :return: {list} The found vulnerabilities' info
        """
        url = f"{self.api_root}/vulnerabilities"

        res = self.session.get(url)
        return self._paginate_results(
            url=url, method="GET", err_msg="Unable to list vulnerabilities", limit=limit
        )

    def get_vulnerability_information(self, vulnerability_id):
        """
        Get the info of a vulnerability by ID.
        :param vulnerability_id: {string} The identifier of the vulnerability.
        :return: {dict} The info of the vulnerability
        """
        url = f"{self.api_root}/vulnerabilities/{vulnerability_id}"
        res = self.session.get(url)
        self.validate_response(res)
        return res.json()

    def get_vulnerability_affected_assets(self, vulnerability_id):
        """
        Get the assets affected by the vulnerability.
        :param vulnerability_id: {string} The identifier of the vulnerability.
        :return: {list} The found assets ids
        """
        url = f"{self.api_root}/vulnerabilities/{vulnerability_id}/assets"
        res = self.session.get(url)
        self.validate_response(
            res,
            f"Unable to get assets affected by the vulnerability {vulnerability_id}",
        )

        return res.json().get("resources", [])

    def get_asset_vulnerability_solution(self, asset_id, vulnerability_id):
        """
        Returns the highest-superceding rollup solutions for a vulnerability on an asset. The solution selected will
        be the most recent and cost-effective means by which the vulnerability can be remediated.
        :param asset_id: {int} the identifier of the asset.
        :param vulnerability_id: {string} The identifier of the vulnerability.
        :return: {list} The found solutions details
        """
        url = f"{self.api_root}/assets/{asset_id}/vulnerabilities/{vulnerability_id}/solution"

        res = self.session.get(url)
        self.validate_response(
            res,
            f"Unable to list solutions for volunerability {vulnerability_id} of asset {asset_id}",
        )
        return res.json().get("resources", [])

    @staticmethod
    def construct_asset_info(asset):
        """
        Construct asset info data from full asset details
        :param asset: {dict} Asset details
        :return: {dict} Constructed and formatted asset info
        """
        asset_info = {
            "ip_address": asset.get("ip"),
            "hostname": asset.get("hostname"),
            "mac": asset.get("mac"),
            "os": asset.get("os"),
            "type": asset.get("type"),
            "risk_score": asset.get("riskScore"),
        }

        asset_info.update(
            {
                f"vulnerabilities_{k}": v
                for k, v in list(asset.get("vulnerabilities", {}).items())
            }
        )

        return asset_info

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            # Not a JSON - return content
            raise Rapid7ManagerError(f"{error_msg}: {error} {response.content}")
