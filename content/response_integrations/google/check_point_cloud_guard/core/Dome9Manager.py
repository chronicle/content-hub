# ============================================================================#
# title           :Dome9Manager.py
# description     :This Module contain all Dome 9 operations functionality
# author          :avital@siemplify.co
# date            :09-09-2020
# python_version  :3.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests

from .Dome9Parser import Dome9Parser
from . import datamodels
from . import exceptions
from . import consts


class Dome9Manager:
    """
    Dome9 Manager
    """

    def __init__(self, api_key_id, api_key_secret, verify_ssl=False):
        self.session = requests.Session()
        self.session.auth = (api_key_id, api_key_secret)
        self.session.verify = verify_ssl
        self.api_root = consts.API_ROOT
        self.parser = Dome9Parser()

    def test_connectivity(self):
        """
        Get a token (equals to login)
        """
        url = f"{self.api_root}/Settings"
        response = self.session.get(url)
        self.validate_response(
            response, "Unable to connect to the Check Point Cloud Guard server"
        )
        return True

    def get_findings(
        self,
        limit=None,
        severities=None,
        start_time=None,
        sort_by="createdTime",
        asc=True,
        existing_ids=None,
    ):
        """
        Get findings by various filters
        :param limit: {int} Max amount of findings to fetch
        :param severities: {list} List of severities to fetch
        :param start_time: {datetime.datetime} Search for findings that were created after given start time
        :param sort_by: {str} Field name to sort the results by
        :param asc: {bool} If true, results will be ascending, otherwise descending
        :param existing_ids: {list} List of already seen IDS to filter out of the results
        :return: {list} List of found Findings
        """
        url = f"{self.api_root}/Compliance/Finding/search"
        payload = {
            "pageSize": min(consts.PAGE_SIZE, limit) if limit else consts.PAGE_SIZE,
            "sorting": {
                "fieldName": sort_by,
                "direction": consts.ASC if asc else consts.DESC,
            },
            "filter": {},
        }

        if start_time:
            payload["filter"]["creationTime"] = {
                "from": start_time.strftime(consts.TIME_FORMAT)
            }

        if severities:
            payload["filter"]["fields"] = []

            for severity in severities:
                if severity not in datamodels.SEVERITIES:
                    raise exceptions.Dome9ValidationError(
                        f"{severity} is invalid value for severity field. Valid values: {', '.join(consts.SEVERITIES.keys())}"
                    )

                payload["filter"]["fields"].append(
                    {"name": "severity", "value": severity}
                )

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Unable to get findings.")

        raw_findings = response.json().get("findings", [])
        if existing_ids:
            filtered_findings = [
                finding
                for finding in raw_findings
                if finding.get("id") not in existing_ids
            ]
        else:
            filtered_findings = raw_findings
        parsed_findings = [
            self.parser.build_siemplify_finding_obj(finding)
            for finding in filtered_findings
        ]

        while response.json().get("findings", []):
            if limit and len(parsed_findings) >= limit:
                break

            payload.update({"searchAfter": response.json().get("searchAfter")})

            response = self.session.post(url, json=payload)
            self.validate_response(response, "Unable to get findings.")

            raw_findings = response.json().get("findings", [])
            if existing_ids:
                filtered_findings = [
                    finding
                    for finding in raw_findings
                    if finding.get("id") not in existing_ids
                ]
            else:
                filtered_findings = raw_findings
            parsed_findings.extend(
                [
                    self.parser.build_siemplify_finding_obj(finding)
                    for finding in filtered_findings
                ]
            )

        return parsed_findings[:limit] if limit else parsed_findings

    def get_findings_page(
        self,
        page_size=100,
        severities=None,
        start_time=None,
        sort_by="createdTime",
        asc=True,
        search_after=None,
    ):
        """
        Get findings single page by various filters
        :param page_size: {int} Max amount of findings to fetch in a single page
        :param severities: {list} List of severities to fetch
        :param start_time: {datetime.datetime} Search for findings that were created after given start time
        :param sort_by: {str} Field name to sort the results by
        :param asc: {bool} If true, results will be ascending, otherwise descending
        :return: {tuple} (searchAfter, Findings}
        """
        url = f"{self.api_root}/Compliance/Finding/search"
        payload = {
            "pageSize": page_size,
            "sorting": {
                "fieldName": sort_by,
                "direction": consts.ASC if asc else consts.DESC,
            },
            "filter": {},
        }

        if start_time:
            payload["filter"]["creationTime"] = {
                "from": start_time.strftime(consts.TIME_FORMAT)
            }

        if severities:
            payload["filter"]["fields"] = []

            for severity in severities:
                if severity not in datamodels.SEVERITIES:
                    raise exceptions.Dome9ValidationError(
                        f"{severity} is invalid value for severity field. Valid values: {', '.join(consts.SEVERITIES.keys())}"
                    )

                payload["filter"]["fields"].append(
                    {"name": "severity", "value": severity}
                )

        if search_after:
            payload.update({"searchAfter": search_after})

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Unable to get findings page.")

        raw_findings = response.json().get("findings", [])
        parsed_findings = [
            self.parser.build_siemplify_finding_obj(finding) for finding in raw_findings
        ]

        return response.json().get("searchAfter"), parsed_findings

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {unicode} The error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise exceptions.Dome9ManagerError(
                f"{error_msg}: {error} {response.content}"
            )
