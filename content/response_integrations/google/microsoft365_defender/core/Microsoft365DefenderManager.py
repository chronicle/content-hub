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

import datetime
import time
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urljoin

import requests

from soar_sdk.SiemplifyUtils import utc_now

from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.filters import filter_old_alerts

from .constants import (
    ALERT_ID_KEY,
    ALERT_UNIQUE_ID_KEY,
    ALERTS_LIMIT_PER_REQUEST,
    AND_OPERATOR,
    API_ROOT,
    CUSTOM_ACCESS_TOKEN_URL,
    DEFAULT_RESULTS_LIMIT,
    DEFENDER_SCOPE_TEMPLATE,
    ENDPOINTS,
    FETCHING_TIMEOUT_TRESHOLD,
    FILTER_TIME_FORMAT,
    GRAPH_API_ROOT_DEFAULT,
    GRAPH_API_SCOPE_TEMPLATE,
    HTTP_NOT_FOUND_STATUS_CODE,
    INCIDENTS_LIMIT_PER_REQUEST,
    LOGIN_API_ROOT_DEFAULT,
    PREFER_HEADER_FOR_CONNECTOR,
    RETRY_SLEEP,
)
from .datamodels import Alert, AlertWithEvidence, Incident
from .Microsoft365DefenderExceptions import (
    NotFoundItemException,
    Microsoft365DefenderException,
    APIPermissionError,
    TooManyRequestsError,
)
from .Microsoft365DefenderParser import Microsoft365DefenderParser
from .UtilsManager import get_alert_id_from_display_id, validate_response


class Microsoft365DefenderManager:
    def __init__(
        self,
        api_root,
        tenant_id,
        client_id,
        client_secret,
        verify_ssl,
        microsoft_graph_url=GRAPH_API_ROOT_DEFAULT,
        login_api_root=LOGIN_API_ROOT_DEFAULT,
        siemplify=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the Microsoft 365 Defender instance.
        :param tenant_id: {str} Microsoft 365 Defender account tenant ID.
        :param client_id: {str} Microsoft 365 Defender account client ID.
        :param client_secret: {str} Microsoft 365 Defender account client secret.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the
        connection to the server is valid.
        :param microsoft_graph_url: {str} Microsoft Graph API Root
        :param login_api_root: {str} Login API root of the Microsoft 365 Defender
        :param siemplify: Siemplify Connector Executor.
        """
        self.api_root = api_root
        self.login_api_root = login_api_root
        self.microsoft_graph_url = microsoft_graph_url
        self.siemplify = siemplify
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = Microsoft365DefenderParser(
            logger=self.siemplify.LOGGER if self.siemplify else None
        )
        defender_scope = DEFENDER_SCOPE_TEMPLATE.format(
            api_root=self.api_root.rstrip("/")
        )
        graph_scope = GRAPH_API_SCOPE_TEMPLATE.format(
            graph_api_root=self.microsoft_graph_url.rstrip("/")
        )
        self.access_token = self._generate_token(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            verify=verify_ssl,
            scope=defender_scope,
            login_api_root=self.login_api_root,
        )
        self.graph_api_token = self._generate_token(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            verify=verify_ssl,
            scope=graph_scope,
            login_api_root=self.login_api_root,
        )
        self._update_headers()
        self.use_graph_api_for_alerts = True
        self.too_many_request_last_occurrence = None
        self.not_found_alert_ids: set[str] = set()

    def _update_headers(self, use_graph_api: bool = False):
        token = self.access_token
        if use_graph_api:
            token = self.graph_api_token

        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def _enable_prefer_header(self) -> None:
        self.session.headers.update({"Prefer": PREFER_HEADER_FOR_CONNECTOR})

    def _disable_prefer_header(self) -> None:
        self.session.headers.pop("Prefer", None)

    @staticmethod
    def _generate_token(
        client_id,
        client_secret,
        tenant_id,
        login_api_root,
        verify=True,
        scope=None,
    ) -> str:
        """
        Request access token (Valid for 60 min)
        :param client_id: {str} Microsoft 365 Defender account client ID.
        :param client_secret: {str} Microsoft 365 Defender account client secret.
        :param tenant_id: {str} Microsoft 365 Defender Tenant ID.
        :param verify: {bool} Whether to verify SSL certificates
        :param scope: {str} Scope for auth token
        :param login_api_root: {str} Login API root of the Microsoft 365 Defender
        instance.
        :return: Access token
        """
        TOKEN_PAYLOAD = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope if scope is not None else f"{API_ROOT}/.default",
            "grant_type": "client_credentials",
        }
        request_url = CUSTOM_ACCESS_TOKEN_URL.format(
            login_api_root=login_api_root,
            tenant_id=tenant_id,
        )
        response = requests.post(request_url, data=TOKEN_PAYLOAD, verify=verify)
        validate_response(
            response, "Unable to generate access token for Microsoft 365 Defender"
        )

        return response.json().get("access_token")

    def _get_full_url(self, url_id, use_graph=False, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(
            self.api_root if not use_graph else self.microsoft_graph_url,
            ENDPOINTS[url_id].format(**kwargs),
        )

    def test_connectivity(self):
        """
        Test connectivity
        """
        self._update_headers(use_graph_api=True)
        request_url = self._get_full_url(url_id="list_incidents_graph", use_graph=True)
        params = self._build_api_params(start_time=utc_now(), limit=1, graph=True)
        self._execute_request_with_retry(self.session.get, request_url, params=params)

    def update_incident(
        self,
        incident_id,
        status: Optional[str] = None,
        classification: Optional[str] = None,
        determination: Optional[str] = None,
        assign_to: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        """
        Update incident in Microsoft 365 Defender
        :param incident_id: {int} The id of the incident to update
        :param status: {str} Status to set for the incident
        :param classification: {str} Classification to set for the incident
        :param determination: {str} Determination to set for the incident
        :param assign_to: {str} To whom to assign the incidenteg
        :param comment: {str} Comment to add to incident
        """
        self._update_headers(use_graph_api=True)
        request_url = self._get_full_url(
            "update_incident", use_graph=True, incident_id=incident_id
        )
        payload = {}
        if status:
            payload["status"] = status
        if classification:
            payload["classification"] = classification
        if determination:
            payload["determination"] = determination
        if assign_to:
            payload["assignedTo"] = assign_to
        if comment:
            payload["comment"] = comment

        response = self.session.patch(request_url, json=payload)

        if response.status_code == 404:
            raise NotFoundItemException(
                f'incident "{incident_id}" wasn\'t found in Microsoft 365 Defender'
            )

        validate_response(response)

    def add_comment_to_incident(self, incident_id: int, comment: str = None) -> None:
        """Add a comment to an incident in Microsoft 365 Defender.

        Args:
            incident_id (int): The ID of the incident to update.
            comment (str): The comment to add to the incident.
        """

        self._update_headers(use_graph_api=True)
        request_url = self._get_full_url(
            "add_comment_incident", use_graph=True, incident_id=incident_id
        )
        payload = {}

        if comment:
            payload["comment"] = comment

        response = self.session.post(request_url, json=payload)

        if response.status_code == 404:
            raise NotFoundItemException(
                f'incident "{incident_id}" wasn\'t found in Microsoft 365 Defender'
            )

        validate_response(response)

    def add_comment_to_alert(self, alert_id: str, comment: str | None = None) -> None:
        """Add a comment to an alert in Microsoft 365 Defender.

        Args:
            alert_id (str): The ID of the alert to update.
            comment (str, None): The comment to add to the alert. Defaults to None.

        """
        if not comment or not str(comment).strip():
            return

        self._update_headers(use_graph_api=True)
        request_url = self._get_full_url(
            "add_comment_to_alert",
            use_graph=True,
            alert_id=alert_id,
        )
        payload = {"comment": comment}

        self._execute_request_with_retry(
            self.session.post,
            request_url,
            alert_id,
            json=payload,
        )

    def get_alert(self, alert_id: str) -> AlertWithEvidence:
        """Get a single alert by its ID.

        Args:
            alert_id (str): The ID of the alert to fetch.

        Returns:
            AlertWithEvidence: The alert object.
        """
        self._update_headers(use_graph_api=True)
        request_url = self._get_full_url(
            "update_alert",
            use_graph=True,
            alert_id=alert_id,
        )
        response = self._execute_request_with_retry(
            self.session.get,
            request_url,
            alert_id,
        )

        return self.parser.build_alert_with_evidence_object(response.json())

    def update_alert(
        self,
        alert_id,
        status: str | None = None,
        classification: str | None = None,
        determination: str | None = None,
    ) -> None:
        """Update an alert in Microsoft 365 Defender.

        Args:
            alert_id (str): The ID of the alert to update.
            status (str, None): The status to set for the alert. Defaults to None.
            classification (str, None): The classification to set for the alert.
            Defaults to None.
            determination (str, None): The determination to set for the alert.
            Defaults to None.

        """
        self._update_headers(use_graph_api=True)
        request_url = self._get_full_url(
            "update_alert",
            use_graph=True,
            alert_id=alert_id,
        )
        payload = {}
        if status:
            payload["status"] = status
        if classification:
            payload["classification"] = classification
        if determination:
            payload["determination"] = determination

        self._execute_request_with_retry(
            self.session.patch,
            request_url,
            alert_id,
            json=payload,
        )

    def get_alerts_by_ids(self, alert_ids: list[str]) -> list[AlertWithEvidence]:
        """Get alerts by a list of IDs.

        Args:
            alert_ids (list[str]): A list of alert IDs to fetch.

        Returns:
            list[AlertWithEvidence]: A list of alert objects.
        """
        fetched_alerts = []
        for alert_id in alert_ids:
            try:
                fetched_alerts.append(self.get_alert(alert_id))
            except Exception as e:
                is_not_found = (
                    isinstance(e, NotFoundItemException)
                    or e.__class__.__name__ == "NotFoundItemException"
                )
                if is_not_found:
                    self.not_found_alert_ids.add(alert_id)
                    if self.siemplify:
                        self.siemplify.LOGGER.warn(
                            f"Alert {alert_id} wasn't found in Microsoft 365 "
                            f"Defender. Skipping. Error: {e}"
                        )
                else:
                    if self.siemplify:
                        self.siemplify.LOGGER.error(
                            f"Failed to fetch alert {alert_id} from Microsoft 365 "
                            f"Defender. Error: {e}"
                        )
                    raise

        return fetched_alerts

    def get_incidents(
        self,
        existing_incidents: Dict[str, Any],
        limit: int,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        statuses: List[str],
        detection_source: List[str],
        service_source: List[str],
        connector_starting_time: int,
        python_process_timeout: int,
        is_tracking_enabled: bool = False,
        assignees: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        Get incidents
        :param existing_incidents: {dict} Dict with existing incident / alerts data
        :param limit: {int} The limit for results
        :param start_time: {datetime} The start datetime from where to fetch
        :param end_time: {datetime} The end datetime to fetch incidents up to
        :param statuses: {List[str]} List of statuses of incidents to fetch
        :param detection_source: {List[str]} List of detection sources to fetch
        when using graph api
        :param service_source: {List[str]} List of service sources to fetch
        when using graph api
        :param connector_starting_time: {int} Connector starting time in UNIX
        :param python_process_timeout: {int} Python process timeout in secs
        :param is_tracking_enabled: {bool} Specifies if alerts tracking is enabled
        :param assignees: {List[str]} List of assignees of incidents to fetch
        :param tags: {List[str]} List of tags of incidents to fetch
        :return: {list} The list of filtered Incident objects
        """

        if self.siemplify is None:
            raise Microsoft365DefenderException(
                "Please initialize manager with siemplify parameter filled"
            )
        self._update_headers(use_graph_api=True)
        self._enable_prefer_header()
        request_url = self._get_full_url("list_incidents_graph", use_graph=True)
        additional_filters = {"status": statuses}
        if assignees:
            additional_filters["assignedTo"] = assignees

        params = self._build_api_params(
            start_time=start_time,
            end_time=end_time,
            additional_filters=additional_filters,
            graph=True,
        )

        pagination_limit = (
            limit
            if not (assignees or tags)
            else max(limit * 5, INCIDENTS_LIMIT_PER_REQUEST)
        )
        incidents_data = self._paginate_results(
            method="GET",
            url=request_url,
            params=params,
            limit=pagination_limit,
            connector_starting_time=connector_starting_time,
            python_process_timeout=python_process_timeout,
        )
        filtered_incidents = []

        incident_data_sorted = sorted(
            incidents_data, key=lambda incident: incident["lastUpdateDateTime"]
        )

        for incident_data in incident_data_sorted:
            if len(filtered_incidents) >= limit:
                break

            if is_approaching_timeout(
                connector_starting_time=connector_starting_time,
                python_process_timeout=python_process_timeout,
                timeout_threshold=FETCHING_TIMEOUT_TRESHOLD,
            ):
                self.siemplify.LOGGER.info(
                    "Timeout is approaching. Connector will gracefully exit"
                )
                break

            if assignees:
                incident_assignee = str(incident_data.get("assignedTo") or "").strip()
                if not any(
                    a.strip().lower() == incident_assignee.lower()
                    for a in assignees
                    if a
                ):
                    continue

            if tags:
                incident_tags_list = (
                    (incident_data.get("customTags") or [])
                    + (incident_data.get("tags") or [])
                )
                formatted_tags = [
                    t.strip().lower()
                    if isinstance(t, str)
                    else str(t.get("name", "")).strip().lower()
                    if isinstance(t, dict)
                    else ""
                    for t in incident_tags_list
                ]
                if not any(
                    any(target_tag.strip().lower() == t for t in formatted_tags)
                    for target_tag in tags
                    if target_tag
                ):
                    continue

            incident = self.parser.build_incident_object(raw_data=incident_data)

            existing_alerts = set(existing_incidents.get(str(incident.incident_id), []))

            try:
                self.siemplify.LOGGER.info(
                    f"Fetching alerts for incident - {incident.incident_id}"
                )
                incident.alerts = self.get_incident_alerts(
                    incident=incident,
                    incidents_start_time=start_time,
                    existing_alerts=existing_alerts,
                    detection_source=detection_source,
                    service_source=service_source,
                    is_tracking_enabled=is_tracking_enabled,
                )
            except TooManyRequestsError as err:
                self.siemplify.LOGGER.error(
                    "Too many queries were executed to Graph alerts API. "
                    "Rate limit is reached. The connector will stop fetching new "
                    "alerts and process only fully fetched incidents."
                )
                self.too_many_request_last_occurrence = err.encountered_at
                break

            if incident.alerts or (
                incident.alerts is None
                and str(incident.incident_id) not in existing_incidents
            ):
                filtered_incidents.append(incident)

        self._disable_prefer_header()

        return filtered_incidents

    def get_incident(self, incident_id: str) -> Incident:
        """
        Get single incident details.
        :param incident_id: {str} Incident ID.
        :return: {Incident} The parsed Incident object.
        """
        self._update_headers(use_graph_api=True)
        request_url = self._get_full_url(
            "update_incident", use_graph=True, incident_id=incident_id
        )
        response = self.session.get(request_url)

        if response.status_code == 404:
            raise NotFoundItemException(
                f'incident "{incident_id}" wasn\'t found in Microsoft 365 Defender'
            )

        validate_response(response)
        return self.parser.build_incident_object(response.json())

    def get_incident_alerts(
        self,
        incident: Incident,
        incidents_start_time: datetime.datetime,
        existing_alerts: Set[str],
        detection_source: List[str],
        service_source: List[str],
        is_tracking_enabled: bool = False,
    ):
        """
        Get alerts from incidents either from its data or from new Graph API
        :param incident: {Incident} Parsed incident data
        :param incidents_start_time: {datetime} The start datetime from where to fetch
        :param existing_alerts: {Set[str]} Existing alerts ids set to filter our
        already fetched
        :param detection_source: {List[str]} List of detection sources to fetch
        alerts when using graph api
        :param service_source: {List[str]} List of service sources to fetch alerts
        when using graph api
        :param is_tracking_enabled: {bool} Specifies if alerts tracking is enabled
        :return: {list} The list of filtered Incident objects
        """

        alerts = [
            self.parser.build_alert_object(raw_data=raw_json)
            for raw_json in incident.raw_data.get("alerts", [])
        ]
        alerts_start_time = incidents_start_time
        if self.use_graph_api_for_alerts:
            self._update_headers(use_graph_api=True)
            self._enable_prefer_header()

            try:
                request_uri = self._get_full_url("get_alerts", use_graph=True)
                additional_filters = {
                    "incidentId": incident.incident_id,
                    "detectionSource": detection_source,
                    "serviceSource": service_source,
                }
                params = self._build_api_params(
                    additional_filters=additional_filters,
                    graph=True,
                )

                alerts_data = self._paginate_results(
                    method="GET",
                    url=request_uri,
                    params=params,
                    limit=ALERTS_LIMIT_PER_REQUEST,
                    limit_per_request=ALERTS_LIMIT_PER_REQUEST,
                )
                if alerts_data:
                    alerts = [
                        self.parser.build_alert_with_evidence_object(raw_data=raw_json)
                        for raw_json in alerts_data
                    ]

            except APIPermissionError:
                self.siemplify.LOGGER.error(
                    "Application that is used for the connector doesn't have all "
                    "of the necessary permissions. Please check the documentation "
                    "for more information. The incidents will be processed based "
                    "on only Defender 365 data."
                )
                self.use_graph_api_for_alerts = False
            finally:
                self._update_headers()
                self._disable_prefer_header()

        alerts = self.get_filtered_alerts(
            alerts=alerts,
            existing_ids=existing_alerts,
            is_tracking_enabled=is_tracking_enabled,
        )
        self.siemplify.LOGGER.info(
            f"Fetching {len(alerts) if alerts is not None else 0} new alerts "
            f"since {alerts_start_time}"
        )

        return alerts

    def search_for_devices(
        self,
        table_names=None,
        start_time=None,
        end_time=None,
        user_query=None,
        fields=None,
        sort_field=None,
        sort_order=None,
        limit=None,
        custom_query=None,
    ):
        """
        Search for devices. Tries to use Graph API first, and falls back to legacy API
        on permission errors.

        Args:
            table_names (list): List of table names
            start_time (str): Start time for results
            end_time (str): End time for results
            user_query (str): User provided query to execute
            fields (str): Fields to return in results
            sort_field (str): Field to use for sorting
            sort_order (str): Order of sorting
            limit (int): Number of results to return
            custom_query (str): Query that is entirely provided by the user

        Returns:
            Tuple[list, str]: List of Device objects, final query string
        """
        if custom_query:
            query = custom_query
            if start_time and end_time:
                query += (
                    f"| where Timestamp between(datetime({start_time}) .. datetime({end_time}))"
                )
            query += f"| limit {limit}"
        else:
            query = self._build_request_query(
                table_names=table_names,
                start_time=start_time,
                end_time=end_time,
                user_query=user_query,
                fields=fields,
                sort_field=sort_field,
                sort_order=sort_order,
                limit=limit,
            )

        try:
            self._update_headers(use_graph_api=True)
            response = self.session.post(
                self._get_full_url("execute_query_graph", use_graph=True),
                json={"query": query},
            )

            if response.status_code == 400:
                error_message = (
                    response.json()
                    .get("error", {})
                    .get("message", str(response.content))
                )
                raise Microsoft365DefenderException(error_message)

            validate_response(response)

            devices = self.parser.build_device_objects(
                raw_data=response.json(), data_root_key="results"
            )

            return devices, query

        except APIPermissionError:
            if self.siemplify:
                self.siemplify.LOGGER.info(
                    "Couldn't execute search with Graph API due to permission error. "
                    "Falling back to legacy API."
                )

            self._update_headers(use_graph_api=False)
            response = self.session.post(
                self._get_full_url("execute_query"), json={"Query": query}
            )

            if response.status_code == 400:
                error_message = (
                    response.json()
                    .get("error", {})
                    .get("message", str(response.content))
                )
                raise Microsoft365DefenderException(error_message)  # pylint: disable=raise-missing-from

            validate_response(response)

            devices = self.parser.build_device_objects(
                raw_data=response.json(), data_root_key="Results"
            )

            return devices, query

    def build_query_string(
        self,
        ip_key,
        hostname_key,
        hash_key,
        user_key,
        url_key,
        email_key,
        cross_entity_operator,
        ip_entities,
        hostname_entities,
        hash_entities,
        user_entities,
        url_entities,
        email_entities,
    ):
        """
        Prepare the query string based on entities
        :param ip_key: {str} Key to use with IP entities
        :param hostname_key: {str} Key to use with Hostname entities
        :param hash_key: {str} Key to use with File Hash entities
        :param user_key: {str} Key to use with User entities
        :param url_key: {str} Key to use with URL entities
        :param email_key: {str} Key to use with Email Address entities
        :param cross_entity_operator: {str} Operator to use between entity types.
        Possible values: OR, AND.
        :param ip_entities: {list} List of IP entities to use in the query
        :param hostname_entities: {list} List of Hostname entities to use in the query
        :param hash_entities: {list} List of File Hash entities to use in the query
        :param user_entities: {list} List of User entities to use in the query
        :param url_entities: {list} List of URL entities to use in the query
        :param email_entities: {list} List of Email Address entities to use in the query
        :return: {str} The query string
        """
        queries = []

        if ip_key and ip_entities:
            queries.append(" or ".join([f"{ip_key} == '{ip}'" for ip in ip_entities]))

        if hostname_key and hostname_entities:
            queries.append(
                " or ".join(
                    [
                        f"{hostname_key} == '{hostname}'"
                        for hostname in hostname_entities
                    ]
                )
            )

        if hash_key and hash_entities:
            queries.append(
                " or ".join([f"{hash_key} == '{hash}'" for hash in hash_entities])
            )

        if user_key and user_entities:
            queries.append(
                " or ".join([f"{user_key} == '{user}'" for user in user_entities])
            )

        if url_key and url_entities:
            queries.append(
                " or ".join([f"{url_key} == '{url}'" for url in url_entities])
            )

        if email_key and email_entities:
            queries.append(
                " or ".join([f"{email_key} == '{email}'" for email in email_entities])
            )

        query_string = (
            " | where ".join(queries)
            if cross_entity_operator == AND_OPERATOR
            else " or ".join(queries)
        )

        return f"| where {query_string}" if query_string else ""

    def _build_request_query(
        self,
        table_names,
        start_time,
        end_time,
        user_query,
        fields,
        sort_field,
        sort_order,
        limit=DEFAULT_RESULTS_LIMIT,
    ):
        """
        Prepare the query string
        :param table_names: {list} List of table names
        :param start_time: {str} Start time for results
        :param end_time: {str} End time for results
        :param user_query: {str} User provided query to execute
        :param fields: {str} Fields to return in results
        :param sort_field: {str} Field to use for sorting
        :param sort_order: {str} Order of sorting
        :param limit: {int} Number of results to return
        """
        query = "union " if len(table_names) > 1 else ""
        query += f"{', '.join(table_names)}"
        query += (
            f"| where Timestamp between(datetime({start_time}) .. datetime({end_time}))"
        )

        if user_query:
            query += user_query

        if fields:
            query += f"| project {', '.join(fields)}"

        if sort_field:
            query += f"| top {limit} by {sort_field} {sort_order}"

        return query

    def _build_api_params(
        self,
        start_time=None,
        end_time=None,
        created_time=None,
        additional_filters=None,
        limit=None,
        graph=False,
    ):
        """Create filtration dictionary for API parameters.

        Args:
            start_time (str): Start time to fetch incidents from.
            end_time (str): End time to fetch incidents to.
            created_time (str): Start time to fetch alerts from.
            additional_filters (dict): Additional filters listed in a dict.
            limit (int): How many items should be fetched.
            graph (bool): True if using the graph API, False otherwise.

        Returns:
            dict: Dictionary of filters.
        """
        if additional_filters is None:
            additional_filters = {}

        filter_params = []

        if start_time:
            filter_name = "lastUpdateDateTime" if graph else "lastUpdateTime"
            filter_params.append(
                f"{filter_name} ge {start_time.strftime(FILTER_TIME_FORMAT)}"
            )

        if end_time:
            filter_name = "lastUpdateDateTime" if graph else "lastUpdateTime"
            filter_params.append(
                f"{filter_name} le {end_time.strftime(FILTER_TIME_FORMAT)}"
            )

        if created_time:
            filter_params.append(
                f"createdDateTime ge {created_time.strftime(FILTER_TIME_FORMAT)}"
            )

        for key, value in additional_filters.items():
            if not value:
                continue

            if isinstance(value, list):
                filter_value = "({})".format(
                    " or ".join(f"{key} eq '{val}'" for val in value)
                )
            else:
                filter_value = f"{key} eq '{value}'"
            filter_params.append(filter_value)

        params = {
            "$filter": " and ".join(filter_params) if filter_params else None,
            "$top": limit,
            "$skip": 0,
        }

        return params

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        start_offset=0,
        limit=None,
        limit_per_request=INCIDENTS_LIMIT_PER_REQUEST,
        connector_starting_time=None,
        python_process_timeout=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a request
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param start_offset: {int} The start offset of the results to fetch
        :param limit: {int} The limit of the results to fetch
        :param limit_per_request: {int} The limit of the results to fetch on each page
        :param connector_starting_time: {int} Optional connector starting time for timeout check
        :param python_process_timeout: {int} Optional process timeout for timeout check
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if params is None:
            params = {}

        params.update({"$skip": start_offset, "$top": limit_per_request})

        response = self.session.request(method, url, params=params, json=body)

        validate_response(response, err_msg)
        response_json = response.json()
        results = response_json.get("value", [])
        next_link = response_json.get("@odata.nextLink")

        if next_link:
            while next_link:
                if limit and len(results) >= limit:
                    break

                if (
                    connector_starting_time
                    and python_process_timeout
                    and is_approaching_timeout(
                        connector_starting_time=connector_starting_time,
                        python_process_timeout=python_process_timeout,
                        timeout_threshold=FETCHING_TIMEOUT_TRESHOLD,
                    )
                ):
                    if self.siemplify:
                        self.siemplify.LOGGER.info(
                            "Timeout is approaching during pagination. Gracefully exiting pagination."
                        )
                    break

                response = self.session.request(method, next_link, json=body)
                validate_response(response, err_msg)
                resp_json = response.json()
                results.extend(resp_json.get("value", []))
                next_link = resp_json.get("@odata.nextLink")
        else:
            results_per_request = len(results)
            while True:
                if results_per_request < limit_per_request:
                    break
                if limit and len(results) >= limit:
                    break

                if (
                    connector_starting_time
                    and python_process_timeout
                    and is_approaching_timeout(
                        connector_starting_time=connector_starting_time,
                        python_process_timeout=python_process_timeout,
                        timeout_threshold=FETCHING_TIMEOUT_TRESHOLD,
                    )
                ):
                    if self.siemplify:
                        self.siemplify.LOGGER.info(
                            "Timeout is approaching during pagination. Gracefully exiting pagination."
                        )
                    break

                params.update({"$skip": start_offset + len(results)})

                response = self.session.request(method, url, params=params, json=body)

                validate_response(response, err_msg)
                results_per_request = len(response.json().get("value", []))
                results.extend(response.json().get("value", []))

        return results

    def get_filtered_alerts(
        self,
        alerts: [Alert | AlertWithEvidence],
        existing_ids: [str],
        is_tracking_enabled: bool = False,
    ) -> [Alert | AlertWithEvidence]:
        """
        Filter already processed alerts

        Args:
            alerts ([Alert | AlertWithEvidence]): list of Alert or AlertWithEvidence
                objects
            existing_ids ([str]): list of existing ids to use for filtering
            is_tracking_enabled (bool): specifies if alerts tracking is enabled

        Returns:
            [Alert | AlertWithEvidence]: list of filtered Alert or AlertWithEvidence
                objects
        """
        id_key = ALERT_UNIQUE_ID_KEY if is_tracking_enabled else ALERT_ID_KEY

        if not is_tracking_enabled:
            return self.filter_old_alerts_containing_id(
                alerts=alerts,
                id_key=id_key,
                existing_ids=existing_ids,
            )

        return filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            id_key=id_key,
            existing_ids=existing_ids,
        )

    def filter_old_alerts_containing_id(
        self,
        alerts: [Alert | AlertWithEvidence],
        existing_ids: [str],
        id_key: str,
    ) -> [Alert | AlertWithEvidence]:
        """
        Filter already processed alerts containing id

        Args:
            alerts ([Alert | AlertWithEvidence]): list of Alert or AlertWithEvidence
                objects
            existing_ids ([str]): list of existing ids to use for filtering
            id_key (str): key of alert identifier

        Returns:
            [Alert | AlertWithEvidence]: list of filtered Alert or AlertWithEvidence
                objects
        """
        filtered_alerts = []
        processed_alert_ids = set(existing_ids)
        processed_alert_ids.update(get_alert_id_from_display_id(existing_id) for existing_id in existing_ids)

        for alert in alerts:
            alert_id = getattr(alert, id_key)

            if alert_id not in processed_alert_ids:
                filtered_alerts.append(alert)
            else:
                self.siemplify.LOGGER.info(
                    f"The alert {alert_id} skipped since it has been fetched before"
                )

        return filtered_alerts

    def _execute_request_with_retry(
        self,
        method: Callable,
        url: str,
        alert_id: str | None = None,
        **kwargs,
    ) -> requests.Response:
        """
        Executes an HTTP request with retry logic for handling
        429 Too Many Requests responses.

        Args:
            method: The HTTP method (e.g., "GET", "POST", "PATCH").
            url: The URL to send the request to.
            alert_id (str | None): The ID of the alert to update.
            kwargs: Additional arguments to pass to the request (e.g., params, json).

        Returns:
            The HTTP response object.
        """
        response = method(url, **kwargs)

        if response.status_code == HTTP_NOT_FOUND_STATUS_CODE and alert_id is not None:
            raise NotFoundItemException(
                f'Alert "{alert_id}" wasn\'t found in Microsoft 365 Defender.'
            )

        try:
            validate_response(response)
            return response

        except TooManyRequestsError as error:
            self.siemplify.LOGGER.info(
                f"Waiting for {error.retry_after or RETRY_SLEEP} seconds..."
            )
            wait_time = int(error.retry_after) + 2 if error.retry_after else RETRY_SLEEP
            time.sleep(wait_time)

            response = method(url, **kwargs)

            validate_response(response)
            return response
