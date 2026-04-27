# ============================================================================#
# title           :DigitalShadowsManager.py
# description     :This Module contain all DigitalShadows operations functionality
# author          :harutyun.hovhannisyan@siemplify.co
# date            :16-03-2020
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================ IMPORTS ====================================== #

from __future__ import annotations
import requests
from urllib.parse import urljoin
from .DigitalShadowsParser import DigitalShadowsParser
import base64


from .DigitalShadowsConstants import (
    API_URL,
    HEADERS,
    API_ENDPOINTS,
    SEARCH_BODY,
    ALERTS_FETCH_SIZE,
    ALERTS_LIMIT,
    SEVERITIES,
)

from .UtilsManager import filter_old_alerts


# ============================== CLASSES ==================================== #
class EntityTypes:
    DOMAIN_WHOIS = "DOMAIN_WHOIS"
    WEBROOT_IP = "WEBROOT_IP"
    CYLANCE_FILE_HASH = "CYLANCE_FILE_HASH"
    WEBROOT_FILE_HASH = "WEBROOT_FILE_HASH"
    EXPLOIT = "EXPLOIT"
    VULNERABILITY = "VULNERABILITY"


class DigitalShadowsException(Exception):
    """
    General Exception for  Digital Shadows manager
    """

    pass


class DigitalShadowsResponseError(Exception):
    """
    Response Error Exception for Digital Shadows manager
    """

    pass


class DigitalShadowsManager:

    def __init__(self, api_key, api_secret, verify_ssl=False, siemplify_logger=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.siemplify_logger = siemplify_logger
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = verify_ssl
        auth = f"{self.api_key}:{self.api_secret}"
        auth = base64.b64encode(auth.encode("utf-8")).decode("utf-8")
        self.session.headers.update({"Authorization": f"Basic {auth}"})
        self.digitalShadowsParser = DigitalShadowsParser(EntityTypes)
        self.test_connectivity()

    def test_connectivity(self):
        """
        Test the connectivity using sample GET request to DigitalShadows server
        """
        self.search("www.google.com", [EntityTypes.DOMAIN_WHOIS])
        return True

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(API_URL, API_ENDPOINTS[url_id].format(**kwargs))

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise DigitalShadowsResponseError(
                    f"{error_msg}: {error} - {response.content}"
                )
            raise DigitalShadowsResponseError(
                f"{error_msg}: {response.json().get('message', response.content)}"
            )

        return True

    def search(self, query, types):
        """
        Do a search based on a given query and entity types
        :param query: {str} The query that need to be run
        :param types: {list} List of EntityTypes fields
        :return: {list} List of results
        """
        ret = []
        url = urljoin(API_URL, API_ENDPOINTS["SEARCH_FIND"])
        body = SEARCH_BODY.copy()
        body["query"] = body["query"].format(query)
        body["filter"]["types"] = types
        response = self.session.request("POST", url, json=body)
        self.validate_response(response)

        ret.extend(response.json().get("content", []))
        total = response.json().get("total", 0)

        while len(ret) < total:
            body["pagination"]["offset"] += 1
            response = self.session.request("POST", url, json=body)
            self.validate_response(response)
            ret.extend(response.json().get("content", []))

        return ret

    def enrich_hash(self, file_hash):
        """
        Enrich the hash
        :param file_hash: The hash value to enrich
        :return: Enriched hash object
        """
        hash_data_entities = self.search(
            file_hash, [EntityTypes.CYLANCE_FILE_HASH, EntityTypes.WEBROOT_FILE_HASH]
        )

        if not hash_data_entities:
            raise DigitalShadowsException(f"Can't retrieve data for hash {file_hash}")

        hash_obj = self.digitalShadowsParser.build_hash_object(
            hash_data_entities, file_hash
        )
        if not hash_obj:
            raise DigitalShadowsException(f"Can't retrieve data for hash {file_hash}")
        return hash_obj

    def enrich_url(self, url):
        """
        Enrich the Url
        :param url: The url value to enrich
        :return: Enriched Url object
        """
        url_data_entities = self.search(url, [EntityTypes.DOMAIN_WHOIS])

        if not url_data_entities:
            raise DigitalShadowsException(f"Can't retrieve data for Url` {url}")

        url_obj = self.digitalShadowsParser.build_url_object(url_data_entities, url)
        if not url_obj:
            raise DigitalShadowsException(f"Can't retrieve data for Url {url}")
        return url_obj

    def enrich_ip(self, ip):
        """
        Enrich the Ip
        :param ip: The hash value to enrich
        :return: Enriched IP object
        """
        ip_data_entities = self.search(ip, [EntityTypes.WEBROOT_IP])

        if not ip_data_entities:
            raise DigitalShadowsException(f"Can't retrieve data for IP {ip}")

        ip_obj = self.digitalShadowsParser.build_ip_object(ip_data_entities, ip)
        if not ip_obj:
            raise DigitalShadowsException(f"Can't retrieve data for IP {ip}")

        return ip_obj

    def enrich_cve(self, cve):
        """
        Enrich the Cve
        :param cve: The hash value to enrich
        :return: Enriched CVE object
        """
        cve_data_entities = self.search(
            cve, [EntityTypes.EXPLOIT, EntityTypes.VULNERABILITY]
        )

        if not cve_data_entities:
            raise DigitalShadowsException(f"Can't retrieve data for CVE {cve}")

        cve_obj = self.digitalShadowsParser.build_cve_object(cve_data_entities, cve)
        if not cve_obj:
            raise DigitalShadowsException(f"Can't retrieve data for CVE {cve}")

        return cve_obj

    def get_incidents(
        self, existing_ids, start_time, end_time, types, lowest_severity, fetch_limit
    ):
        """
        Get incidents.
        :param existing_ids: {list} The list of existing ids.
        :param start_time: {str} The datetime from where to fetch incidents.
        :param end_time: {str} The datetime to where to fetch incidents.
        :param types: {list} List of incident types that should be ingested.
        :param lowest_severity: {int} Lowest severity that will be used to fetch incidents.
        :param fetch_limit: {int} Max incidents to fetch
        :return: {list} The list of Incidents.
        """
        request_url = self._get_full_url("get_incidents")
        payload = {
            "filter": {
                "dateRange": f"{start_time}/{end_time}",
                "dateRangeField": "published",
                "statuses": ["UNREAD", "READ"],
                "types": self._build_types_query(types),
                "severities": self._get_severities_from(lowest_severity),
            },
            "sort": {"property": "published", "direction": "ASCENDING"},
            "pagination": {},
        }
        incidents = [
            self.digitalShadowsParser.build_incident_object(incident_json)
            for incident_json in self._paginate_results(
                method="POST", url=request_url, body=payload, fetch_limit=fetch_limit
            )
        ]
        filtered_alerts = filter_old_alerts(
            logger=self.siemplify_logger, alerts=incidents, existing_ids=existing_ids
        )
        return sorted(filtered_alerts, key=lambda alert: alert.published)[:fetch_limit]

    def _paginate_results(
        self,
        method,
        url,
        result_key="content",
        fetch_limit=ALERTS_LIMIT,
        params=None,
        body=None,
        err_msg="Unable to get incidents",
    ):
        """
        Paginate the results
        :param method: {unicode} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {unicode} The url to send request to
        :param result_key: {unicode} The key to extract data
        :param fetch_limit: {int} Max alerts to fetch
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {unicode} The message to display on error
        :return: {list} List of results
        """
        if body is None:
            body = {"pagination": {}}
        body["pagination"]["offset"] = 0
        body["pagination"]["size"] = ALERTS_FETCH_SIZE

        response = self.session.request(method, url, params=params, json=body)
        self.validate_response(response, err_msg)
        json_result = response.json()
        results = json_result.get(result_key, [])

        while response.json().get(result_key, []):
            if len(results) >= fetch_limit:
                break
            body["pagination"]["offset"] = len(results)
            response = self.session.request(method, url, params=params, json=body)
            self.validate_response(response, err_msg)
            results.extend(response.json().get(result_key, []))

        return results

    @staticmethod
    def _get_severities_from(lowest_severity):
        """
        Get the highest severities started from the lowest.
        Ex. Low -> [LOW, MEDIUM, HIGH, VERY_HIGH]
        Ex. High -> [HIGH, VERY_HIGH]
        Ex. Unknown -> []
        @param lowest_severity: Lowest severity to start from
        @return: List of the highest severities
        """
        return (
            SEVERITIES[SEVERITIES.index(lowest_severity) :]
            if lowest_severity in SEVERITIES
            else []
        )

    def _build_types_query(self, types):
        """
        Build the types query from given list.
        :param types: {list} List of types.
        :return: {list} Types query
        """
        return [{"type": incident_type} for incident_type in types]
