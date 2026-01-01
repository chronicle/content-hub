from __future__ import annotations

import copy
from urllib.parse import urljoin

import requests

from .constants import DEFAULT_COMMENTS_COUNT, DEFAULT_NEWS_COUNT
from .exceptions import (
    PulsediveBadRequest,
    PulsediveException,
    PulsediveLimitReachedException,
    PulsediveNotFoundException,
    UnauthorizedException,
)
from .PulsediveParser import PulsediveParser

API_ENDPOINTS = {
    "info": "/api/info.php",
    "search": "/api/search.php",
    "analyze": "/api/analyze.php",
    "submit": "/api/submit.php",
}

REQUEST_PARAM = {"key": "", "pretty": "1"}  # Pretty-print the results

# Additional Options but seem unnessessary
#    "schema": "0",  # Returns Indicators and attribute schema for displaying user-friendly labels.
#                      (Like "Protocol" instead of "protocol")
#    "sanitize": "0",  # HTLM-Friendly Output
#    "historical": "0"  # Returns historical property data or latest based on value

TEST_REQUEST_PARAM = {
    "key": "",
    "type": ["all"],
    "risk": ["all"],
    "retired": "true",
    "attribute": ["http", "443"],
    "property": ["content-type:text/html"],
    "threat": ["zeus", "banjori"],
    "feed": ["zeus_bad_ips"],
    "sanitize": 1,
    "pretty": 0,
    "limit": "hundred",
}

PULSEDIVE_PROBLEM = 500
RATE_LIMIT_STATUS_CODE = 429
NOT_FOUND_STATUS_CODE = 404
UNAUTHORIZED_STATUS_CODE = 401
BAD_REQUEST = 400


# =====================================
#              CLASSES                #
# =====================================


class PulsediveManager:
    """The method is used to init an object of PulsediveManager class
    :param api_key: API key
    :param verify_ssl: Enable (True) or disable (False). If enabled, verify SSL certificate for the connection
    """

    def __init__(self, api_root, api_key, verify_ssl=False):
        self.api_root = api_root
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = verify_ssl
        REQUEST_PARAM.update({"key": api_key})
        self.parser = PulsediveParser()

    def test_connectivity(self):
        """Ping to server to be sure that connected
        :return: {bool}
        """
        request_url = self._get_full_url("search")
        params = copy.deepcopy(TEST_REQUEST_PARAM)
        params["key"] = self.api_key

        res = self.session.get(request_url, json=params)
        self.validate_response(res)

        return True

    def get_indicator_data(
        self,
        indicator_id=None,
        indicator=None,
        get_links=False,
        get_properties=False,
        schema=False,
        historical=False,
        retrieve_comments=False,
        comment_limit=DEFAULT_COMMENTS_COUNT,
    ):
        request_url = self._get_full_url("info")
        params = copy.deepcopy(REQUEST_PARAM)
        params["schema"] = int(schema)
        comments = None

        if indicator is not None:
            params["indicator"] = indicator
            entity = indicator
        elif indicator_id is not None:
            params["iid"] = indicator_id
            entity = indicator_id
        else:
            raise PulsediveException(
                "Indicator ID or Indicator required and none were provided",
            )

        params["historical"] = int(historical)

        indicator_data = self.session.get(request_url, params=params)
        self.validate_response(indicator_data)

        # Not Implemented
        if get_links:
            additional_data_params = copy.deepcopy(params)
            additional_data_params["get"] = "links"
            indicator_links = self.session.get(request_url, params=params)
            self.validate_response(indicator_links)

        # Not Implemented
        if get_properties:
            additional_data_params = copy.deepcopy(params)
            additional_data_params["get"] = "properties"
            properties_data = self.session.get(request_url, params=params)
            self.validate_response(properties_data)

        if retrieve_comments:
            comments = self.get_comments(indicator_data.json(), limit=comment_limit)

        return self.parser.build_indicator_object(
            indicator_data.json(),
            entity_type="url",
            comments=comments,
        )

    def get_comments(self, response, limit):
        return self.parser.build_comment_results(response, limit)

    def scan_indicator(self, indicator=None, base64_data=None, scan_type="0"):
        """Retrieve a report on a given url/file
        :param indicator: {string} The file of the url,
        :return: {dict}
        """
        params = copy.deepcopy(REQUEST_PARAM)
        request_url = self._get_full_url("analyze")

        if indicator is not None:
            params["value"] = indicator
        elif base64_data is not None:
            params["ioc"] = base64_data
        else:
            raise PulsediveException(
                "Indicator or Indicator base64 required and none were provided",
            )

        params["probe"] = scan_type

        response = self.session.post(request_url, params=params)
        self.validate_response(response)

        return response.json().get("qid")

    # Don't think this is implemented
    def parse_scan_data(
        self,
        scan_results,
        retrieve_comments=False,
        comment_limit=DEFAULT_COMMENTS_COUNT,
    ):
        # comments = None
        # if retrieve_comments:
        #     comments = self.get_comments(scan_results, limit=comment_limit)
        #
        # return self.parser.build_indicator_object(scan_results.json().get('data'), entity_type='url', entity=entity,
        #                                           comments=comments)

        raise NotImplementedError

    def get_scan_data(self, scan_qid):
        """Retrieve a report on a given url/file
        :param resource: {string} The file of the url,
        :param resource_type: {string} indicate weather resource is url or file, can be FILEHASH_TYPE or URL_TYPE
        :return: {dict}
        """
        params = copy.deepcopy(REQUEST_PARAM)
        params["qid"] = scan_qid
        request_url = self._get_full_url("analyze")

        response = self.session.post(request_url, params=params)
        self.validate_response(response)

        return response

    def is_scan_report_ready(self, scan_qid):
        """Check if scan report is still queued or ready
        :param task_id: {string} scan id
        :param resource_type: {string} hash/url
        :return: {dict} resource report of none
        """
        scan_results = self.get_scan_data(scan_qid)

        return self.parser.get_analysis_status(scan_results.json())

    def get_scan_indicator_data(
        self,
        indicator,
        retrieve_comments=False,
        comment_limit=DEFAULT_COMMENTS_COUNT,
        completed_scan_id="",
    ):
        indicator_scan_data = self.get_scan_data(completed_scan_id)

        if retrieve_comments:
            comments = self.get_comments(
                indicator_scan_data.json().get("data"),
                limit=comment_limit,
            )

        return self.parser.build_indicator_object(
            indicator_scan_data.json().get("data"),
            entity_type="url",
            comments=comments,
        )

    def submit_indicator(
        self,
        indicator=None,
        actions="submit",
        indicator_type="indicator",
        probe=0,
        indicator_risk="unknown",
        indicator_threat=[],
        stamp_seen=None,
        indicator_activate=None,
        indicator_comment="Submitted by Siemplify",
        indicator_attributes=None,
    ):
        # Actions: submit, analyze, retire, activate
        params = copy.deepcopy(REQUEST_PARAM)
        request_url = self._get_full_url("submit")
        submission_data = {
            "value": indicator,
            "type": indicator_type,
            "action": actions,
            "risk": indicator_risk,
            "threat": indicator_threat,
            "attributes": {},
            "probe": probe,
            "stamp_seen": stamp_seen,
            "activate": indicator_activate,
            "comment": indicator_comment,
        }

        params["action"] = actions
        params["type"] = indicator_type
        params["data"] = submission_data

        response = self.session.post(request_url, params=params)
        self.validate_response(response)  # will return qid

        return response.json().get("qid")

    def retire_indicator(self, indicator, comment="Retired indicator by Siemplify"):
        params = copy.deepcopy(REQUEST_PARAM)
        request_url = self._get_full_url("submit")

        params.update(
            {
                "action": "retire",
                "type": "indicator",
                "data": {"value": indicator, "comment": comment},
            },
        )

        response = self.session.post(request_url, params=params)
        self.validate_response(response)

        return response.json().get("qid")

    def activate_indicator(self, indicator, comment="Retired indicator by Siemplify"):
        params = copy.deepcopy(REQUEST_PARAM)
        request_url = self._get_full_url("submit")

        params.update(
            {"action": "activate", "type": "indicator", "data": {"iid": indicator}},
        )

        response = self.session.post(request_url, params=params)
        self.validate_response(response)

        return response.json().get("qid")

    def get_threats(
        self,
        threat_id=None,
        threat_name=None,
        get_linked_indicators=False,
        retrieve_comments=False,
        comment_limit=DEFAULT_COMMENTS_COUNT,
        split_risk=False,
        news_limit=DEFAULT_NEWS_COUNT,
    ):
        request_url = self._get_full_url("info")
        params = copy.deepcopy(REQUEST_PARAM)
        comments = None

        if threat_name:
            params["threat"] = threat_name
        elif threat_id:
            params["tid"] = threat_id
        else:
            raise PulsediveException(
                "Threat ID or threat name required and none were provided",
            )

        if split_risk:
            params["splitrisk"] = int(split_risk)

        threat_data = self.session.get(request_url, params=params)
        self.validate_response(threat_data)

        # Not Implemented
        if get_linked_indicators:
            linked_data_params = copy.deepcopy(params)
            linked_indicators = self.get_linked_indicators(linked_data_params)

        if retrieve_comments:
            comments = self.get_comments(threat_data.json(), limit=comment_limit)

        news = self.get_news(threat_data.json(), limit=news_limit)

        return self.parser.build_threat_object(
            threat_data.json(),
            comments=comments,
            news=news,
        )

    def get_news(self, response, limit):
        return self.parser.build_news_results(response, limit)

    # Not Implemented
    def get_linked_indicators(self, link_indicators_params):
        # Not Implemented

        # link_indicators_params["get"] = "links"
        # indicator_links = self.session.get(request_url, params=link_indicators_params)
        # self.validate_response(indicator_links)
        # #return self.parser.build_threat_links_object(indicator_links.json())
        # return indicator_links.json()

        raise NotImplementedError

    def _get_full_url(self, url_id, **kwargs):
        """Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, API_ENDPOINTS[url_id].format(**kwargs))

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if response.status_code == RATE_LIMIT_STATUS_CODE:
                raise PulsediveLimitReachedException(error)
            if response.status_code == NOT_FOUND_STATUS_CODE:
                raise PulsediveNotFoundException(response.json().get("error"))
            if response.status_code == UNAUTHORIZED_STATUS_CODE:
                raise UnauthorizedException(error)
            if response.status_code == BAD_REQUEST:
                raise PulsediveBadRequest(error)
            raise Exception(f"{error_msg}: {error} {error.response.content}")
        return True
