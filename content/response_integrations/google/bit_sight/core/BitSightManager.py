from __future__ import annotations
from urllib.parse import urljoin
import requests
from bit_sight.core.BitSightParser import BitSightParser
from bit_sight.core.utils import validate_response
from bit_sight.core.constants import ENDPOINTS, DEFAULT_MAX_LIMIT


class BitSightManager:
    def __init__(self, api_root, api_key, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        Args:
            api_root (str): BitSight API root
            api_key (str): BitSight API key
            verify_ssl (bool): Specifies if certificate that is configured on the api root should be validated
            siemplify_logger (object): Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = BitSightParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.auth = (api_key, None)

    def _get_full_url(self, url_id, **kwargs) -> str:
        """
        Get full url from url identifier.
        Args:
            url_id (str): The id of url
            **kwargs: Variables passed for string formatting

        Returns:
            (str): The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        Returns:
            (void)
        """
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response)

    def get_companies(self):
        """
        Get companies
        Returns:
            (list): List of Company objects
        """
        url = self._get_full_url("get_companies")
        response = self.session.get(url)
        validate_response(response)

        return self.parser.build_results(
            raw_json=response.json(),
            method="build_company_object",
            data_key="companies",
        )

    def get_company_details(self, company_id):
        """
        Get company details
        Args:
            company_id (str): The ID of the company
        Returns:
            (datamodels.Company): Company object
        """
        url = self._get_full_url("get_company_details", company_id=company_id)
        response = self.session.get(url)
        validate_response(response)

        return self.parser.build_company_object(raw_data=response.json())

    def get_company_vulnerabilities(self, company_id, high_confidence):
        """
        Get company vulnerabilities
        Args:
            company_id (str): The ID of the company
            high_confidence (bool): If true, will fetch only with high confidence

        Returns:
            (list): List of VulnerabilityStats objects
        """
        url = self._get_full_url("get_company_vulnerabilities", company_id=company_id)
        params = {"confidence": "HIGH"} if high_confidence else {}
        response = self.session.get(url, params=params)
        validate_response(response)

        statistics = self.parser.build_vulnerability_statistics(
            raw_data=response.json()
        )
        return sorted(statistics, key=lambda stat: (stat.end_date, stat.start_date))

    def get_alerts(self, start_timestamp, severity_filter, limit):
        """
        Get Alerts
        Args:
            start_timestamp (str): Start time to fetch alerts from
            severity_filter (str): Severity values to use for filtering
            limit (int): Limit for results

        Returns:
            (list): List of Alert objects
        """
        url = self._get_full_url("get_alerts")
        params = {
            "sort": "alert_date",
            "alert_date_gte": start_timestamp,
            "expand": "details",
            "severity": severity_filter,
            "limit": max(limit, DEFAULT_MAX_LIMIT),
        }
        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_results(
            raw_json=response.json(), method="build_alert_object"
        )

    def get_findings(self, start_timestamp, company_guid, family_filter):
        """
        Get Findings
        Args:
            start_timestamp (str): Start time to fetch findings from
            company_guid (str): Company id to fetch from
            family_filter (str): Finding type filter

        Returns:
            (list): List of Finding objects
        """
        url = self._get_full_url("get_findings", company_id=company_guid)
        params = {
            "affects_rating": "true",
            "details.infection.family": family_filter,
            "sort": "-last_seen",
            "last_seen_gte": start_timestamp,
        }
        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_results(
            raw_json=response.json(), method="build_finding_object"
        )

    def get_company_highlights(
        self, company_id, start_time=None, end_time=None, limit=None
    ):
        """
        Get company highlights
        Args:
            company_id (str): ID of the company
            start_time (str): Start time for the results
            end_time (str): End time for the results
            limit (int): Limit for results

        Returns:
            (list): List of Highlight objects
        """
        url = self._get_full_url("get_company_highlights")
        params = {"company": company_id, "start": start_time, "end": end_time}

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_results(
            response.json(), "build_highlight_object", pure_data=True, limit=limit
        )
