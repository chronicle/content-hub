from __future__ import annotations
import datetime
import time
from urllib.parse import urljoin

import requests

from .Rapid7InsightIDRExceptions import NotFoundException
from .Rapid7InsightIDRParser import Rapid7InsightIDRParser
from soar_sdk.SiemplifyUtils import unix_now
from .UtilsManager import validate_response
from .constants import ACTION_PROCESS_TIMEOUT, REQUEST_DURATION_BUFFER
from .constants import ENDPOINTS, DATETIME_FORMAT
import datetime
from .Rapid7InsightIDRExceptions import NotFoundException
import time
from .constants import (
    ACTION_PROCESS_TIMEOUT,
    REQUEST_DURATION_BUFFER,
    DEFAULT_MAX_LIMIT,
    MAX_INVESTIGATION_ALERTS_LIMIT,
)
from typing import List
from .datamodels import Investigation


class Rapid7InsightIDRManager:
    def __init__(self, api_root, api_key, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Specifies API Root to use for connection
        :param api_key: {str} Specifies API Key to use for connection
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = Rapid7InsightIDRParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers["X-Api-Key"] = self.api_key

    def test_connectivity(self):
        """
        Test connectivity to the Rapid7 by validating api key
        """
        url = self._get_full_url("validate")
        response = self.session.get(url)
        validate_response(response)

    def _get_full_url(self, url_id: str, **kwargs: str) -> str:
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def list_investigations(self, time_frame, limit, include_closed_investigations):
        """
        Get investigations list based on provided filters
        :param time_frame: {int} Specifies a time frame in hours for which to fetch data
        :param limit: {int} Specifies limit for fetched data
        :param include_closed_investigations: {bool} Specifies whether to include closed investigations or no
        :return: {list} The list of Investigation objects
        """
        url = self._get_full_url("investigations")
        params = {
            "statuses": self.build_statuses_filter(include_closed_investigations),
            "index": 0,
            "size": limit,
            "start_time": self.build_start_time_filter(time_frame),
            "end_time": self.build_end_time_filter(),
        }

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_investigation_objects(response.json())

    def build_statuses_filter(self, include_closed_investigations):
        """
        Build statuses filter
        :param include_closed_investigations: {bool} Specifies whether to include closed investigations or no
        :return: {str} The statuses filter
        """
        return "OPEN,CLOSED" if include_closed_investigations else "OPEN"

    def build_end_time_filter(self):
        """
        Build end time filter
        :return: {str} The end time filter
        """
        return datetime.datetime.fromtimestamp(unix_now() / 1000).strftime(
            DATETIME_FORMAT
        )

    def build_start_time_filter(self, time_frame):
        """
        Build start time filter
        :param time_frame: {int} The time frame in hours for start time filter building
        :return: {str} The start time filter
        """
        offset = time_frame * 60 * 60 * 1000
        start_time = unix_now() - offset
        return datetime.datetime.fromtimestamp(start_time / 1000).strftime(
            DATETIME_FORMAT
        )

    def set_investigation_status(self, investigation_id, status):
        """
        Set the status for the specific investigation by id
        :param investigation_id: {str} The investigation ID to update status for
        :param status: {str} The new status of investigation
        :return: {Investigation} The Investigation object
        """
        url = self._get_full_url(
            "update_investigation_status",
            investigation_id=investigation_id,
            status=status,
        )
        response = self.session.put(url)
        validate_response(response)
        return self.parser.build_investigation_object(response.json())

    def set_investigation_assignee(self, investigation_id, assignee_email):
        """
        Set the assignee for the specific investigation by id
        :param investigation_id: {str} The investigation ID to update assignee for
        :param assignee_email: {str} Email of a new assignee of investigation
        :return: {Investigation} The Investigation object
        """
        url = self._get_full_url(
            "update_investigation_assignee", investigation_id=investigation_id
        )
        payload = {"user_email_address": assignee_email}

        response = self.session.put(url, json=payload)
        validate_response(response)
        return self.parser.build_investigation_object(response.json())

    def list_saved_queries(self, limit):
        """
        Get saved queries list
        :param limit: {int} Specifies limit for fetched data
        :return: {list} The list of SavedQuery objects
        """
        url = self._get_full_url("saved_queries")
        response = self.session.get(url)
        validate_response(response)
        results = self.parser.build_saved_query_objects(response.json())
        return results[:limit] if limit else results

    def create_saved_query(self, name, statement, time_frame, log_names):
        """
        Create saved query based on the provided data
        :param name: {str} Name for the new saved query
        :param statement: {str} Statement to execute in query
        :param time_frame: {int} Time frame in hours for which query should fetch data
        :param log_names: {list} Log names query should execute against
        :return: {SavedQuery} The SavedQuery object
        """
        url = self._get_full_url("create_saved_queries")
        payload = {
            "saved_query": {
                "logs": self.get_logs_ids(log_names) if log_names else [],
                "leql": {
                    "during": {
                        "from": self.build_from_data(time_frame),
                        "to": self.build_to_data(),
                    },
                    "statement": self.transform_statement_data(statement),
                },
                "name": name,
            }
        }

        response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.get_saved_query_object(response.json())

    def get_logs_ids(self, log_names):
        """
        Get logs ids based on the logs names
        :param log_names: {list} The logs names
        :return: {list} The logs ids
        """
        url = self._get_full_url("logs")
        response = self.session.get(url)
        validate_response(response)
        return self.parser.get_logs_ids(response.json(), log_names)

    def build_from_data(self, time_frame):
        """
        Build from data for create saved query request
        :param time_frame: {int} The time frame in hours for from data building
        :return: {int} The from data in milliseconds
        """
        offset = time_frame * 60 * 60 * 1000
        return unix_now() - offset

    def build_to_data(self):
        """
        Build to data for create saved query request
        :return: {int} The to data in milliseconds
        """
        return unix_now()

    def transform_statement_data(self, statement):
        """
        Transform statement data for create saved query request
        :param statement: {str} The statement string
        :return: {str} The transformed statement string
        """
        return statement.replace("'", "'").replace('"', '"')

    def delete_saved_query(self, saved_query_id):
        """
        Delete saved query by provided id
        :param saved_query_id: The ID of the saved query to delete
        :return: {void}
        """
        url = self._get_full_url("delete_saved_queries", saved_query_id=saved_query_id)
        response = self.session.delete(url)
        validate_response(response)

    def run_saved_query(self, saved_query_id, action_start_time):
        """
        Run saved query by provided id and get query results
        :param saved_query_id: {str} The ID of the saved query to run
        :param action_start_time: {int} Action start time in millisecond
        :return: {list} Results raw data
        """
        url = self._get_full_url("run_saved_query", saved_query_id=saved_query_id)
        response = self.session.get(url)
        validate_response(response)
        query_results, next_query_link = self.parser.get_saved_query_results(
            response.json()
        )

        while next_query_link:
            # Checks if the action process timeout approaching
            if (
                unix_now() - action_start_time
                >= ACTION_PROCESS_TIMEOUT - REQUEST_DURATION_BUFFER
            ):
                break

            try:
                results, next_query_link = self.get_saved_query_results(next_query_link)
                query_results.extend(results)
                time.sleep(
                    1
                )  # this is needed because too fast sequential requests can cause API crush
            except NotFoundException:
                # In case when results already received the link for query results expires
                break

        return query_results

    def get_saved_query_results(self, link):
        """
        Get saved query results by provided link
        :param link: The link to use in request
        :return: {tuple} Results raw data, request link
        """
        response = self.session.get(link)
        validate_response(response)
        return self.parser.get_saved_query_results(response.json())

    def update_investigation(
        self, investigation_id: str, **kwargs: str
    ) -> Investigation:
        url = self._get_full_url(
            "update_investigation", investigation_id=investigation_id
        )
        payload = {key: value for key, value in kwargs.items() if value is not None}
        self.session.headers.update({"Accept-version": "investigations-preview"})
        response = self.session.patch(url, json=payload)
        validate_response(response)
        return self.parser.build_investigation_object(response.json())

    def get_investigations(
        self, start_time: datetime, sources: str, severities: str, limit: int
    ) -> List[Investigation]:
        """
        Get investigations
        Args:
            start_time: Start time to fetch from
            sources: Source types to filter with
            severities: Severity types to filter with
            limit: Max number to fetch

        Returns:
            (list)
        """
        url = self._get_full_url("get_investigations")
        params = {
            "start_time": start_time.strftime(DATETIME_FORMAT),
            "sort": "created_time,ASC",
            "statuses": "OPEN,INVESTIGATING",
            "multi-customer": False,
            "sources": sources,
            "priorities": severities,
        }
        self.session.headers.update({"Accept-version": "investigations-preview"})
        results = self._paginate_results(
            url=url, method="GET", params=params, limit=limit
        )

        return self.parser.build_investigation_objects(raw_data=results, pure_data=True)

    def get_investigation_alerts(self, investigation_id: str) -> List[dict]:
        """
        Get investigation alerts
        Args:
            investigation_id: ID of the investigation

        Returns:
            (list)
        """
        url = self._get_full_url(
            "get_investigation_alerts", investigation_id=investigation_id
        )
        self.session.headers.update({"Accept-version": "investigations-preview"})
        return self._paginate_results(
            url=url, method="GET", limit=MAX_INVESTIGATION_ALERTS_LIMIT
        )[:MAX_INVESTIGATION_ALERTS_LIMIT]

    def _paginate_results(
        self,
        url: str,
        method: str,
        params: dict = None,
        data: dict = None,
        err_msg: str = "Unable to fetch resources",
        limit: int = None,
    ) -> List[dict]:
        index = 0

        if not params:
            params = {}

        params.update({"index": index, "size": DEFAULT_MAX_LIMIT})

        res = self.session.request(method, url, params=params, json=data)
        validate_response(res, err_msg)

        res_json = res.json()
        total_results = res_json.get("metadata", {}).get("total_data", {})
        results = res_json.get("data", [])

        while len(results) < total_results:
            if limit and len(results) >= limit:
                break

            index += len(results)

            params.update({"index": index})

            res = self.session.request(method, url, params=params, json=data)
            validate_response(res, err_msg)

            results.extend(res.json().get("data", []))

        return results
