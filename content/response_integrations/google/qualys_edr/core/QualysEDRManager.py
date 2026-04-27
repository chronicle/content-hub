from __future__ import annotations
from urllib.parse import urljoin
import requests
from .QualysEDRParser import QualysEDRParser
from .UtilsManager import validate_response, filter_old_alerts
from .constants import HEADERS, ENDPOINTS, DEFAULT_MAX_LIMIT


class QualysEDRManager:
    def __init__(self, api_root, username, password, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Api Root to use for connection
        :param username: {str} Username to use for connection
        :param password: {str} Password to use for connection
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = QualysEDRParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.headers.update({"Authorization": f"Bearer {self.get_token()}"})

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def get_token(self):
        """
        Get JWT token
        :return: {str} The JWT token
        """
        url = self._get_full_url("auth")
        payload = {
            "username": self.username,
            "password": self.password,
            "token": "true",
        }

        response = self.session.post(url, data=payload)
        validate_response(response)
        return response.text

    def get_alerts(self, existing_ids, limit, start_timestamp, types, score=None):
        """
        Get alerts
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_timestamp: {int} The timestamp for oldest event to fetch
        :param types: {list} The list of type filters for the events
        :param score: {int} The score filter for the events
        :return: {list} The list of filtered Alert objects
        """
        params = {
            "filter": self.build_filter_query(start_timestamp, types, score),
            "state": "true",
            "sort": '[{"event.dateTime":"asc"}]',
        }

        alerts = sorted(
            self._paginate_results(
                method="GET",
                url=self._get_full_url("events"),
                parser_method="build_alert_object",
                limit=max(limit, DEFAULT_MAX_LIMIT),
                params=params,
            ),
            key=lambda x: x.datetime,
        )

        return filter_old_alerts(self.siemplify_logger, alerts, existing_ids, "id")

    def _paginate_results(
        self,
        method,
        url,
        parser_method,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        page_size=100,
    ):
        """
        Paginate the results
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param parser_method: {str} The name of parser method to build the result
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :param page_size: {int} Items per page
        :return: {list} List of results
        """
        params = params or {}
        page_number = 0
        params["pageSize"] = page_size
        params.update({"pageNumber": page_number})

        response = None
        results = []

        while True:
            if response:
                if limit and len(results) >= limit:
                    break

                params.update({"pageNumber": params["pageNumber"] + 1})

            response = self.session.request(method, url, params=params, json=body)

            validate_response(response, err_msg)
            current_items = [
                getattr(self.parser, parser_method)(item_json)
                for item_json in response.json()
            ]
            results.extend(current_items)
            if len(current_items) < page_size:
                break

        return results[:limit] if limit else results

    @staticmethod
    def build_filter_query(start_timestamp, types, score=None):
        """
        Build query string for filter parameter
        :param start_timestamp: {int} The timestamp for oldest event to fetch
        :param score: {int} The score filter for the events
        :param types: {list} The list of type filters for the events
        :return: {str} The query string
        """
        filters = [
            f'event.dateTime:["{start_timestamp}" .. "now"]',
            "({})".format(" or ".join([f"type:'{type}'" for type in types])),
        ]

        if score or score == 0:
            filters.append(f"indicator.score >={score}")

        return " and ".join(filters)
