# ============================================================================#
# title           :TruSTARManager.py
# description     :This Module contain all TruSTAR operations functionality
# author          :amit.levizky@siemplify.co
# date            :13-04-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#

from __future__ import annotations
from typing import List, Optional, Dict
from urllib.parse import urljoin

import requests

from .TruSTARTransformationLayer import TruSTARTransformationLayer
from .consts import (
    UNAUTHORIZED_ERROR,
    INTEGRATION_NAME,
    DEFAULT_SIZE_PAGE,
    FIRST_PAGE_NUMBER,
)
from .datamodels import (
    Enclave,
    RelatedIndicator,
    IndicatorMetadata,
    IndicatorSummary,
    RelatedReport,
    ReportDetails,
    ReportTag,
)

# ============================= IMPORTS ===================================== #
from .exceptions import TruSTARException, TruSTARUnauthorizedException

ENDPOINTS = {
    "get_token": "/oauth/token",
    "ping": "api/1.3/version",
    "list-enclaves": "api/1.3/enclaves",
    "get-related-indicators": "api/1.3/indicators/related",
    "get_metadata_info": "api/1.3/indicators/metadata",
    "get_indicator_summary": "api/1.3/indicators/summaries",
    "get-correlated-reports": "api/1.3/reports/correlated",
    "get-report-details": "api/1.3/reports/{report_id}",
    "get-report-tags": "api/1.3/reports/{report_id}/tags",
}


class TruSTARManager:
    def __init__(
        self, api_root: str, api_key: str, api_secret: str, verify_ssl: bool = True
    ):
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_secret = api_secret
        self.api_key = api_key

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.auth = (api_key, api_secret)
        self.session.headers["Authorization"] = f"Bearer {self._get_token()}"

        self.parser = TruSTARTransformationLayer()

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_key].format(**kwargs))

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                if error.response.status_code == UNAUTHORIZED_ERROR:
                    raise TruSTARUnauthorizedException(
                        "Unauthorized error. Please check your credentials."
                    )

                # Not a JSON - return content
                raise TruSTARException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise TruSTARException(
                f"{error_msg}: {error} {response.json().get('message')}"
            )

    def _get_token(self) -> str:
        """
        Get token from TruSTAR service
        return: {str} If the provided credentials are valid, An access token will be returned, else,
        error will be raised.
        raise: (TruSTARException, TruSTARUnauthorizedException)
        """
        payload = {"grant_type": "client_credentials"}
        request_url = self._get_full_url("get_token")
        response = self.session.post(request_url, data=payload)
        self.validate_response(response)
        access_token = response.json().get("access_token")

        if access_token:
            # Basic auth is not needed anymore.
            self.session.auth = None
            # Return Token
            return access_token

        raise TruSTARException("Error: No access token received.")

    def test_connectivity(self):
        """
        Test connectivity to the TruSTAR with parameters provided at the integration configuration page on the
        Marketplace tab.
        """
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        self.validate_response(
            response, f"Unable to connect to {INTEGRATION_NAME} service"
        )

    def get_metadata_info(
        self, entities_identifiers: List[Dict], enclaves_ids: List[str] = None
    ) -> List[IndicatorMetadata]:
        """
        Get indicators metadata information.
        :param entities_identifiers: {List[Dict]} list dictionaries of entities ids. for example: [{"value": "1.2.3.4"}]
        :param enclaves_ids: {List[str]} List of enclaves. if this parameter is not None or [], only indicators that
        related to those enclaves will be returned.
        :return: {List[IndicatorMetadata]} List of indicators metadata information.
        """
        request_url = self._get_full_url(url_key="get_metadata_info")
        params = {}
        if enclaves_ids:
            params["enclaveIds"] = ",".join(enclaves_ids)

        response = self.session.post(
            url=request_url, json=entities_identifiers, params=params
        )
        self.validate_response(
            response,
            f"Unable to get indicators metadata from {INTEGRATION_NAME} service",
        )

        return self.parser.build_indicator_meta_objects(response)

    def get_indicators_summary(
        self,
        indicators: List[str],
        enclaves_ids: List[str],
        page_size: int = DEFAULT_SIZE_PAGE,
        starting_page: int = FIRST_PAGE_NUMBER,
    ) -> List[IndicatorSummary]:
        """
        Get indicators summary from third party resources.
        :param indicators: {List[str]} List of indicators (entity) ids.
        :param enclaves_ids: {List[str]} List of enclaves ids.
        :param page_size: Page size for pagination.
        :param starting_page: The first page of the response, part of pagination.
        :return: {List[IndicatorSummary]} List of indicator summary data models.
        """
        request_url = self._get_full_url(url_key="get_indicator_summary")
        params = {"pageNumber": starting_page, "pageSize": page_size}

        if enclaves_ids:
            params["enclaveIds"] = ",".join(enclaves_ids)

        summaries = []
        while True:
            response = self.session.post(
                url=request_url, json=indicators, params=params
            )
            self.validate_response(
                response,
                f"Unable to get indicators summary from {INTEGRATION_NAME} service",
            )
            summary_response = self.parser.build_indicator_summary_response(response)
            summaries.extend(summary_response.summaries)

            if not summary_response.hasNext:
                break

            params["pageNumber"] = params.get(
                "pageNumber", summary_response.total_pages
            )

        return summaries

    def list_enclaves(self) -> List[Enclave]:
        """
        List available enclaves
        :return: {[Enclaves]} List of Enclaves data models
        """
        request_url = self._get_full_url("list-enclaves")
        response = self.session.get(request_url)
        self.validate_response(response, f"Unable to list enclaves")
        return self.parser.build_enclaves_obj_list(response.json())

    def get_related_iocs(
        self, indicators: List[str], limit: int, enclave_ids: Optional[List[str]] = None
    ) -> List[RelatedIndicator]:
        """
        Get related IOCs
        :param indicators: {[str]} List of indicators to search related IOCs for
        :param limit: {int} Max results to return
        :param enclave_ids:  {[str]} List of enclave IDS to use. If nothing is provided, filter will not be applied.
        :return: {[RelatedIndicator]} List of RelatedIndicator data models
        """
        request_url = self._get_full_url("get-related-indicators")
        params = {"indicators": ", ".join(indicators), "pageSize": limit}
        if enclave_ids:
            params.update({"enclaveIds": ", ".join(enclave_ids)})
        response = self.session.get(request_url, params=params)
        self.validate_response(response, f"Unable to get related indicators")
        return self.parser.build_related_indicator_obj_list(response.json())

    def get_correlated_reports(
        self, indicators: List[str], limit: int, enclave_ids: Optional[List[str]]
    ) -> List[RelatedReport]:
        """
        Get related reports
        :param indicators: {[str]} List of indicators to search reports for
        :param limit: {int} Max reports to return
        :param enclave_ids: {[str]} List of enclave IDS to use. If nothing is provided, filter will not be applied.
        :return: {[RelatedReport]} List of RelatedReport data models
        """
        request_url = self._get_full_url("get-correlated-reports")
        params = {"indicators": ", ".join(indicators), "pageSize": limit}
        if enclave_ids:
            params.update({"enclaveIds": ", ".join(enclave_ids)})
        response = self.session.get(request_url, params=params)
        self.validate_response(response, f"Unable to get related reports")
        return self.parser.build_related_report_obj_list(response.json())

    def get_report_details(self, report_id: str) -> ReportDetails:
        """
        Get report details
        :param report_id: {str} Report tracking id
        :return: {ReportDetails} ReportDetails data model
        """
        request_url = self._get_full_url("get-report-details", report_id=report_id)
        response = self.session.get(request_url)
        self.validate_response(
            response, f"Unable to get details for report with id: {report_id}"
        )
        return self.parser.build_report_details_obj(response.json())

    def get_report_tags(self, report_id: str) -> ReportTag:
        """
        Get report tags
        :param report_id: {str} Report tracking id to get tags for
        :return: {[ReportTag]} List of ReportTag data model
        """
        request_url = self._get_full_url("get-report-tags", report_id=report_id)
        response = self.session.get(request_url)
        self.validate_response(
            response, f"Unable to get tags for report with id: {report_id}"
        )
        return self.parser.build_report_tags_obj_list(response.json())
