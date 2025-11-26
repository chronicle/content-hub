from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Union
from urllib.parse import urlencode, urljoin

import requests
from constants import DEFAULT_MAX_LIMIT, ENDPOINTS
from DarktraceParser import DarktraceParser
from datamodels import Alert
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon.filters import filter_old_alerts
from UtilsManager import string_to_base64, validate_response


class DarktraceManager:
    def __init__(self, api_root, api_token, api_private_token, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Darktrace API root
        :param api_token: {str} Darktrace API token
        :param api_private_token: {str} Darktrace API private token
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root
        should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root
        self.api_token = api_token
        self.api_private_token = api_private_token
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = DarktraceParser()
        self.session = requests.session()
        self.session.verify = verify_ssl

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def prepare_request_headers(self, url_id, params={}, **kwargs):
        """
        Prepare request headers
        :param url_id: {str} The id of url
        :param params: {dict} Parameters for the request
        :param kwargs: {dict} Variables passed for url string formatting
        :return: {dict} The request headers
        """
        date_string = datetime.utcnow().isoformat(timespec="seconds")

        return {
            "DTAPI-Token": self.api_token,
            "DTAPI-Date": date_string,
            "DTAPI-Signature": self.generate_signature(url_id, date_string, params, **kwargs),
        }

    def generate_signature(self, url_id, date_string, params: Union[dict, str] = None, **kwargs):
        """
        Generate signature for request headers
        :param url_id: {str} The id of url
        :param date_string: {str} The date string to use in signature
        :param params: {dict} Parameters for the request
        :param kwargs: {dict} Variables passed for url string formatting
        :return: {str} The generated signature
        """
        if params is None:
            params = {}

        private_token = self.api_private_token.encode()
        endpoint_string = ENDPOINTS[url_id].format(**kwargs)

        if isinstance(params, dict):
            params_string = urlencode(params)
            url_string = "?".join(item for item in [endpoint_string, params_string] if item)
        elif isinstance(params, str):
            url_string = f"{endpoint_string}?{params}"
        else:
            raise Exception("Unexcpected param type")

        signature_string = f"{url_string}\n{self.api_token}\n{date_string}".encode()
        return hmac.new(key=private_token, digestmod=hashlib.sha1, msg=signature_string).hexdigest()

    def test_connectivity(self):
        """
        Test connectivity
        """
        url = self._get_full_url("status")
        response = self.session.get(url, headers=self.prepare_request_headers("status"))
        validate_response(response)

    def get_ai_alerts(
        self,
        existing_ids: list,
        start_timestamp: int,
        end_timestamp: int,
        score: int,
        siemplify: SiemplifyConnectorExecution,
    ) -> list:
        """
        The method is used to get Ai Alert.
        Args:
            existing_ids: (list) List of ids to filter.
            start_timestamp (int): The start timestamp for oldest ai incident to fetch
            end_timestamp (int): The end timestamp for oldest ai incident to fetch
            score (int): The lowest score for ai incident to fetch
            siemplify: Siemplify
        Returns:
            list: List of filtered Alert objects.
        """
        url = self._get_full_url("ai_analyst_incident_events")
        params = {
            "starttime": start_timestamp,
            "endtime": end_timestamp,
            "minscore": score,
            "includeallpinned": "false",
        }

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers("ai_analyst_incident_events", params),
        )
        validate_response(response)
        ai_incidents = self.parser.build_ai_alert_objects(response.json())
        return filter_old_alerts(siemplify, ai_incidents, existing_ids, "id")

    def get_alerts(
        self,
        existing_ids: list[str],
        limit: int,
        start_timestamp: int,
        score: int,
        siemplify: SiemplifyConnectorExecution,
        min_priority: int | None = None,
    ) -> list[Alert]:
        """Get model breaches as alerts.

        Args:
            existing_ids(list[str]): The list of existing ids.
            limit(int): The limit for results.
            start_timestamp(int): The timestamp for oldest model breach to fetch.
            score(int): The lowest score for model breach to fetch.
            min_priority(int): The lowest priority for model breach to fetch.
            siemplify(SiemplifyConnectorExecution): SiemplifyConnectorExecution object.

        Returns:
            list[Alert]: The list of filtered Alert objects
        """
        url = self._get_full_url("model_breaches")
        params = {
            "starttime": start_timestamp,
            "minimal": "false",
            "minscore": score / 100,
            "historicmodelonly": "false",
            "order": "ASC",
            "count": max(limit, DEFAULT_MAX_LIMIT),
        }

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers("model_breaches", params),
        )
        validate_response(response)
        all_model_breaches = self.parser.build_alert_objects(response.json())

        if min_priority is not None:
            all_model_breaches = [
                breach for breach in all_model_breaches if breach.priority >= min_priority
            ]

        return filter_old_alerts(siemplify, all_model_breaches, existing_ids, "id")

    def get_model_breach_details(self, id):
        """
        Get model breach details by id
        :param id: {int} The id of model breach
        """
        url = self._get_full_url("model_breach_details")
        params = {"pbid": id}

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers("model_breach_details", params),
        )
        validate_response(response)
        return self.parser.build_event_objects(response.json())

    def search_devices_by_hostname(self, hostname):
        """
        Search for devices by hostname
        :param hostname: {str} The hostname to perform search
        :return: {Device} Device object
        """
        url = self._get_full_url("device_search")
        params = {"query": f"hostname:{hostname}"}

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers("device_search", params),
        )
        validate_response(response)
        return self.parser.get_device_object(response.json())

    def get_devices(self, key, value):
        """
        Get devices by provided key
        :param key: {str} The key to get devices. Possible values ip, mac
        :param value: {str} The value to get devices
        :return: {Device} Device object
        """
        url = self._get_full_url("devices")
        params = {key: value}

        response = self.session.get(
            url, params=params, headers=self.prepare_request_headers("devices", params)
        )
        validate_response(response)
        return self.parser.build_device_object(response.json())

    def get_similar_devices(self, did, limit):
        """
        Get similar devices by provided id
        :param did: {str} The id to get similar devices for
        :param limit: {str} The results limit
        :return: {list} List of Device objects
        """
        url = self._get_full_url("similar_devices")
        params = {"did": did, "fulldevicedetails": True, "count": limit}

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers("similar_devices", params),
        )
        validate_response(response)
        return self.parser.build_device_objects_list(response.json())

    def get_endpoint_details(self, key, value):
        """
        Get endpoint details by key
        :param key: {str} The key to get endpoint details. Possible values ip, hostname
        :param value: {str} The value to get endpoint details
        :return: {EndpointDetails} EndpointDetails object
        """
        url = self._get_full_url("endpoint_details")
        params = {key: value, "devices": "true", "additionalinfo": "true"}

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers("endpoint_details", params),
        )
        validate_response(response)
        return self.parser.build_endpoint_details_object(response.json())

    def acknowledge_model_breach(self, model_breach_id):
        """
        Acknowledge model breach by id
        :param model_breach_id: {int} Model breach id
        :return: {void}
        """
        url = self._get_full_url("acknowledge", model_breach_id=model_breach_id)
        payload = {"acknowledge": "true"}

        response = self.session.post(
            url,
            data=payload,
            headers=self.prepare_request_headers(
                "acknowledge", params=payload, model_breach_id=model_breach_id
            ),
        )

        validate_response(response)

    def unacknowledge_model_breach(self, model_breach_id):
        """
        Unacknowledge model breach by id
        :param model_breach_id: {int} Model breach id
        :return: {void}
        """
        url = self._get_full_url("unacknowledge", model_breach_id=model_breach_id)
        payload = {"unacknowledge": "true"}

        response = self.session.post(
            url,
            data=payload,
            headers=self.prepare_request_headers(
                "unacknowledge", params=payload, model_breach_id=model_breach_id
            ),
        )

        validate_response(response)

    def get_model_breach(self, model_breach_id):
        """
        Get model breach by id
        :param model_breach_id: {int} Model breach id
        :return: {ModelBreach} ModelBreach object
        """
        url = self._get_full_url("model_breach", model_breach_id=model_breach_id)
        params = {"includeacknowledged": "true"}

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers(
                "model_breach", params=params, model_breach_id=model_breach_id
            ),
        )

        validate_response(response)
        return self.parser.build_model_breach_object(response.json())

    def get_events_for_endpoint(self, did_id, event_type, start_time, end_time, limit):
        """
        Get events for endpoint
        :param did_id: {int} The device id
        :param event_type: {str} The event type
        :param start_time: {int} Start time filter
        :param end_time: {int} End time filter
        :param limit: {int} The limit for results
        :return: {list} List of Event objects
        """
        url = self._get_full_url("details")
        params = {
            "did": did_id,
            "starttime": start_time,
            "endtime": end_time,
            "eventtype": event_type,
            "count": limit,
        }

        response = self.session.get(
            url, params=params, headers=self.prepare_request_headers("details", params)
        )
        validate_response(response)
        return self.parser.build_event_objects(response.json())

    def get_connection_data(self, did_id, hours_backwards):
        """
        Get connection data
        :param did_id: {int} The device id
        :param hours_backwards: {int} amount of hours from where to fetch data
        :return: {ConnectionData} ConnectionData object
        """
        url = self._get_full_url("connection_data")
        params = {
            "did": did_id,
            "fulldevicedetails": "true",
            "odid": 0,
            "showallgraphdata": "false",
            "intervalhours": hours_backwards,
        }

        response = self.session.get(
            url,
            params=params,
            headers=self.prepare_request_headers("connection_data", params),
        )
        validate_response(response)
        return self.parser.build_connection_data_object(response.json())

    def execute_custom_query(self, query, start_time, end_time, limit):
        """
        Execute custom query
        :param query: {str} query to execute
        :param start_time: {str} start time for results
        :param end_time: {str} end time for results
        :param limit: {int} limit for results
        :return: {list} list of SearchResult objects
        """
        params = {
            "search": query,
            "fields": [],
            "offset": 0,
            "timeframe": "custom",
            "time": {"from": start_time, "to": end_time, "user_interval": "0"},
            "size": limit,
        }

        base64_query = string_to_base64(json.dumps(params))
        url = self._get_full_url("advanced_search", base64_query=base64_query)

        response = self.session.get(
            url,
            headers=self.prepare_request_headers("advanced_search", base64_query=base64_query),
        )
        validate_response(response)

        if not response.content:
            return []

        return self.parser.build_search_result_objects(response.json())

    def add_comment_to_model_breach(self, model_breach_id: str, comment: str) -> dict:
        """
        Add comment to model breach

        Args:
            model_breach_id: {str} Model breach id
            comment: {str} Comment to add

        Returns:
            None
        """
        url = self._get_full_url("add_comment", model_breach_id=model_breach_id)
        payload = {"message": comment}

        response = self.session.post(
            url,
            data=json.dumps(payload),
            headers=self.prepare_request_headers(
                "add_comment",
                params=json.dumps(payload),
                model_breach_id=model_breach_id,
            ),
        )

        validate_response(response)
        return response.json()
