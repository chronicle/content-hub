# ============================================================================#
# title           :SumologicManager.py
# description     :This Module contain all Sumologic operations functionality
# author          :gabriel.munits@siemplify.co (refactored)
# date            :15-02-2021
# python_version  :3.7
# libraries       :requests
# product_version :1.0
# API DOCS: https://help.sumologic.com/@api/deki/pages/5856/pdf/APIs.pdf?stylesheet=default,
# https://help.sumologic.com/Beta/APIs/APIs
# ============================================================================#

from __future__ import annotations
from typing import Optional, List
from urllib.parse import urljoin

import arrow
import requests

from .SumoLogicParser import SumoLogicParser
from .consts import (
    COMPLETED_STATUS,
    ERROR_STATUSES,
    LIMIT_PER_REQUEST,
    ENDPOINTS,
    HEADERS,
)
from .datamodels import SearchMessage
from .exceptions import SumologicManagerError
from .utils import filter_old_alerts


class SumoLogicManager:
    """
    Sumo Logic Manager
    """

    def __init__(
        self, server_address, access_id, access_key, verify_ssl=False, logger=None
    ):
        self.server_address = server_address
        self.session = requests.Session()
        self.session.headers = HEADERS
        self.session.auth = (access_id, access_key)
        self.session.verify = verify_ssl

        self.logger = logger
        self.parser = SumoLogicParser()

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.server_address, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to Sumologic
        :return: {bool} True if successful, exception otherwise.
        """
        since = arrow.utcnow().int_timestamp * 1000
        job_id = self.search("| count _sourceCategory", since=since, to=since + 1)
        self.delete_job(job_id)

    def search(
        self, query: str, since: str, to: str, by_receipt_time: Optional[bool] = False
    ):
        """
        Initiate a search job
        :param query: {str} The actual search expression. Make sure your query
        is in valid JSON format, you may need to escape certain characters.
        :param since: {str} The ISO 8601 date and time of the time range to start the search.
        Can be unixtime (milliseconds) or YYYY-MM-DDTHH:mm:ss.
        :param to: {str} The ISO 8601 date and time of the time range to end the search.
        Can be unixtime (milliseconds) or YYYY-MM-DDTHH:mm:ss.
        :param by_receipt_time: {bool} Define as "true" to run the search
        using receipt time. By default, searches do not run by receipt time.
        :return: {str} The id of the search job
        """
        request_url = self._get_full_url("search_job")

        payload = {
            "query": query,
            "from": since,
            "to": to,
            "byReceiptTime": by_receipt_time,
        }

        response = self.session.post(request_url, json=payload)
        self.validate_response(response, f"Unable to run search for query {query}")
        return self.parser.get_search_job_id(response.json())

    def get_job_info(self, job_id):
        """
        Get job information
        :param job_id: {str} The job's id
        :return: {dict} The job info
        """
        request_url = self._get_full_url("get_job_info", job_id=job_id)
        response = self.session.get(request_url)
        self.validate_response(response, f"Unable to get job status for job {job_id}")
        return self.parser.build_job_info_obj(response.json())

    def get_job_status(self, job_id):
        """
        Get a job's state
        :param job_id: {str} The job's id
        :return: {str} The job's current status
        """
        return self.get_job_info(job_id).state

    def is_job_completed(self, job_id):
        """
        Check whether a job is completed
        :param job_id: {str} The job's id
        :return: {bool} True if completed, False otherwise.
        """
        job_status = self.get_job_status(job_id)
        return job_status == COMPLETED_STATUS

    def is_job_error(self, job_id):
        """
        Check whether a job completed with an error
        :param job_id: {str} The job's id
        :return: {bool} True if error, False otherwise.
        """
        job_status = self.get_job_status(job_id)
        return job_status in ERROR_STATUSES

    def get_latest_search_results(self, job_id, limit=None) -> List[SearchMessage]:
        """
        Get latest search results
        :param job_id: {str} The search job's id
        :param limit: {int} The limit of results to fetch
        :return: {[SearchMessage]} List of results
        """
        request_url = self._get_full_url("get_search_results", job_id=job_id)

        offset = 0
        response = self.session.get(
            request_url, params={"limit": LIMIT_PER_REQUEST, "offset": offset}
        )

        self.validate_response(response, f"Unable to get job results for job {job_id}")
        results = self.parser.build_search_message_obj_list(response.json())

        while True:
            if limit and len(results) >= limit:
                break

            offset += LIMIT_PER_REQUEST
            response = self.session.get(
                request_url, params={"limit": LIMIT_PER_REQUEST, "offset": offset}
            )

            self.validate_response(
                response, f"Unable to get more job results for job {job_id}"
            )
            more_results = self.parser.build_search_message_obj_list(response.json())
            if not more_results:
                break

            results.extend(more_results)

        results = sorted(results, key=lambda message: message.receipt_time)
        return results[:limit] if limit is not None else results

    def get_oldest_search_results(
        self, job_id: str, message_count: int, existing_ids: List[str], limit=None
    ) -> List[SearchMessage]:
        """
        Get oldest search results.
        :param job_id: {str} The search job's id
        :param message_count: {int} Total number of messages in search results
        :param existing_ids: {[str]} List of already seen alert ids
        :param limit: {int} The limit of results to fetch
        :return: {[SearchMessage]} List of results
        """
        request_url = self._get_full_url("get_search_results", job_id=job_id)

        start_offset = message_count - LIMIT_PER_REQUEST
        offset = 0 if start_offset < 0 else start_offset

        response = self.session.get(
            request_url, params={"limit": LIMIT_PER_REQUEST, "offset": offset}
        )

        self.validate_response(response, f"Unable to get job results for job {job_id}")
        results = self.parser.build_search_message_obj_list(response.json())
        results = sorted(results, key=lambda message: message.message_time)
        filtered_results = filter_old_alerts(
            logger=self.logger,
            alerts=results,
            existing_ids=existing_ids,
            id_key="message_id",
        )

        while offset > 0:

            if limit and len(filtered_results) >= limit:
                break

            offset -= LIMIT_PER_REQUEST
            request_limit = LIMIT_PER_REQUEST

            if offset < 0:  # Last Request
                offset = 0
                request_limit = offset + LIMIT_PER_REQUEST - 1

            response = self.session.get(
                request_url, params={"limit": request_limit, "offset": offset}
            )
            self.validate_response(
                response, f"Unable to get more job results for job {job_id}"
            )
            more_results = self.parser.build_search_message_obj_list(response.json())
            more_results = sorted(
                more_results, key=lambda message: message.message_time
            )
            filtered_results.extend(
                filter_old_alerts(
                    logger=self.logger,
                    alerts=more_results,
                    existing_ids=existing_ids,
                    id_key="message_id",
                )
            )

        filtered_results = sorted(
            filtered_results, key=lambda message: message.message_time
        )
        filtered_results = (
            filtered_results[:limit] if limit is not None else filtered_results
        )
        return filtered_results

    def delete_job(self, job_id):
        """
        Delete a job
        :param job_id: {str} The job's id
        :return: {bool} True if successful, exception otherwise.
        """
        request_url = self._get_full_url("delete_job", job_id=job_id)
        response = self.session.delete(request_url)
        self.validate_response(response, f"Unable to delete job {job_id}")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} The message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise SumologicManagerError(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise SumologicManagerError(
                f"{error_msg}: {str(error)} {response.json()['message']}"
            )
