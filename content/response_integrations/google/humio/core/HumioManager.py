from __future__ import annotations
from urllib.parse import urljoin
import requests
from .HumioParser import HumioParser
from .constants import (
    ENDPOINTS,
    DEFAULT_MAX_LIMIT,
    HEADERS,
    SORT_FIELD_TYPE_MAPPING,
    SORT_ORDER_MAPPING,
)
from .UtilsManager import validate_response, filter_old_alerts
from soar_sdk.SiemplifyUtils import unix_now


class HumioManager:
    def __init__(self, api_root, api_token, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Humio API root
        :param api_token: {str} Humio API token
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = HumioParser()
        self.session = requests.session()
        self.session.headers = HEADERS
        self.session.verify = verify_ssl
        self._set_auth_token()

    def _set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update({"Authorization": f"Bearer {self.api_token}"})

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
        Test connectivity
        """
        payload = {"queryString": "|select([@id]) | head(1)"}

        url = self._get_full_url("ping")
        response = self.session.post(url, json=payload)
        validate_response(response)

    def get_events(
        self,
        existing_ids,
        limit,
        start_timestamp,
        repository_name,
        query,
        alert_field_name,
    ):
        """
        Get events
        :param existing_ids: {list} list of existing ids
        :param limit: {int} limit for results
        :param start_timestamp: {int} timestamp for oldest alert to fetch
        :param repository_name: {str} name of the repository
        :param query: {str} query for the events
        :param alert_field_name: {str} name of the key that should be used for alert name
        :return: {list} list of Alert objects
        """
        url = self._get_full_url("get_events", repository_name=repository_name)
        payload = {
            "queryString": f"{query or ''} | head({max(limit, DEFAULT_MAX_LIMIT)})",
            "start": start_timestamp,
            "end": unix_now(),
        }

        response = self.session.post(url, json=payload)
        validate_response(response)

        return filter_old_alerts(
            self.siemplify_logger,
            self.parser.build_alert_objects(response.json(), alert_field_name),
            existing_ids,
            "id",
        )

    def get_events_by_custom_query(
        self,
        repository_name,
        query,
        limit,
        start_time=None,
        end_time=None,
        fields_to_return=None,
        sort_field=None,
        sort_field_type=None,
        sort_order=None,
    ):
        """
        Get events by custom query
        :param repository_name: {str} name of the repository
        :param query: {str} query for the events
        :param limit: {int} limit for results
        :param start_time: {str} start time filter
        :param end_time: {str} end time filter
        :param fields_to_return: {list} list of fields to return
        :param sort_field: {str} field name for sorting
        :param sort_field_type: {str} sorting field type
        :param sort_order: {str}  sorting order
        :return: {tuple} list of Event objects, constructed query
        """
        url = self._get_full_url("get_events", repository_name=repository_name)
        query_string = ""

        if query:
            query_string += query

        if fields_to_return:
            query_string += f"| select([{', '.join(fields_to_return)}])"

        query_string += f"| head({limit})"

        if sort_field and sort_field_type and sort_order:
            query_string += (
                f"| sort(field={sort_field}, type={SORT_FIELD_TYPE_MAPPING.get(sort_field_type)}, "
                f"order={SORT_ORDER_MAPPING.get(sort_order)})"
            )

        payload = {"queryString": query_string}

        if start_time and end_time:
            payload["start"] = start_time
            payload["end"] = end_time

        response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.build_event_objects(response.json()), query_string
