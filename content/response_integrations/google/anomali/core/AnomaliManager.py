from __future__ import annotations
import requests
from requests.models import PreparedRequest
from .exceptions import (
    AnomaliManagerException,
    AnomaliUnauthorizedException,
    AnomaliBadRequestException,
    AnomaliPermissionException,
    AnomaliNotFoundException,
)
from .AnomaliParser import AnomaliParser
from urllib.parse import urljoin
from .utils import LOGGER


OR = "OR"
THREAT_INFO_RESOURCE = "intelligence"
ENDPOINTS_MAPPER = {
    "Threat Bulletins": "tipreport",
    "Actors": "actor",
    "Attack Patterns": "attackpattern",
    "Campaigns": "campaign",
    "Courses Of Action": "courseofaction",
    "Identities": "identity",
    "Incidents": "incident",
    "Infrastructure": "infrustructure",
    "Intrusion Sets": "intrusionset",
    "Malware": "malware",
    "Signatures": "signature",
    "Tools": "tool",
    "TTPs": "ttp",
    "Vulnerabilities": "vulnerability",
}
HEADERS = {
    "ACCEPT": "application/json, text/html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36",
}
LIMIT = 1000

API_ENDPOINTS = {
    "ping": f"v2/{THREAT_INFO_RESOURCE}",
    "threats": f"v2/{THREAT_INFO_RESOURCE}",
    "get_indicators": f"v2/{THREAT_INFO_RESOURCE}",
    "get_related_associations": "v1/{association_type}/associated_with_intelligence",
    "get_association_details": "v1/{association_type}/{association_id}",
}


class AnomaliManager:
    def __init__(
        self, api_root, username, api_key, force_check_connectivity=False, logger=None
    ):
        self.url = self._get_adjusted_root_url(api_root)
        self.username = username
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(HEADERS)
        self.parser = AnomaliParser()
        self.logger = LOGGER(logger)

        self.set_auth_header()

        if force_check_connectivity:
            self.test_connectivity()

    @staticmethod
    def _get_adjusted_root_url(api_root):
        """
        Get adjusted url
        :param api_root: {str} Provided api root
        :return: {str} The adjusted url
        """
        return api_root if api_root[-1] == r"/" else f"{api_root}/"

    def set_auth_header(self):
        """
        Set authorization header to request session
        """
        self.session.headers.update({
            "Authorization": f"apikey {self.username}:{self.api_key}"
        })

    @staticmethod
    def _get_max_default_limit_param():
        """
        Get max default limit for items
        """
        return {"limit": LIMIT}

    def _get_full_url(self, url_id, default_limit=True, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param default_limit: {bool} default limit
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        full_url = urljoin(self.url, API_ENDPOINTS[url_id].format(**kwargs))
        rest_query_params = self._get_max_default_limit_param() if default_limit else {}
        request = PreparedRequest()
        request.prepare_url(full_url, rest_query_params)
        return request.url

    def _get_next_page_url(self, next_cursor_url):
        """
        Get next page url
        :param next_cursor_url: {str} The url to send request to
        :return: {str} Full url for next page
        """
        return urljoin(self.url, "/".join(next_cursor_url.split("/")[2:]))

    def _paginate_results(self, *, full_url, build_with, params=None, limit=None):
        """
        Paginate the results
        :param full_url: {str} The url to send request to
        :param params: {dict}
        :param limit: {int} The limit of the results to fetch
        :return: {list} List of results
        """
        results, next_cursor_url, response = [], None, None

        while True:
            if response:
                if (not next_cursor_url) or (limit and len(results) > limit):
                    break

                full_url = self._get_next_page_url(next_cursor_url)

            response = self.session.get(full_url, params=params)
            self.validate_response(response)

            next_cursor_url = self.parser.get_next_cursor(response.json())

            results.extend(
                self.parser.build_results(
                    response.json(), method=build_with, limit=limit
                )
            )

        return results

    def test_connectivity(self):
        """
        Test connectivity with Anomali ThreatStream
        """
        response = self.session.get(
            self._get_full_url("ping", default_limit=False), params={"limit": 1}
        )
        self.validate_response(response)

    def get_threat_info(self, entity, limit=None):
        """
        Get threat information about a given entity with pagination
        :param entity: {str} ip or host to investigate
        :param limit: {int} if no limit specified, in the request will be used the default max limit
        :return: {json} The threat report
        """
        return self._paginate_results(
            full_url=self._get_full_url("threats", default_limit=False),
            params={"value__exact": entity},
            build_with="build_threat",
            limit=limit,
        )

    def get_indicators(self, entities):
        """
        Get Indicators for provided entities
        :param entities: {list}
        :return: {list} The Reports
        """
        params = {"q": f" {OR} ".join([f"value={entity}" for entity in entities])}

        response = self.session.get(self._get_full_url("get_indicators"), params=params)
        self.validate_response(response)

        return self.parser.build_results(response.json(), "build_indicator_object")

    def get_associations(self, association_type, indicator_ids, limit=None):
        """
        Get Associations for provided indicators
        :param association_type: {str} api endpoint part
        :param indicator_ids: {list} Indicator Ids
        :param limit: {int} related properties limit
        :return: {list} list of {Associations} models
        """
        params = {
            "ids": ",".join([str(indicator_id) for indicator_id in indicator_ids])
        }

        associations = self._paginate_results(
            full_url=self._get_full_url(
                "get_related_associations", association_type=association_type
            ),
            params=params,
            build_with="build_association_object",
        )

        sorted_associations = sorted(
            associations,
            key=lambda association: getattr(association, "modified_ts"),
            reverse=True,
        )
        return sorted_associations[:limit] if limit is not None else sorted_associations

    def get_association_details(self, association_type, association_id):
        """
        Get Association details
        :param association_type: {str} api endpoint part
        :param association_id: {str} Association ID
        :return: {list} list of {Association} models
        """
        params = {"skip_associations": True, "skip_intelligence": True}
        url = self._get_full_url(
            "get_association_details",
            association_type=association_type,
            association_id=association_id,
        )
        response = self.session.get(url, params=params)
        self.validate_response(response)

        return self.parser.build_association_details_object(response.json())

    @classmethod
    def get_api_error_message(cls, exception):
        """
        Get API error message
        :param exception: {Exception} The api error
        :return: {str} error message
        """
        try:
            if not exception.response.json().get("error"):
                return exception.response.json().get("message")

            return exception.response.json().get("error")
        except:
            return exception.response.content.decode()

    @classmethod
    def validate_response(cls, response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            error_message = cls.get_api_error_message(error)

            if response.status_code == 401:
                raise AnomaliUnauthorizedException(
                    "Access Denied. Check API Credentials."
                )
            if response.status_code == 400:
                raise AnomaliBadRequestException(error_message)
            if response.status_code == 403:
                raise AnomaliPermissionException(error_message)
            if response.status_code == 404:
                raise AnomaliNotFoundException(error_message)

            raise AnomaliManagerException(f"{error_msg}: {error} {response.content}")
