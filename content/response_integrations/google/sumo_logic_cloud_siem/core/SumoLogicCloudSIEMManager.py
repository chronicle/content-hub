from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS, DEFAULT_MAX_LIMIT, API_ROOT_SUFFIX
from .UtilsManager import validate_response
from .SumoLogicCloudSIEMParser import SumoLogicCloudSIEMParser


class SumoLogicCloudSIEMManager:
    def __init__(
        self,
        api_root,
        verify_ssl,
        api_key=None,
        access_id=None,
        access_key=None,
        siemplify_logger=None,
        force_check_connectivity=False,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the SumoLogicCloudSIEM instance
        :param api_key: {str} API Key of the SumoLogicCloudSIEM instance
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.access_id = access_id
        self.access_key = access_key
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = SumoLogicCloudSIEMParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.set_auth_headers()

        if force_check_connectivity:
            self.test_connectivity()

    def set_auth_headers(self):
        """
        Set auth headers based on configuration
        :return: {void}
        """
        if not self.api_key and not self.access_id and not self.access_key:
            raise Exception(
                'Either "API Key" or "Access ID" + "Access Key" needs to be provided for '
                "authentication"
            )
        elif not self.api_key and not (self.access_id and self.access_key):
            raise Exception(
                'You need to provide both "Access ID" and "Access Key" in the configuration.'
            )

        if self.api_key:
            self.session.headers.update({"X-API-Key": f"{self.api_key}"})
        else:
            self.session.auth = (self.access_id, self.access_key)

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(
            self.api_root,
            f"{API_ROOT_SUFFIX.get('by_api_key') if self.api_key else API_ROOT_SUFFIX.get('by_access_id')}"
            f"{ENDPOINTS[url_id].format(**kwargs)}",
        )

    def test_connectivity(self):
        """
        Test connectivity
        """
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response)

    def add_comment_to_insight(self, insight_id, comment):
        """
        Add Comment To Insight
        :param insight_id: {str} Id of the insight
        :param comment: {str} Comment to add
        """
        url = self._get_full_url("add_comment_to_insight", insight_id=insight_id)
        payload = {"body": comment}
        response = self.session.post(url, json=payload)
        validate_response(response)
        return response.json()

    def add_tag_to_insight(self, insight_id, tag):
        """
        Add Tag To Insight
        :param insight_id: {str} Id of the insight
        :param tag: {str} Tag to add
        """
        url = self._get_full_url("add_tags_to_insight", insight_id=insight_id)
        payload = {"tagName": tag}
        response = self.session.post(url, json=payload)
        validate_response(response)
        return response.json()

    def update_assignee(self, insight_id, assignee_type, assignee):
        """
        Update assignee
        :param insight_id: {str} id of the insight
        :param assignee_type: {str} assignee type for assignee
        :param assignee: {str} assignee identifier
        :return: {void}
        """
        url = self._get_full_url("update_assignee", insight_id=insight_id)
        payload = {"assignee": {"type": assignee_type, "value": assignee}}

        response = self.session.put(url, json=payload)
        validate_response(response)

    def update_status(self, insight_id, status):
        """
        Update status
        :param insight_id: {str} id of the insight
        :param status: {str} insight status
        :return: {void}
        """
        url = self._get_full_url("update_status", insight_id=insight_id)
        payload = {"status": status}

        response = self.session.put(url, json=payload)
        validate_response(response)

    def get_insights(self, limit, start_timestamp, lowest_severity):
        """
        Get insights
        :param limit: {int} The limit for results
        :param start_timestamp: {datetime} The timestamp for oldest insight to fetch
        :param lowest_severity: {str} Lowest severity to use for fetching
        :return: {list} The list of Insight objects
        """
        params = {
            "sorts": "created",
            "q": f'-status:"closed" created:>={start_timestamp}',
        }

        if lowest_severity:
            params["q"] += f' severity:>="{lowest_severity.upper()}"'

        return self._paginate_results(
            method="GET",
            params=params,
            url=self._get_full_url("get_insights"),
            limit=max(limit, DEFAULT_MAX_LIMIT),
            parser_method="build_insight",
        )

    def get_entity_info(self, entity_type, entity_identifier):
        """
        Get entity info
        :param entity_type: {str} entity type
        :param entity_identifier: {str} entity identifier
        :return: {EntityInfo} EntityInfo object
        """
        request_url = self._get_full_url("get_entity_info")

        params = {"q": f'{entity_type}:"{entity_identifier}"', "expand": "inventory"}

        response = self.session.get(request_url, params=params)
        validate_response(response)
        entity_info_objects = self.parser.build_entity_info_objects(response.json())
        return entity_info_objects[0] if entity_info_objects else None

    def get_signals(
        self,
        start_time,
        end_time,
        lowest_severity,
        entity_type,
        entity_identifier,
        limit,
    ):
        """
        Get Signals
        :param start_time: {str} Start time for results
        :param end_time: {str} End time for results
        :param lowest_severity: {int} Lowest severity to filter results with
        :param entity_type: {str} Entity type
        :param entity_identifier: {str} Entity identifier
        :param limit: {int} The limit for results
        :return: {list} List of Signal objects
        """
        url = self._get_full_url("get_signals")
        params = {
            "q": self._build_query_string(
                start_time, end_time, lowest_severity, entity_type, entity_identifier
            ),
            "limit": limit,
        }

        response = self.session.get(url, params=params)
        validate_response(response)

        return self.parser.build_signal_objects(response.json())

    def _build_query_string(
        self, start_time, end_time, severity, entity_type, entity_identifier
    ):
        query_string = ""
        if start_time:
            query_string += f"timestamp:>={start_time} "
        if end_time:
            query_string += f"timestamp:<={end_time} "
        if severity:
            query_string += f"severity:>={severity} "
        if entity_identifier:
            query_string += f'{entity_type}:"{entity_identifier}"'

        return query_string

    def _paginate_results(
        self,
        method,
        url,
        parser_method,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        page_size=20,
    ):
        """
        Paginate the results
        :param method: {str} method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} url to send request to
        :param parser_method: {str} name of parser method to build the result
        :param params: {dict} params of the request
        :param body: {dict} json payload of the request
        :param limit: {int} limit of the results to fetch
        :param err_msg: {str} message to display on error
        :param page_size: {int} items per page
        :return: {list} list of results
        """
        params = params or {}
        page_number = 0
        params["limit"] = page_size
        params.update({"offset": page_number * page_size})

        response = None
        results = []

        while True:
            if response:
                if limit and len(results) >= limit:
                    break

                page_number += 1
                params.update({"offset": page_number * page_size})

            response = self.session.request(method, url, params=params, json=body)

            validate_response(response, err_msg)
            current_items = [
                getattr(self.parser, parser_method)(item_json)
                for item_json in response.json().get("data", {}).get("objects", [])
            ]
            results.extend(current_items)

            if len(current_items) < page_size:
                break

        return results[:limit] if limit else results

    def get_insight(self, insight_id):
        """
        Get insight by id
        :param insight_id: {str} insight id
        :return: {Insight} Insight object
        """
        url = self._get_full_url("get_insight", insight_id=insight_id)
        response = self.session.get(url)
        validate_response(response)
        return self.parser.build_insight(response.json())
