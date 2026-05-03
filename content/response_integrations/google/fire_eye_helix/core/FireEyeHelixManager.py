# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests

from .FireEyeHelixConstants import (
    ALERT_ID_FIELD,
    ENDPOINTS,
    HEADERS,
    ALERTS_FETCH_SIZE,
    NEXT_PAGE_URL_KEY,
    META_URL_KEY,
    SEVERITIES,
    LOW_SEVERITY,
    DATETIME_FORMAT,
    SORT_BY_MAPPER,
    SORT_ORDER_MAPPER,
    ITEM_TYPE_MAPPER,
    ITEM_SORT_BY_MAPPER,
    ALERTS_LIMIT,
    ACCEPTABLE_TIME_UNITS,
    JOB_PAUSED_STATUS,
    JOB_FINISHED_STATUS,
    VALID_TIME_FRAME_PATTERN,
    SHIFT_HOURS,
)
from .FireEyeHelixExceptions import (
    FireEyeHelixNotFoundAlertException,
    FireEyeHelixNotFoundListException,
    FireEyeHelixJobPausedException,
    FireEyeHelixJobNotFinishedException,
    FireEyeHelixInvalidTimeFrameException,
)
from .FireEyeHelixParser import FireEyeHelixParser
from TIPCommon import filter_old_alerts
from .UtilsManager import validate_response, naive_time_converted_to_aware


class FireEyeHelixManager:

    def __init__(self, api_root, api_token, siemplify=None, verify_ssl=False):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the FireEye Helix instance.
        :param api_token: API token of the FireEye Helix.
        :param siemplify: Siemplify object.
        :param verify_ssl: If enabled, verify the SSL certificate for connection to the FireEye Helix server is valid.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.api_token = api_token
        self.siemplify = siemplify
        self.parser = FireEyeHelixParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.headers.update({"x-fireeye-api-key": self.api_token})

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _paginate_results(
        self,
        method,
        url,
        result_key="results",
        fetch_limit=ALERTS_LIMIT,
        params=None,
        body=None,
        err_msg="Unable to get results",
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
        if params is None:
            params = {}
        params["offset"] = 0
        params["limit"] = ALERTS_FETCH_SIZE

        response = self.session.request(method, url, params=params, json=body)
        validate_response(response, err_msg)
        json_result = response.json()
        results = json_result.get(result_key, [])

        while True:
            if len(results) >= fetch_limit or not json_result.get(META_URL_KEY, {}).get(
                NEXT_PAGE_URL_KEY
            ):
                break
            params.update({"offset": len(results)})
            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            results.extend(response.json().get(result_key, []))

        return results

    def test_connectivity(self):
        """
        Test connectivity to the FireEye Helix.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to FireEye Helix.")

    def get_alerts(
        self, existing_ids, start_time, lowest_severity, timezone_offset, fetch_limit
    ):
        """
        Get alerts.
        :param existing_ids: {list} The list of existing ids.
        :param start_time: {str} The datetime from where to fetch indicators.
        :param lowest_severity: {str} Lowest severity that will be used to fetch indicators.
        :param timezone_offset: {str} UTC timezone offset
        :param fetch_limit: {int} Max alerts to fetch
        :return: {list} The list of Alerts.
        """
        request_url = self._get_full_url("get_alerts")

        params = {"state": "Open", "created_at__gte": start_time}
        if lowest_severity != LOW_SEVERITY:
            params["risk"] = self._build_severity_filter(lowest_severity)

        alerts = [
            self.parser.build_alert_object(alert_json, timezone_offset)
            for alert_json in self._paginate_results(
                method="GET", url=request_url, params=params, fetch_limit=fetch_limit
            )
        ]

        filtered_alerts = filter_old_alerts(
            self.siemplify, alerts, existing_ids, id_key=ALERT_ID_FIELD
        )
        return sorted(
            filtered_alerts,
            key=lambda alert: naive_time_converted_to_aware(
                alert.created_at, timezone_offset
            ),
        )

    def get_events_for_alerts(self, alert_id, timezone_offset):
        """
        Get alert events.
        :param alert_id: {str} The id of alert.
        :param timezone_offset: {str} UTC timezone offset
        :return: {list} The list of Events
        """
        request_url = self._get_full_url("get_events", id=alert_id)
        events = [
            self.parser.build_event_object(event_json, timezone_offset)
            for event_json in self._paginate_results(method="GET", url=request_url)
        ]
        return events

    @staticmethod
    def _build_severity_filter(lowest_severity):
        """
        Build severity filter.
        :param lowest_severity: {str} Lowest severity that will be used to fetch indicators.
        :return: {str} The query for certainty filter
        """
        severities = (
            SEVERITIES[SEVERITIES.index(lowest_severity) :]
            if lowest_severity in SEVERITIES
            else []
        )
        return ",".join([f"{severity}" for severity in severities])

    def suppress_alert(self, alert_id, duration):
        """
        Suppress Alert in FireEye Helix.
        :param alert_id: {int} The alert ID that needs to be suppressed.
        :param duration: {int} The duration which specifies for how long the alert should be suppressed in minutes
        :return: {void}
        """
        payload = {"endDate": self.get_date_from_duration(duration)}

        response = self.session.post(
            self._get_full_url("suppress_alert", alert_id=alert_id), json=payload
        )

        if response.status_code == 404:
            raise FireEyeHelixNotFoundAlertException

        validate_response(response)

    @staticmethod
    def get_date_from_duration(duration):
        """
        Get date from duration
        :param duration: {int} The duration in minutes
        :return: {str} The date from duration
        """
        return (datetime.now() + timedelta(minutes=duration)).strftime(DATETIME_FORMAT)

    def close_alert(self, alert_id, revision_note):
        """
        Close Alert in FireEye Helix.
        :param alert_id: {int} The alert ID that needs to be closed.
        :param revision_note: {str} The revision note for the alert.
        :return: {void}
        """
        payload = {"state": "Closed"}

        if revision_note:
            payload["revisionNotes"] = revision_note

        response = self.session.put(
            self._get_full_url("close_alert", alert_id=alert_id), json=payload
        )

        if response.status_code == 404:
            raise FireEyeHelixNotFoundAlertException

        validate_response(response)

    def add_note_to_alert(self, alert_id, note):
        """
        Add a Note to Alert in FireEye Helix.
        :param alert_id: {int} The alert ID to add note to.
        :param note: {str} The note for the alert.
        :return: {void}
        """
        payload = {"note": note}

        response = self.session.post(
            self._get_full_url("add_note", alert_id=alert_id), json=payload
        )

        # Endpoint returns 500 Server Error in case when no alert matches the given query.
        if response.status_code == 500:
            raise FireEyeHelixNotFoundAlertException

        validate_response(response)

    def get_lists(
        self, name, short_name, active, internal, protected, sort_by, sort_order, limit
    ):
        """
        Get Lists from FireEye Helix.
        :param name: {str} The name of list.
        :param short_name: {str} The short name of list.
        :param active: {bool} Specify whether the result should contain only active lists.
        :param internal: {bool}  Specify whether the result should contain only internal lists.
        :param protected: {bool} Specify whether the result should contain only protected lists.
        :param sort_by: {str} Specify sorting parameter for result.
        :param sort_order: {str} Specify sorting order for result.
        :param limit: {int} Maximum number of records to return.
        :return: {list} The list of List objects.
        """
        params = {
            "name": name,
            "short_name": short_name,
            "order_by": self._order_by_filter_builder(
                SORT_BY_MAPPER, sort_by, sort_order
            ),
            "is_internal": internal,
            "is_protected": protected,
            "is_active": active,
            "limit": limit,
        }

        response = self.session.get(self._get_full_url("get_lists"), params=params)
        validate_response(response)
        return self.parser.get_lists(response.json())

    def get_list_by_short_name(self, short_name):
        """
        Get List by short name from FireEye Helix.
        :param short_name: {str} The unique short name of list.
        :return: {List} The List object.
        """
        params = {"short_name": short_name}

        response = self.session.get(self._get_full_url("get_lists"), params=params)
        validate_response(response)
        lists = self.parser.get_lists(response.json())

        if not lists:
            raise FireEyeHelixNotFoundListException()

        return lists[0]

    def get_list_items(self, short_name, value, item_type, sort_by, sort_order, limit):
        """
        Get List items from FireEye Helix.
        :param short_name: {str} The short name of list.
        :param value: {str} Specify value filter for the items.
        :param item_type: {str} Specify type filter for the items.
        :param sort_by: {str} Specify sorting parameter for result.
        :param sort_order: {str} Specify sorting order for result.
        :param limit: {int} Maximum number of records to return.
        :return: {list} The list of Item objects.
        """
        res = self.get_list_by_short_name(short_name)

        params = {
            "value": value,
            "type": self._type_filter_builder(item_type),
            "order_by": self._order_by_filter_builder(
                ITEM_SORT_BY_MAPPER, sort_by, sort_order
            ),
            "limit": limit,
        }

        response = self.session.get(
            self._get_full_url("get_list_items", list_id=res.id), params=params
        )
        validate_response(response)
        return self.parser.get_items(response.json())

    @staticmethod
    def _order_by_filter_builder(sort_by_mapper, sort_by_key, sort_order):
        """
        Build order_by filter.
        :param sort_by_mapper: {dict} Mapper for sorting key.
        :param sort_by_key: {str} Specify sorting key for result.
        :param sort_order: {str} Specify sorting order for result.
        :return: {str} The order_by filter.
        """
        return SORT_ORDER_MAPPER.get(sort_order, "") + sort_by_mapper.get(
            sort_by_key, ""
        )

    @staticmethod
    def _type_filter_builder(filter_type):
        """
        Build type filter.
        :param filter_type: {str} Specify type filter for the items.
        :return: {str} The type filter.
        """
        return ITEM_TYPE_MAPPER.get(filter_type, "")

    def add_item_to_list(self, list_id, value, item_type, risk, note):
        """
        Add entity to list items
        :param list_id: {int} The ID of list.
        :param value: {str} Specify the value of the item.
        :param item_type: {str} Specify the type of the item.
        :param risk: {str} Specify the risk of the item.
        :param note: {str} Specify the note of the item.
        :return: {Item} The Item object.
        """
        payload = {"risk": risk, "type": item_type, "value": value}

        if note:
            payload["notes"] = note

        response = self.session.post(
            self._get_full_url("get_list_items", list_id=list_id), json=payload
        )
        validate_response(response)
        return self.parser.get_item(response.json())

    def index_search(self, query, time_frame, limit):
        """
        Perform index search in FireEye Helix.
        :param query: {str} Specify the query for the search.
        :param time_frame: {str} Specify the time frame for the search.
        :param limit: {int} Maximum number of results to return.
        :return: {IndexSearchResult} The IndexSearchResult object.
        """
        payload = {
            "query": query,
            "options": self._build_search_options(time_frame, limit),
        }

        response = self.session.post(self._get_full_url("search"), json=payload)
        validate_response(response)
        return self.parser.get_index_search_result(response.json())

    def _build_search_options(self, time_frame, limit):
        """
        Build search options.
        :param time_frame: {str} Specify the time frame for the search.
        :param limit: {int} Maximum number of results to return.
        :return: {dict} The search options.
        """
        options = {"offset": 0, "page_size": limit}

        if time_frame:
            options["time_range"] = self._fetch_hours_from_time_frame(time_frame)

        return options

    @staticmethod
    def _fetch_hours_from_time_frame(time_frame):
        """
        Fetch hours from time frame.
        :param time_frame: {str} Specify the time frame to fetch hours.
        :return: {int} The hours fetched from time frame.
        """
        if not re.search(VALID_TIME_FRAME_PATTERN, time_frame):
            raise FireEyeHelixInvalidTimeFrameException(
                'Unexpected format is used in the parameter "Time Frame". '
                "Please check the specified value."
            )
        hours = 0
        time_frame_items = re.findall(r"(\d*)(\w)", time_frame)

        for value, unit in time_frame_items:
            if unit in ACCEPTABLE_TIME_UNITS.keys() and value:
                hours += int(value) * ACCEPTABLE_TIME_UNITS[unit]

        return hours

    def initialize_archive_search_query(self, query, time_frame):
        """
        Initialize archive search query in FireEye Helix.
        :param query: {str} Specify the query for the search.
        :param time_frame: {str} Specify the time frame for the search.
        :return: {int} The job id
        """
        payload = {
            "query": query,
            "searchStartDate": self._build_search_start_date(time_frame),
            "searchEndDate": self._build_search_end_date(),
        }

        response = self.session.post(self._get_full_url("archive_search"), json=payload)
        validate_response(response)
        return self.parser.get_job_id(response.json())

    def _build_search_start_date(self, time_frame):
        """
        Build search start date filter from time frame hours
        :param time_frame: {str} Specify the time frame for building the start date filter.
        :return: {str} The start date filter
        """
        start_date_filter = datetime.now() - timedelta(hours=SHIFT_HOURS)
        start_date_filter = start_date_filter - timedelta(
            hours=self._fetch_hours_from_time_frame(time_frame)
        )
        return start_date_filter.strftime(DATETIME_FORMAT)

    @staticmethod
    def _build_search_end_date():
        """
        Build search end date filter
        :return: {str} The end date filter
        """
        res = datetime.now() - timedelta(hours=SHIFT_HOURS)
        return res.strftime(DATETIME_FORMAT)

    def get_query_result(self, job_id, limit):
        """
        Get query results from FireEye Helix.
        :param job_id: {int} The job id to fetch data.
        :param limit: {int} Maximum number of results to return.
        :return: {ArchiveSearchResult} The ArchiveSearchResult object
        """
        params = {"includes": "_createdBy", "offset": 0, "page_size": limit}

        response = self.session.get(
            self._get_full_url("archive_search_results", job_id=job_id), params=params
        )
        validate_response(response)
        job_state = self.parser.get_job_state(response.json())

        if job_state == JOB_PAUSED_STATUS:
            raise FireEyeHelixJobPausedException()

        if JOB_FINISHED_STATUS not in job_state:
            raise FireEyeHelixJobNotFinishedException()

        return self.parser.get_archive_search_result(response.json())

    def resume_archive_search_query(self, job_id):
        """
        Resume archive search query in FireEye Helix.
        :param job_id: {int} The job id to resume.
        :return: {void}
        """
        response = self.session.post(
            self._get_full_url("resume_archive_search", job_id=job_id)
        )
        validate_response(response)

    def get_endpoint(self, value):
        """
        Get information on endpoint
        :param value: Entity identifier
        :return: Endpoint object
        """
        request_url = self._get_full_url("get_assets")
        params = {"asset_name": value, "page": 1, "limit": 1}
        response = self.session.get(request_url, params=params)
        validate_response(response)
        return self.parser.build_asset_object(raw_data=response.json())

    def get_alert_details(self, alert_id):
        """
        Retrieve information about Alert from FireEye Helix.
        :param alert_id: ID of the Alert
        :return: Alert object
        """
        request_url = self._get_full_url("close_alert", alert_id=alert_id)
        response = self.session.get(request_url)
        if response.status_code == 404:
            raise FireEyeHelixNotFoundAlertException

        validate_response(response)
        return self.parser.build_first_alert(response.json())
