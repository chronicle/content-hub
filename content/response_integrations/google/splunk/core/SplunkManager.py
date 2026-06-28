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
import base64
import json
import time
import urllib.parse
from typing import List, Optional, Dict, Any

import requests

from TIPCommon.base.utils import CreateSession

from splunk.core.SplunkParser import SplunkParser
from splunk.core.UtilsManager import filter_old_alerts
from splunk.core.UtilsManager import wait_and_check_if_job_id_done, get_less_possible_combinations
from splunk.core.constants import (
    DEFAULT_ALERTS_FETCH_LIMIT,
    MAX_EVENTS_COUNT,
    SEVERITY_MAPPER,
    API_BAD_REQUEST,
    API_SERVER_ERROR,
    AUTO_FINALIZE_EC_LIMIT,
)
from splunk.core.exceptions import (
    SplunkManagerException,
    UnableToUpdateNotableEvents,
    SplunkHTTPException,
    SplunkCaCertificateException,
    SplunkBadRequestException,
    AdhocSearchLevelException,
)

ENDPOINTS = {
    "ping": "services/search/v2/jobs/export",
    "search_jobs_export": "services/search/v2/jobs/export",
    "job_details": "services/search/jobs/{orig_sid}",
    "notable_update": "/services/notable_update",
    "submit_event": "/services/receivers/simple",
    "create_search_job": "services/search/jobs",
    "job_results": "services/search/jobs/{orig_sid}/results?count={limit}",
    "host_events": "/services/search/v2/jobs/export",
    "get_related_events": (
        "/services/search/jobs/{orig_sid}/events?count={limit}&search={search}"
    ),
}

CA_CERTIFICATE_FILE_PATH = "cacert.pem"


class SplunkManager:
    def __init__(
        self,
        server_address,
        username,
        password,
        api_token=None,
        ca_certificate=None,
        verify_ssl=False,
        siemplify_logger=None,
        force_check_connectivity=False,
        multi_value_fields=None,
    ):
        """
        The method is used to init an object of Splunk class
        :param server_address: {str} Splunk full server address (scheme://ip:port)
        :param username: {str} an account specified at Splunk
        :param password: {str} a code phrase for the mentioned above account
        :param verify_ssl: {bool} Enable or disable SSL verification for https connections.
        :param siemplify_logger: {SiemplifyLogger} Siemplify logger.
        :param force_check_connectivity: {bool} If True it will check connectivity initially.
        :param multi_value_fields: {list} List of keys given by user to split siemplify events based on them.
        """
        self.server_address = server_address
        self.username = username.encode() if username is not None else None
        self.password = password.encode() if password is not None else None
        self.token = api_token
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.session = CreateSession.create_session()
        self.session.verify = self._verify_certificate(ca_certificate)
        self._authenticate()
        self.parser = SplunkParser()
        self.invalid_orig_sids = []
        self.successful_orig_sids = {}
        self.multi_value_fields = multi_value_fields or []

        if force_check_connectivity:
            self.test_connectivity()

    def _authenticate(self):
        """
        The method is used to authenticate request use token or username and password.
        :return: None or rise SplunkManagerException exception
        """
        if not self.token and not (self.username and self.password):
            raise SplunkManagerException(
                "Please specify username and password or API token."
            )

        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            self.session.auth = (self.username, self.password)

    @property
    def default_query_params(self):
        return {"output_mode": "json"}

    def _get_full_url(
        self, url_id: str, query_params: Optional[Dict[str, Any]] = None, **params: dict
    ) -> str:
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        query_params = query_params or {}
        query_params.update(self.default_query_params)

        full_url = urllib.parse.urljoin(
            self.server_address, ENDPOINTS[url_id].format(**params)
        )
        # update query params
        url_parts = list(urllib.parse.urlparse(full_url))
        query = dict(urllib.parse.parse_qsl(url_parts[4]))
        query.update(query_params)
        url_parts[4] = urllib.parse.urlencode(query)

        return urllib.parse.urlunparse(url_parts)

    def _verify_certificate(self, ca_certificate=None):
        if ca_certificate is not None and self.verify_ssl:
            return self._save_certificate_file(ca_certificate)

        return self.verify_ssl

    def _save_certificate_file(self, ca_certificate_file):
        try:
            file_content = base64.b64decode(ca_certificate_file).decode()
            with open(CA_CERTIFICATE_FILE_PATH, "w") as f:
                f.write(file_content)
                f.close()
            return CA_CERTIFICATE_FILE_PATH
        except Exception as e:
            raise SplunkCaCertificateException(f"Certificate Error: {e}")

    def test_connectivity(self):
        """
        Test connectivity to Splunk
        :return: {bool} True if successful, exception otherwise
        """
        data = {
            "search": f"search index=main | where _time > {time.time()}| head 1",
            "adhoc_search_level": "fast",
            "output_mode": "json",
        }
        response = self.session.post(self._get_full_url("ping"), data=data)

        self.validate_response(response)
        return True

    @staticmethod
    def remove_none_params(params):
        """
        Remove None params.
        :param params: {dict} The original params to send.
        :return: {dict} Params without None values
        """
        return {k: v for k, v in params.items() if v is not None}

    def submit_event(self, index, event, host=None, source=None, source_type=None):
        """
        Submits a single event to the index using ``HTTP POST``.
        :param event: {str} The event to submit.
        :param index: {str}
        :param host: {str} The host value of the event.
        :param source: {str} The source value of the event.
        :param source_type: {str} The source type value of the event.
        """
        query_params = self.remove_none_params(
            {"index": index, "host": host, "source": source, "sourcetype": source_type}
        )
        response = self.session.post(
            self._get_full_url("submit_event", query_params=query_params),
            data=event.encode(encoding="UTF-8"),
        )
        self.validate_response(response)

        return self.parser.build_event(response.json())

    def get_notable_events(
        self,
        existing_ids,
        start_timestamp,
        severity,
        query_filter,
        limit=DEFAULT_ALERTS_FETCH_LIMIT,
    ):
        """
        Get Notable Events.
        :param existing_ids: {list} The list of existing ids.
        :param start_timestamp: {str} Timestamp for oldest notable event to fetch.
        :param severity: {str} Lowest urgency that will be used to fetch notable events.
        :param query_filter: {str} Query filter that will be used to fetch notable events.
        :param limit: {int} The maximum number of events to return.
        :return: [NotableEvent] Results list
        """
        url = self._get_full_url("search_jobs_export")
        payload = self.get_notable_events_payload(
            severity, query_filter, start_timestamp, sort_by_key="_time"
        )
        self.siemplify_logger.info(f"Payload for Splunk: {payload}")
        response = self.session.post(url, data=payload, stream=True)
        self.validate_response(response)

        events = []
        response.encoding = response.encoding or "utf-8"
        fetched_event_ids = set()

        for line in response.iter_lines(decode_unicode=True):
            if line:
                notable_event_search_result = self.parser.get_event_from_search_result(
                    json.loads(line)
                )
                if not notable_event_search_result:
                    continue

                event_id = notable_event_search_result.event.event_id
                if (
                    self._should_process(notable_event_search_result, existing_ids)
                    and event_id not in fetched_event_ids
                ):
                    events.append(notable_event_search_result.event)
                    fetched_event_ids.add(event_id)

            if len(events) >= limit:
                break

        return sorted(events, key=lambda event: event.timestamp_ms)

    def _should_process(self, notable_event_search_result, existing_ids):
        """
        Should process event
        :param notable_event_search_result: {NotableEventSearchResult} Notable event search result.
        :param existing_ids: {list} The list of existing ids.
        :return: {bool} True if should process
        """
        if not notable_event_search_result:
            return False

        if notable_event_search_result.event.event_id in existing_ids:
            self.siemplify_logger.info(
                f"Alert {notable_event_search_result.event.event_id} "
                "already processed. Skipping"
            )
            return False

        return True

    def get_notable_events_payload(
        self, severity, query_filter, start_timestamp, sort_by_key=None
    ):
        """
        Get notable events payload.
        :param severity: {str} severity.
        :param start_timestamp: {str} Earliest time.
        :param query_filter: {str} Query filter that will be used to fetch notable events.
        :param sort_by_key: {str} Sort by key.
        :return: {dict} Payload to load notable events
        """
        return {
            "search": self._get_search_query(
                self._build_where_condition(
                    [self._build_severity_filter(severity), query_filter]
                ),
                sort_by_key=sort_by_key,
            ),
            "adhoc_search_level": "fast",
            "output_mode": "json",
            "earliest_time": start_timestamp,
        }

    @staticmethod
    def _build_where_condition(queries, operator="AND", with_prefix=True):
        """
        Join and build where conditions.
        :param queries: {list} List of queries.
        :param operator: {str} AND or OR
        :param with_prefix: {bool} If True 'where' string will be add before the condition
        :return: {str} Concatenated query
        """
        clean_queries = [query for query in queries if query]
        if clean_queries:
            condition = f" {operator} ".join(
                [f"({query})" for query in queries if query]
            )
            return f"where {condition}" if with_prefix else condition

    @staticmethod
    def _get_search_query(where_condition, sort_by_key=None):
        """
        Build search filter.
        :param where_condition: {str} where condition query string.
        :param sort_by_key: {str} Sort by key.
        :return: {str} The query for search filter
        """
        where_condition_query = f"| {where_condition}" if where_condition else ""
        sort_by = f"| sort {sort_by_key}" if sort_by_key else ""
        return (
            "search `get_notable_index` | eval epoch=_time | eval "
            "`get_event_id_meval`,rule_id=event_id | tags outputfield=tag | "
            "`mvappend_field(tag,orig_tag)` | `notable_xref_lookup` | "
            "`get_correlations` | `get_current_status` | `get_owner` | `get_urgency` | "
            f"typer {where_condition_query} {sort_by} | fields *"
        )

    @staticmethod
    def _build_severity_filter(severity):
        """
        Build severity filter.
        :param severity: {str} Lowest urgency that will be used to fetch notable events.
        :return: {str} The query for severity filter
        """
        severity_filters = []

        for key, value in sorted(SEVERITY_MAPPER.items()):
            if value.lower() == severity.lower():
                break

            severity_filters.append(value)

        if severity_filters:
            return " AND ".join(
                [f'urgency!="{severity}"' for severity in severity_filters]
            )

    def get_job_details(self, alert):
        job_details = self.successful_orig_sids.get(alert.orig_sid)
        if not job_details:
            try:
                if not alert.orig_sid or alert.orig_sid in self.invalid_orig_sids:
                    raise
                response = self.session.get(
                    self._get_full_url("job_details", orig_sid=alert.orig_sid),
                    data={"output_mode": "json"},
                )
                self.validate_response(response)
                job_details = self.parser.build_job_details_object(response.json())
                self.successful_orig_sids[alert.orig_sid] = job_details
            except Exception as e:
                self.invalid_orig_sids.append(alert.orig_sid)
        return job_details

    def get_base_events(self, alert):
        """
        Get events for notable connector .
        :param alert: {AlertInfo} The alert to fetch events.
        :return: {list} Events related to alert
        """
        alert.set_job_details(self.get_job_details(alert))
        is_source_events_available = alert.is_source_events_available()
        self.siemplify_logger.info(
            f"Is source events available: {is_source_events_available}"
        )
        if is_source_events_available:
            source_events = self.load_source_events(alert)
            if source_events:
                self.siemplify_logger.info(f"Found {len(source_events)} source events")
                return alert.prepare_events(source_events)
            else:
                self.siemplify_logger.info("Empty source events")

    def get_events(
        self,
        alert,
        extract_base_events=True,
        notable_event_data_along_base_event=False,
        drilldown_events=False,
    ):
        """
        Get events for notable connector.
        :param alert: {AlertInfo} The alert to fetch events.
        :param extract_base_events: {Bool} If enabled, connector will try to extract base events related to notable event using information about the job.
        :param notable_event_data_along_base_event: {Bool} If True, connector will load events based on Notable Event in addition to Base Events.
        :param drilldown_events: {Bool} If True, the connector will only fetch drilldown events without trying to fetch base events.
        :return: {list} Events related to alert
        """
        notable_events = self.get_events_with_multi_value_fields(alert)

        if not extract_base_events:
            self.siemplify_logger.info(
                "Extract base events disabled. Using only notable events."
            )
            return notable_events
        else:
            extra_events = notable_events if notable_event_data_along_base_event else []
            self.siemplify_logger.info(
                f"Loaded {len(notable_events)} extra events (notable)"
            )

            if not drilldown_events:
                try:
                    base_events = self.get_base_events(alert)

                    if base_events:
                        return extra_events + base_events
                    else:
                        # If base events are not found, try fetching drilldown events
                        self.siemplify_logger.info(
                            "Base events not found. Trying to fetch drilldown events."
                        )

                        return self.get_drill_down_with_extra_events(
                            alert, extra_events, notable_events
                        )

                except Exception as e:
                    self.siemplify_logger.info(
                        "Unable to get base events. Applying fallback mechanism. "
                        f"Reason: {e}"
                    )
            else:
                return self.get_drill_down_with_extra_events(
                    alert, extra_events, notable_events
                )

        return extra_events or notable_events

    def get_drill_down_with_extra_events(self, alert, extra_events, notable_events):
        try:
            drilldown_events = self.get_drilldown_events(alert)

            if drilldown_events:
                self.siemplify_logger.info(
                    "Source event type: drilldown events. "
                    f"Events count {len(drilldown_events)}"
                )
                return extra_events + drilldown_events

        except Exception as e:
            self.siemplify_logger.info(
                "Unable to get drilldown events. Applying fallback mechanism. "
                f"Reason: {e}"
            )

        return extra_events or notable_events

    def get_drilldown_events(self, alert, limit=MAX_EVENTS_COUNT):
        """
        Get events for notable connector .
        :param alert: {AlertInfo} The alert to fetch events.
        :param limit: {int}
        :return: {list} Events related to alert
        """
        where_conditions = alert.get_drilldown_event_queries(self.siemplify_logger)

        if not where_conditions:
            return []

        self.siemplify_logger.info(f"Drilldown queries count: {len(where_conditions)}")

        events_list = [
            self.get_events_by_query(
                search_query=query,
                limit=limit,
                latest_time=alert.valid_info_max_time or None,
                earliest_time=alert.valid_info_min_time or None,
                build_with="build_notable_event_object",
                log_payload=True,
            )
            for query in where_conditions
        ]

        if not events_list:
            return []

        events_list = self.get_separated_events_per_query(
            events_list,
            events_count_per_list=min(limit // len(where_conditions), int(alert.count)),
        )

        return alert.prepare_events(
            [
                event.get_alert_as_event(set_drilldown_fields=True)
                for event in events_list
            ],
            drilldown_events=True,
        )

    def get_separated_events_per_query(self, events_list, events_count_per_list):
        """
        Detect and fill missing events from extra ones
        :param {list} List of list_events [[..], [..]]
        """
        backlog_events, missing_events = [], []
        # detect missing and save extra events
        for index, events in enumerate(events_list):
            extra_events = events[events_count_per_list:]
            missing_count = events_count_per_list - len(events)
            if extra_events:
                backlog_events.extend(extra_events)
                del events[events_count_per_list:]  # remove extra events
            elif missing_count:  # if positive
                missing_events.append((index, missing_count))
        # extend missing events
        for index, missing_count in missing_events:
            events_list[index].extend(
                backlog_events[:missing_count]
            )  # add missing events
            del backlog_events[:missing_count]

        return [event for events in events_list for event in events]

    def get_events_with_multi_value_fields(self, alert):
        multi_value_fields = alert.get_multi_value_fields(self.multi_value_fields)
        combinations = get_less_possible_combinations(multi_value_fields)
        if combinations:
            # case when we have multi value fields
            self.siemplify_logger.info(
                "Source event type: Duplicated notable. "
                f"Multi value files are {multi_value_fields}"
            )
            return [
                alert.get_updated_event(combination) for combination in combinations
            ]

        self.siemplify_logger.info("Source event type: Notable")
        return [alert.get_alert_as_event()]

    def _build_query_for_source_events(self, combination):
        """
        Build query for source events
        :param combination: {dict} dict for creating the where condition
        :return: {str} The final query to execute
        """
        where_condition_query = ""
        if list(combination.items()):
            where_condition_query = "| where {}".format(
                " AND ".join(
                    f'({key} = "{value}")' for key, value in combination.items()
                )
            )
        return f"search {where_condition_query} | fields *"

    def get_events_by_query(
        self,
        search_query,
        limit=None,
        earliest_time=None,
        latest_time=None,
        build_with="build_query_event",
        revers_limit=None,
        log_payload=False,
    ):
        """
        Get events by provided query
        :param search_query: {str} a query uses to run search
        :param limit: {int}
        :param earliest_time: {str} a value specified the earliest to get events.
        :param latest_time: {str} a value specified the latest time to get events.
        :param build_with: {str} parser method name
        :param revers_limit: {int}
        :param log_payload: {bool} If true payload will be logged
        :return: [] or str Results list or sid
        """
        payload = self.remove_none_params(
            {
                "search": self.build_general_search_query(
                    search_query, limit=limit, fields="*", revers_limit=revers_limit
                ),
                "adhoc_search_level": "fast",
                "output_mode": "json",
                "latest_time": latest_time,
                "earliest_time": earliest_time,
                "auto_finalize_ec": AUTO_FINALIZE_EC_LIMIT,
            }
        )
        if log_payload:
            self.siemplify_logger.info(f"Payload for events: {payload}")
        response = self.session.post(
            self._get_full_url("create_search_job"), data=payload
        )
        self.validate_response(response)

        sid = self.parser.get_sid_from_search(response.json())

        if not wait_and_check_if_job_id_done(self, sid, repeat=100):
            self.siemplify_logger.info(f"Job with sid {sid} not ready yet")
            return []

        events = [
            event
            for event in self.get_job_results(sid, build_with=build_with, limit=limit)
            if event
        ]

        self.delete_job(sid)

        return sorted(events, key=lambda event: event.timestamp or 0)

    def get_related_events(self, sid, limit, search):
        """
        Get related events for source events.
        :param sid: {str} sid of already created job.
        :param limit: {int} result limit
        :param search: {str} search query
        :return: {list} Related events
        """
        response = self.session.get(
            self._get_full_url(
                "get_related_events", orig_sid=sid, limit=limit, search=search
            )
        )
        self.validate_response(response)

        return self.parser.build_results(response.json())

    def get_sid_for_source_event(self, alert):
        """
        Creat job for loading source events
        :param alert: {Alert} Alert for getting source events
        :return: {str} Sid for created job
        """
        payload = {
            "adhoc_search_level": "verbose",
            "output_mode": "json",
            "search": alert.job_details.query_to_execute,
            "earliest_time": alert.source_events_start_time,
            "latest_time": alert.source_events_end_time,
        }
        self.siemplify_logger.info(f"Loading source events using payload: {payload}")
        response = self.session.post(
            self._get_full_url("create_search_job"), data=payload
        )

        self.validate_response(response)
        sid = self.parser.get_sid_from_search(response.json())
        if not wait_and_check_if_job_id_done(self, sid, repeat=100):
            self.siemplify_logger.info(f"Job with sid {sid} not ready yet")
            return False
        return sid

    def load_source_events(self, alert):
        """
        Load source event
        :param alert: {Alert} Alert for getting source events
        :return: {list} Source events
        """
        source_events = []

        sid = self.get_sid_for_source_event(alert)
        if not sid:
            return []

        self.siemplify_logger.info(f"Source event job is ready. Sid: {sid}")

        where_conditions = self._get_source_event_where_conditions(alert)
        limit = min(MAX_EVENTS_COUNT // len(where_conditions), int(alert.count))

        self.siemplify_logger.info(f"Total queries: {len(where_conditions)}")

        for where_condition in where_conditions:
            query = self._build_query_for_source_events(where_condition)
            current_events = self.get_related_events(sid=sid, limit=limit, search=query)
            self.siemplify_logger.info(
                f'Loaded {len(current_events)} source events using query "{query}"'
            )
            source_events += current_events

        return source_events

    def _get_source_event_where_conditions(self, alert):
        """
        Get source event's where conditions
        :param alert: {Alert} Alert to generate the where condition
        :return: {dict} Dict contains key and value for field to build where condition
        """
        fields = alert.get_metadata_static_with_values()
        if not fields:
            raise Exception("fieldMetadataStatic is empty")
        self.siemplify_logger.info(f"Meta static values: {fields}")

        where_conditions = []

        for key, values in fields.items():
            multi_value = values if isinstance(values, list) else [values]
            for single_value in multi_value:
                where_conditions.append({key: single_value})

        return where_conditions if fields else [{}]

    def update_notable_event(
        self,
        notable_event_ids: List[str],
        status: int | None = None,
        urgency: str | None = None,
        new_owner: str | None = None,
        comment: str | None = None,
        disposition: str | None = None,
    ) -> None:
        """
        Update notable event

        Args:
            notable_event_ids: List of notable event ids
            status: Status to update
            urgency: Urgency to update
            new_owner: New owner to update
            comment: Comment to update
            disposition: Disposition to update

        Returns:
            None
        """

        payload: dict[str, Any] = {
            "ruleUIDs[]": notable_event_ids,
        }
        if status is not None:
            payload["status"] = status
        if urgency is not None:
            payload["urgency"] = urgency
        if disposition is not None:
            payload["disposition"] = f"disposition:{str(disposition)}"
        if new_owner:
            payload["newOwner"] = new_owner
        if comment:
            payload["comment"] = comment

        response = self.session.post(self._get_full_url("notable_update"), data=payload)
        try:
            self.validate_response(response)
        except Exception as response_error:
            if response.status_code == 400:
                raise UnableToUpdateNotableEvents(response.json()) from response_error
            raise

    def add_comment_to_event(self, event_id, comment):
        """
        Update event comment.
        :param event_id: {str} notable event ids.
        :param comment: {str} comment.
        """
        payload = {"ruleUIDs[]": event_id, "comment": comment}
        response = self.session.post(self._get_full_url("notable_update"), data=payload)
        self.validate_response(response)

    def close_events(self, event_ids):
        """
        Change events statuses to closed.
        :param event_ids: {list} notable event ids.
        """
        payload = {"ruleUIDs[]": event_ids, "status": 5}
        response = self.session.post(self._get_full_url("notable_update"), data=payload)
        self.validate_response(response)

    def get_siemplify_alerts(self, existing_ids, limit, start_time):
        """
        The method is used to run a normal query at Splunk web.
        :param existing_ids: {list} the list of existing ids.
        :param limit: {int} a value specified a number of events.
        :param start_time: {str} time frame of alerts to fetch.
        :return: Results list
        """
        start_time = float(start_time) / 1000
        search_query = f"| inputlookup siemplify_alerts | where _time >= {start_time} | sort + _time"
        new_alerts = self.get_events_by_query(
            search_query,
            max(limit, 100),
            build_with="build_siemplify_alert_list_from_result_json",
        )
        self.siemplify_logger.info(f"Fetched {len(new_alerts)} alerts from Splunk")
        filtered_alerts = filter_old_alerts(
            self.siemplify_logger, new_alerts, existing_ids
        )
        self.siemplify_logger.info(
            f"Count after removing existing alerts: {len(filtered_alerts)}"
        )
        return filtered_alerts[:limit]

    def get_events_by_filter(self, start_timestamp=None, event_ids=None):
        """
        Get Notable Events by filter.
        :param start_timestamp: {str} Timestamp for oldest notable event to fetch.
        :param event_ids: {list} The list of event ids.
        :return: [NotableEvent] Results list
        """
        url = self._get_full_url("search_jobs_export")
        payload = {
            "search": self._get_search_query(
                self._build_where_condition([self._build_event_ids_filter(event_ids)])
            ),
            "adhoc_search_level": "fast",
            "output_mode": "json",
        }
        if start_timestamp:
            payload["earliest_time"] = start_timestamp

        response = self.session.post(url, data=payload, stream=True)
        self.validate_response(response)

        return self.read_stream_events(response, raw_data=False)

    @staticmethod
    def _build_event_ids_filter(event_ids):
        """
        Build event ids filter.
        :param event_ids: {list} The list of event ids.
        :return: {str} The query for event ids filter
        """
        if event_ids:
            return " OR ".join([f'event_id="{event_id}"' for event_id in event_ids])

    def separated_entities_to_where_condition(
        self, separated_entities, operator, types_mapper
    ):
        """
        Generate where condition for provided separated entities.
        :param separated_entities: {dict} {"users": [the_entity_identifier, example, test@test.test]}
        :param operator: {str} Join operator for splunk. AND or OR
        :param types_mapper: {dict} {"users": user_key_in_splunk}
        :return: {str} Generated where condition
        """
        queries = []
        for entity_key, entity_values in separated_entities.items():
            where_condition = f" or {types_mapper[entity_key]}=".join(
                f'"{entity_val}"' for entity_val in entity_values
            )
            queries.append(f"{types_mapper[entity_key]}={where_condition}")

        return self._build_where_condition(
            queries, operator=operator, with_prefix=False
        )

    def search_job_for_query(
        self,
        search_mode,
        query,
        limit,
        from_time,
        to_time,
        fields,
        separated_entities=None,
        operator=None,
        types_mapper=None,
    ):
        """
        Submit Query to get sid
        :param search_mode {str} Specify the mode for search execution
        :param query: {str} Query run search
        :param limit: {int} Value specified a number of events
        :param from_time: {str} Value specified the earliest time of events
        :param to_time: {str} Value specified the latest time of events
        :param fields: {str} fields that need to be returned
        :param separated_entities: {dict} where condition properties
        :param operator: {str} where condition operator OR or AND
        :param types_mapper: {dict} {type: field_name provided by user}
        :return: {str} ID of search item
        """
        condition = (
            self.separated_entities_to_where_condition(
                separated_entities, operator, types_mapper
            )
            if separated_entities
            else None
        )
        params = {
            "search": self.build_general_search_query(query, limit, fields, condition),
            "earliest_time": from_time,
            "latest_time": to_time,
            "adhoc_search_level": search_mode.lower(),
            "output_mode": "json",
        }
        self.siemplify_logger.info(f'The final query is "{params.get("search")}"\n')
        response = self.session.post(
            self._get_full_url("create_search_job"), data=params
        )
        self.validate_response(response)
        return self.parser.get_sid_from_search(response.json())

    def search_host_events(self, query, limit, from_time, to_time, fields):
        """
        Submit Query to get sid
        :param query: {str} Query run search
        :param limit: {int} Value specified a number of events
        :param from_time: {str} Value specified the earliest time of events
        :param to_time: {str} Value specified the latest time of events
        :param fields: {str} fields that need to be returned
        :return: {str} ID of search item
        """
        params = {
            "search": self.build_general_search_query(query, limit, fields),
            "earliest_time": from_time,
            "latest_time": to_time,
            "adhoc_search_level": "smart",
            "output_mode": "json",
        }
        response = self.session.post(self._get_full_url("host_events"), data=params)
        self.validate_response(response)
        lines = self.read_stream(response)
        current_events = []
        for line in lines:
            search_result = self.parser.build_result(
                json.loads(line), method_name="build_event"
            )
            if search_result:
                current_events.append(search_result)

        return current_events

    @staticmethod
    def read_stream(response):
        """
        Return none empty lines
        :param response: {list} List of raw jsons
        :return: {list} List of lines
        """
        if response.encoding is None:
            response.encoding = "utf-8"

        return [line for line in response.iter_lines(decode_unicode=True) if line]

    def read_stream_events(self, response, limit=None, is_notable=True, raw_data=True):
        """
        Return events
        :param response: {list} List of raw jsons
        :param limit: {int} Limit of events
        :param is_notable: {bool} Specify object type of an event
        :param raw_data: {bool} True if result should contain raw_json
        :return: {list} List of events
        """
        response.encoding = response.encoding or "utf-8"
        current_events = []
        for line in response.iter_lines(decode_unicode=True):
            if line:
                search_result = self.parser.get_event_from_search_result(
                    json.loads(line), is_notable=is_notable
                )
                if search_result and (search_result.preview is False):
                    current_events.append(
                        search_result.event.raw_data
                        if raw_data
                        else search_result.event
                    )

            if limit and len(current_events) >= limit:
                break

        return current_events

    def build_general_search_query(
        self,
        query,
        limit=None,
        fields=None,
        condition=None,
        sort=None,
        revers_limit=None,
    ):
        """
        Build general search query
        :param query: {str} Query run search
        :param limit: {int} Value specified a number of events
        :param fields: {str} fields that need to be returned
        :param condition: {str} Query condition search
        :param sort: {str} Sort key
        :param revers_limit: {int} Value specified a number of events, this will use Splunk tail
        :return: {str} ID of search item
        """
        search_params = self.remove_none_params(
            {
                "" if query.strip().startswith(("|", "search")) else "search": query,
                "where": condition,
                "sort": sort,
                "head": limit,
                "tail": revers_limit,
                "fields": fields,
            }
        )

        return " | ".join(f"{key} {value}" for key, value in search_params.items())

    def is_job_done(self, sid):
        """
        Get Job status
        :param sid: {str} Job id
        :return: True if job finished, otherwise False
        """
        response = self.session.get(self._get_full_url("job_details", orig_sid=sid))
        self.validate_response(response)
        return self.parser.get_is_done_status(response.json())

    def delete_job(self, sid):
        """
        Delete job
        :param sid: {str} Job id
        :return: True if job deleted, raise exception otherwise
        """
        response = self.session.delete(self._get_full_url("job_details", orig_sid=sid))
        self.validate_response(response)
        return True

    def get_job_results(self, sid, build_with="build_job_detail_model", limit=None):
        """
        Get Job results
        :param sid: {str} Job Id
        :param build_with: {str} model name
        :param limit: {int} The maximum number of events to return.
        :return: {JobDetails} object
        """
        response = self.session.get(
            self._get_full_url("job_results", orig_sid=sid, limit=limit or "")
        )
        self.validate_response(response)

        return self.parser.build_results(response.json(), method_name=build_with)

    def get_api_error_message(self, exception):
        """
        Get API error message
        :param exception: {Exception} The api error
        :return: {str} error message
        """
        try:
            return self.parser.extract_error_message(exception.response.json())
        except:
            return exception.response.content.decode()

    def validate_response(self, response: requests.Response) -> bool:
        """
        Validate response
        :param response: {requests.Response} The response to validate
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if (
                response.status_code == API_BAD_REQUEST
                and self.get_api_error_message(error) == "Invalid adhoc_search_level."
            ):
                raise AdhocSearchLevelException(self.get_api_error_message(error))

            if (
                response.status_code == API_BAD_REQUEST
                or response.status_code >= API_SERVER_ERROR
            ):
                raise SplunkBadRequestException(self.get_api_error_message(error))

            raise SplunkHTTPException(self.get_api_error_message(error))

        return True
