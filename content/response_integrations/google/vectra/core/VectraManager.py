# coding=utf-8
from __future__ import annotations
from datetime import datetime

import requests
import urllib.parse

from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import utc_now
from TIPCommon import filter_old_alerts
from .UtilsManager import validate_response
from .VectraExceptions import (
    ItemNotFoundException,
    TagsUpdateFailException,
    UnknownTagsUpdateException,
)
from .VectraParser import VectraParser
from .constants import (
    NEXT_PAGE_URL_KEY,
    ENDPOINT_TYPE,
    DETECTION_FIXED_STATUS,
    VECTRA_DATETIME_FORMAT,
    DEFAULT_PAGE_SIZE,
    NOT_FOUND_STATUS_CODE,
)

ENDPOINTS = {
    "ping": "api/v2.1/hosts",
    "hosts": "api/v2.1/hosts/{item_id}",
    "detections": "api/v2.1/detections/{item_id}",
    "host_tagging": "/api/v2.1/tagging/host/{item_id}",
    "detection_tagging": "/api/v2.1/tagging/detection/{item_id}",
    "detection_status": "api/v2.1/detections",
    "search_detections": "/api/v2.1/search/detections",
    "triage_rule_details": "/api/v2.1/rules/{triage_id}",
}


class VectraManager:

    def __init__(self, api_root, api_token, verify_ssl=False, siemplify=None):
        """
        The method is used to init an object of Manager class
        :param api_root: API root of the Vectra server.
        :param api_token: API token of the Vectra account
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL certificate for the connection.
        :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class.
        """
        self.api_root = api_root
        self.api_token = api_token
        self.siemplify = siemplify
        self.parser = VectraParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"Token {self.api_token}",
                "Content-Type": "application/json",
            }
        )

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {unicode} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {unicode} The full url
        """
        return urllib.parse.urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _paginate_results(
        self,
        method,
        url,
        result_key="results",
        params=None,
        body=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results
        :param method: {unicode} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {unicode} The url to send request to
        :param result_key: {unicode} The key to extract data
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {unicode} The message to display on error
        :return: {list} List of results
        """
        params["page"] = 1
        params["page_size"] = DEFAULT_PAGE_SIZE
        response = self.session.request(method, url, params=params, json=body)
        validate_response(response, err_msg)
        results = response.json().get(result_key, [])

        while True:
            if not response.json().get(NEXT_PAGE_URL_KEY):
                break
            params["page"] = params["page"] + 1
            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            results.extend(response.json().get(result_key, []))

        return results

    def test_connectivity(self):
        """
        Test connectivity to the Vectra.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = urllib.parse.urljoin(self.api_root, self._get_full_url("ping"))
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to Vectra.")

    def get_item_info(self, item_type, item_id):
        """
        Get information about endpoint/detection.
        :param item_type: {unicode} Selected item type
        :param item_id: {unicode} Selected item ID
        :return: Endpoint or Detection
        """
        url = (
            self._get_full_url("hosts", item_id=item_id)
            if item_type == ENDPOINT_TYPE
            else self._get_full_url("detections", item_id=item_id)
        )
        response = self.session.get(url)
        try:
            validate_response(response, f"Failed to get information about {item_type}")
        except Exception:
            raise ItemNotFoundException(f"{item_type} with ID {item_id} was not found")
        data_json = response.json()

        return (
            self.parser.build_endpoint_object(data_json)
            if item_type == ENDPOINT_TYPE
            else self.parser.build_detection_object(data_json)
        )

    def update_tags(self, item_type, item_id, item_tags):
        """
        Update tags on the endpoint/detection.
        :param item_type: {unicode} Selected item type
        :param item_id: {unicode} Selected item ID
        :param item_tags: {list} List of tags to be updated
        :return: {bool} True if successful, exception otherwise
        """
        url = (
            self._get_full_url("host_tagging", item_id=item_id)
            if item_type == ENDPOINT_TYPE
            else self._get_full_url("detection_tagging", item_id=item_id)
        )
        payload = {"tags": item_tags}
        response = self.session.patch(url, json=payload)

        try:
            validate_response(response, "Failed to update tags.")
        except Exception:
            if response.json().get("tags"):
                raise TagsUpdateFailException(
                    f"Action wasn't able to add tags {','.join(item_tags)} to {item_type} with ID {item_id}. Reason: {response.json().get('tags')}"
                )
            else:
                raise UnknownTagsUpdateException(
                    f"Action wasn't able to add tags to {item_type} with ID {item_id}"
                )

    def update_note(self, item_type, item_id, item_note):
        """
        Update note for the endpoint/detection.
        :param item_type: {unicode} Selected item type
        :param item_id: {unicode} Selected item ID
        :param item_note: {unicode} Note to have on the detection/endpoint.
        :return: {bool} True if successful, exception otherwise
        """
        url = (
            self._get_full_url("hosts", item_id=item_id)
            if item_type == ENDPOINT_TYPE
            else self._get_full_url("detections", item_id=item_id)
        )
        payload = {"note": item_note}
        response = self.session.patch(url, json=payload)
        validate_response(
            response,
            f"Action wasn't able to update note on {item_type} with ID {item_id}",
        )

    def update_detection_status(self, detection_id, detection_status):
        """
        Update status on the detection.
        :param detection_id: {int} ID of the detection to update
        :param detection_status: {unicode} Status to set on the detection
        :return: {bool} True if successful, exception otherwise
        """
        url = self._get_full_url("detection_status")
        mark_as_fixed = (
            "True" if detection_status == DETECTION_FIXED_STATUS else "False"
        )
        payload = {"detectionIdList": [detection_id], "mark_as_fixed": mark_as_fixed}
        response = self.session.patch(url, json=payload)
        try:
            validate_response(response, "Failed to update detection status")
        except Exception:
            raise UnknownTagsUpdateException(
                f"Action wasn't able to update status on detection with ID {detection_id}"
            )

    def get_endpoint_details(self, entity_type, entity_identifier):
        """
        Get information about a specific endpoint in Vectra
        :param entity_type: {HOSTNAME or ADDRESS} The type of the entity
        :param entity_identifier: {unicode} Identifier of the entity
        :return: {list} List of Endpoints
        """
        url = self._get_full_url("ping")
        param_key = "name" if entity_type == EntityTypes.HOSTNAME else "last_source"
        url_params = {param_key: entity_identifier}
        results = self._paginate_results(method="GET", url=url, params=url_params)

        return [
            self.parser.build_endpoint_object(endpoint_json)
            for endpoint_json in results
        ]

    def get_triage_rule_details(self, triage_id):
        """
        Get detailed information about triage rules
        :param triage_id: {int} Triage rule ID
        :return: Triage Rule object
        """
        url = self._get_full_url("triage_rule_details", triage_id=triage_id)
        response = self.session.get(url)
        try:
            validate_response(response, "Failed to get triage rule details")
        except Exception as e:
            if response.status_code == NOT_FOUND_STATUS_CODE:
                raise ItemNotFoundException()
            raise Exception(e)
        return self.parser.build_triage_rule_object(response.json())

    def get_detections(
        self,
        existing_ids,
        limit,
        start_timestamp,
        threat_score,
        certainty_score,
        categories,
    ):
        """
        Get detections.
        :param existing_ids: {list} The list of existing ids.
        :param start_timestamp: {int} Timestamp for oldest detection to fetch.
        :param limit: {int} The limit for results.
        :param threat_score: {int} Lowest threat score that will be used to fetch detections. Min:0 Max:100.
        :param certainty_score: {int} Lowest certainty score that will be used to fetch detections. Min: 0 Max: 100.
        :param categories: {unicode} Specify which categories of detections to ingest into Siemplify.
        :return: {bool} True if successful, exception otherwise.
        """
        url = self._get_full_url("search_detections")
        query_string = self._build_query_string(
            [
                self._build_time_filter(start_timestamp),
                self._build_threat_filter(threat_score),
                self._build_certainty_filter(certainty_score),
                self._build_category_filter(categories),
                self._build_only_actives_filter(),
            ]
        )

        detections = [
            self.parser.build_detection_object(detection_json)
            for detection_json in self._paginate_results(
                method="GET", url=url, params={"query_string": query_string}
            )
        ]

        filtered_detections = filter_old_alerts(
            self.siemplify, detections, existing_ids, "detection_id"
        )
        return sorted(filtered_detections, key=lambda detection: detection.timestamp)

    def _build_only_actives_filter(self):
        """
        Build ONLY actives filter.
        :return: {unicode} The query for ONLY actives
        """
        return 'detection.state:"active"'

    def _build_time_filter(self, start_timestamp):
        """
        Build time filter.
        :param start_timestamp: {int} Timestamp for oldest detection to fetch.
        :return: {unicode} The query for time filter
        """
        return f"detection.last_timestamp:[{datetime.utcfromtimestamp(start_timestamp / 1000).strftime(VECTRA_DATETIME_FORMAT)} TO {utc_now().strftime(VECTRA_DATETIME_FORMAT)}]"

    def _build_certainty_filter(self, certainty_score):
        """
        Build certainty filter.
        :param certainty_score: {int} Lowest certainty score that will be used to fetch detections. Min: 0 Max: 100
        :return: {unicode} The query for certainty filter
        """
        return f"detection.certainty:>={max(0, min(certainty_score, 100))}"

    def _build_threat_filter(self, threat_score):
        """
        Build threat filter.
        :param threat_score: {int} Lowest threat score that will be used to fetch detections. Min:0 Max:100
        :return: {unicode} The query for threat filter
        """
        return f"detection.threat:>={max(0, min(threat_score, 100))}"

    def _build_category_filter(self, categories):
        """
        Build category filter.
        :param categories: {unicode} Comma separated categories of detections to ingest into Siemplify
        :return: {unicode} The query for category filter
        """
        return "({})".format(
            " OR ".join(
                [
                    f'detection.category: "{t.strip().upper()}"'
                    for t in categories.split(",")
                ]
            )
        )

    def _build_query_string(self, queries):
        """
        Join filters.
        :param queries: {list} List of queries.
        :return: {unicode} Concated query
        """
        return " AND ".join(queries)
