# ============================================================================#
# title           :DevoManager.py
# description     :This Module contain all Devo Security operations functionality
# author          :amit.levizky@siemplify.co
# date            :19-09-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#
from __future__ import annotations
import json
import time
import hmac
import hashlib

from typing import Optional, Dict, List
from urllib.parse import urljoin

import requests
from requests import Session
from TIPCommon import filter_old_alerts
from .DevoParser import DevoParser
from .consts import (
    TEST_CONNECTIVITY_STRING,
    INTEGRATION_DISPLAY_NAME,
    API_ERROR,
    JSON_MODE,
    NOW,
    UNAUTHORIZED_ERROR,
    BAD_QUERY_ERROR,
    MINUTE,
    DEFAULT_MAX_ALERTS_PER_CYCLE,
)
from .datamodels import QueryResult, QueryObject
from .utils import remove_empty_kwargs
from .exceptions import (
    DevoManagerError,
    DevoManagerErrorValidationException,
    DevoManagerErrorUnauthorizedException,
    DevoManagerErrorBadQueryException,
)


ENDPOINTS = {"run_query": "/search/query"}

HEADERS = {"Content-Type": "application/json"}


class DevoManager:
    """
    Devo Manager
    """

    def __init__(
        self,
        api_url: str,
        api_token: str = None,
        api_key: str = None,
        api_secret: str = None,
        verify_ssl: bool = False,
        siemplify=None,
        force_test_connectivity: Optional[bool] = False,
    ):
        self._api_url: str = api_url[:-1] if api_url.endswith("/") else api_url
        self._session: Session = requests.Session()
        self._api_token = api_token
        self._api_key = api_key
        self._api_secret = api_secret
        self._session.verify = verify_ssl
        self._siemplify = siemplify
        self._parser = DevoParser()

        if force_test_connectivity:
            self.test_connectivity()

    def _get_full_url(self, url_key: str, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Key value arguments passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self._api_url, ENDPOINTS[url_key].format(**kwargs))

    @classmethod
    def validate_response(
        cls, response: requests.Response, error_msg: str = "An error occurred"
    ):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise DevoManagerError(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            if response.status_code == API_ERROR:
                raise DevoManagerErrorValidationException(
                    f"{error_msg}: {response.json().get('error', '')} {response.json().get('object', '')}"
                )

            if response.status_code == UNAUTHORIZED_ERROR:
                raise DevoManagerErrorUnauthorizedException(
                    f"{error_msg}: {response.json().get('error', {}).get('message', '')}"
                )

            if response.status_code == BAD_QUERY_ERROR:
                raise DevoManagerErrorBadQueryException(
                    f"{error_msg}: {response.json().get('object', '')}"
                )

            raise DevoManagerError(
                f"{error_msg}: {error} {response.json().get('message', '') or response.json().get('error', '')}"
            )

    def sign(self, timestamp_in_ms: str, body: dict = None):
        """
        Generate signature for API request.
        :param body: {dict} Request payload.
        :param timestamp_in_ms: {str} Current timestamp in milliseconds.
        :return: Signature in hex response.
        """
        text_to_hash = json.dumps(body)
        sign = hmac.new(
            self._api_secret.encode("utf-8"),
            (self._api_key + text_to_hash + timestamp_in_ms).encode("utf-8"),
            hashlib.sha256,
        )
        return sign.hexdigest()

    def get_headers(self, params: dict):
        """
        Create headers to the API calls
        :param params: {dict} Request payload
        """
        current_timestamp_in_ms = str(int(time.time()) * 1000)
        sign = self.sign(timestamp_in_ms=current_timestamp_in_ms, body=params)
        if sign:
            self._session.headers.update(
                {
                    "Content-Type": "application/json",
                    "x-logtrust-apikey": self._api_key,
                    "x-logtrust-timestamp": current_timestamp_in_ms,
                    "x-logtrust-sign": sign,
                }
            )

    def test_connectivity(self):
        """
        Test connectivity with Devo Security Auth API server
            raise Exception if failed to test connectivity
        """
        params = {
            "query": TEST_CONNECTIVITY_STRING,
            "from": int(time.time()) - 10 * MINUTE,
            "to": NOW,
            "mode": {"type": JSON_MODE},
            "limit": "1",
        }
        self.run_query(
            params=params,
            error_msg=f"Unable to test connectivity in {INTEGRATION_DISPLAY_NAME} service",
        )

    def run_query(self, params: Dict, error_msg: str) -> Dict:
        """
        Sends query request to Devo API service with the provided parameters.
        :param params: {Dict} Dictionary with query parameters. More details can be found here:
        https://docs.devo.com/confluence/ndt/latest/api-reference/query-api/running-queries-with-the-query-api#id-.RunningquerieswiththeQueryAPIvv7.1.0-Relativedates
        :param error_msg: {str} An error message in case of error.
        :return: {Dict} Response json object
        """
        request_url = self._get_full_url(url_key="run_query")
        if self._api_token:
            HEADERS.update({"Authorization": f"Bearer {self._api_token}"})
            self._session.headers = HEADERS
        else:
            self.get_headers(params)

        response = self._session.post(
            url=request_url, json=remove_empty_kwargs(**params)
        )
        self.validate_response(response, error_msg)
        return response.json()

    def run_advanced_query(self, params: Dict) -> QueryResult:
        """
        Execute an advanced query based on the provided parameters.
        :param params: {Dict} Dictionary with query parameters.
        :return:
        """
        query_result_json = self.run_query(
            params=params, error_msg="Unable to run advanced query"
        )
        return self._parser.build_query_result_model(query_result_json)

    def run_simple_query(self, params: Dict) -> QueryResult:
        """
        Execute an simple query based on the provided parameters.
        :param params: {Dict} Dictionary with query parameters.
        :return:
        """
        query_result_json = self.run_query(
            params=params, error_msg="Unable to run simple query"
        )
        return self._parser.build_query_result_model(query_result_json)

    def get_alerts(
        self, params: Dict, existing_ids=None, limit: int = DEFAULT_MAX_ALERTS_PER_CYCLE
    ) -> List[QueryObject]:
        """
        Execute an simple query based on the provided parameters.
        :param params: {Dict} Dictionary with query parameters.
        :param existing_ids: {[str]} List of existing ids to filter. If provided, ids_attribute_to_filter must also be provided
        :param limit: {int}  Max number of alerts to return
        :return: {[QueryObject]} List of filtered Alert objects
        """
        query_result_json = self.run_query(
            params=params, error_msg="Unable to get alerts"
        )
        query_result = self._parser.build_query_result_model(query_result_json)
        alerts = filter_old_alerts(
            siemplify=self._siemplify,
            alerts=query_result.objects if query_result.objects else [],
            existing_ids=existing_ids,
            id_key="alert_id",
        )
        return alerts[:limit]
