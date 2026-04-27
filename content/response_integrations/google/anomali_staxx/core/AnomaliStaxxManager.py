from __future__ import annotations
from .AnomaliStaxxParser import AnomaliStaxxParser
import requests
from urllib.parse import urljoin

from TIPCommon import filter_old_alerts
from .UtilsManager import validate_response

from .AnomaliStaxxConstants import (
    ENDPOINTS,
    HEADERS,
    QUERY_TYPE,
    SEVERITIES,
    VERY_HIGH_SEVERITY,
    CRITICAL_SEVERITY,
    INDICATORS_FETCH_SIZE,
)


class AnomaliStaxxManager:

    def __init__(self, api_root, username, password, verify_ssl=False, siemplify=None):
        """
        The method is used to init an object of Manager class
        :param api_root: Server address of the Anomali Staxx instance.
        :param username: Username of the Anomali Staxx account.
        :param password: Password of the Anomali Staxx account.
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL
        certificate for the connection.
        :param siemplify: Siemplify Connector Executor
        """
        self.api_root = api_root
        self.username = username
        self.password = password
        self.siemplify = siemplify
        self.parser = AnomaliStaxxParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.api_token = self.get_api_token()

    def get_api_token(self):
        """
        Make login request with valid credentials to retrieve api token
        :return: {str}
        """
        request_url = self._get_full_url("login")
        payload = {"username": self.username, "password": self.password}
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to login to AnomaliStaxx")
        return response.json().get("token_id")

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to the AnomaliStaxx.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("intelligence")
        payload = {
            "token": self.api_token,
            "query": "confidence>0",
            "type": QUERY_TYPE,
            "size": 1,
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to connect to AnomaliStaxx.")

    def get_indicators(
        self, existing_ids, start_time, lowest_severity, confidence, timezone_offset
    ):
        """
        Get indicators.
        :param existing_ids: {list} The list of existing ids.
        :param start_time: {str} The datetime from where to fetch indicators.
        :param lowest_severity: {str} Lowest severity that will be used to fetch
        indicators.
        :param confidence: {int} Lowest confidence that will be used to
        fetch indicators. Min: 0 Max: 100.
        :param timezone_offset: {str} UTC timezone offset
        :return: {list} The list of Indicators.
        """
        request_url = self._get_full_url("intelligence")
        query_string = self._build_query_string(
            [
                self._build_time_filter(start_time),
                self._build_severity_filter(lowest_severity),
                self._build_confidence_filter(confidence),
            ]
        )
        payload = {
            "token": self.api_token,
            "query": query_string,
            "type": QUERY_TYPE,
            "size": INDICATORS_FETCH_SIZE,
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to get Indicators")

        indicators = [
            self.parser.build_indicator_object(indicator_data, timezone_offset)
            for indicator_data in response.json()
        ]
        filtered_indicators = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=indicators,
            existing_ids=existing_ids,
            id_key="id",
        )
        return sorted(
            filtered_indicators,
            key=lambda indicator: indicator.naive_time_converted_to_aware,
        )

    def _build_time_filter(self, start_time):
        """
        Build time filter.
        :param start_time: {str} The datetime from where to fetch indicators.
        :return: {str} The query for time filter
        """
        return f"date_last>={start_time}"

    def _build_confidence_filter(self, confidence):
        """
        Build confidence filter.
        :param confidence: {int} Lowest confidence that will be used to
        fetch indicators. Min: 0 Max: 100.
        :return: {str} The query for certainty filter
        """
        return f"confidence>={max(0, min(confidence, 100))}"

    def _build_severity_filter(self, lowest_severity):
        """
        Build severity filter.
        :param lowest_severity: {str} Lowest severity that will be used to
        fetch indicators.
        :return: {str} The query for certainty filter
        """
        lowest_severity = (
            VERY_HIGH_SEVERITY
            if lowest_severity == CRITICAL_SEVERITY
            else lowest_severity
        )
        severities = (
            SEVERITIES[: SEVERITIES.index(lowest_severity)]
            if lowest_severity in SEVERITIES
            else []
        )
        return " and ".join([f"severity!={severity}" for severity in severities])

    def _build_query_string(self, queries):
        """
        Join filters.
        :param queries: {list} List of queries.
        :return: {str} Concated query
        """
        return " and ".join(list(filter(None, queries)))
