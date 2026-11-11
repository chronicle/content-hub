from __future__ import annotations

import contextlib
import os
from datetime import datetime, timezone
import urllib.parse
from typing import Any, BinaryIO, Callable, Generator

import requests
from requests import Session
from google_threat_intelligence.core import api_data_parser as parser
from google_threat_intelligence.core import data_models
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.base.utils import NewLineLogger
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.types import Entity, SingleJson
from google_threat_intelligence.core.api_utils import (
    build_asm_entity_query_string,
    build_query_for_single_params,
    build_query_string,
    get_full_url,
    get_project_id,
    validate_agent_session_response,
    validate_gti_response,
    validate_response,
)
from google_threat_intelligence.core.constants import (
    AGENT_JSON_ACCEPT_HEADERS,
    AGENT_REQUEST_TIMEOUT_IN_SECONDS,
    AGENT_SESSION_ID_HEADER,
    ALERT_STATUSES,
    ASM_ISSUES_INITIAL_WINDOW_HOURS,
    ASM_ISSUES_MAX_WINDOW_HOURS,
    ASM_ISSUES_MAX_WINDOW_PROBES,
    ASM_ISSUES_MIN_WINDOW_HOURS,
    ASM_ISSUES_TIME_FORMAT,
    ASM_ISSUES_WINDOW_RESULTS_CEILING,
    ASMItemType,
    COMMENT_ENDPOINTS_MAPPING,
    DEFAULT_PAGE_SIZE,
    GTI_IDP_TOKEN_URL,
    GTI_ROOT,
    ITEMS_PER_PAGE,
    MANDIANT_ROOT,
    MAX_LIMIT,
    MAX_NOTIFICATIONS_LIMIT,
    Order,
    SEVERITIES,
    SEVERITY_MAPPING,
    VOTE_ENDPOINTS_MAPPING,
    WIDGET_CHRONICLE_THEME_COLORS,
)
from google_threat_intelligence.core.data_models import (
    ASMEntity,
    ASMIssue,
    DTMAlert,
    Graph,
    GraphDetails,
    IOCSearchResult,
    ThreatActor,
)
from google_threat_intelligence.core.exceptions import (
    FileSubmissionError,
    GoogleThreatIntelligenceExceptions,
    ProjectNotFoundError,
)
from google_threat_intelligence.core.utils import (
    WidgetComponentPreprocessor,
    adjust_time,
    fetch_mitre_data,
    get_next_page_url,
    get_search_window_total,
    is_window_walk_timeout,
    parse_entity_filters,
    prepare_entity_filter,
    prepare_entity_for_manager,
    prepare_hash_identifier,
)

def _collect_document_refs(payload: Any) -> list[str]:
    """Recursively collect document resource IDs or paths from a payload."""
    refs: list[str] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == "discoveryDocumentIds" and isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and item:
                        refs.append(item)
            elif k in ("documentId", "document_id") and isinstance(v, str) and v:
                refs.append(v)
            elif isinstance(v, (dict, list)):
                refs.extend(_collect_document_refs(v))
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, (dict, list)):
                refs.extend(_collect_document_refs(item))
    return refs


def _strip_gti_resource_prefix(name: str) -> str:
    """Strip leading slash and v1beta/ prefix from GTI resource name."""
    return name.lstrip("/").removeprefix("v1beta/")


class ApiManager:
    def __init__(
        self,
        api_root: str,
        session: Session,
        asm_project_name: str,
        logger: NewLineLogger,
    ) -> None:
        """Manager for handling API interactions

        Args:
            api_root (str): API root URL
            session (Session): initialized session object to be used in API session
            asm_project_name (str): ASM project name
            logger (NewLineLogger): logger object

        """
        self.api_root = api_root + "/" if not api_root.endswith("/") else api_root
        self.session = session
        self.asm_project_name = asm_project_name
        self.logger = logger
        self.project_id = None
        self.empty_scan_end: str | None = None

    def test_connectivity(self) -> None:
        """Test connectivity."""
        try:
            response = self.session.get(
                get_full_url(
                    self.api_root,
                    "asm_ping" if self.asm_project_name else "ping",
                )
            )
        except UnicodeEncodeError as exc:
            raise ValueError(
                "API key contains unsupported unicode characters."
            ) from exc

        validate_response(response)

        if self.asm_project_name:
            project_id = get_project_id(
                response.json()["result"],
                self.asm_project_name,
            )

            if not project_id:
                raise ProjectNotFoundError(
                    f"the following ASM Project wasn't found: {self.asm_project_name}."
                    "Please check the integration configuration."
                )

    def set_project_id(self, project_name) -> None:
        """Set Project ID from project name.

        Args:
            project_name: {str} The name of the Project

        """
        project_name = project_name or self.asm_project_name

        url = get_full_url(self.api_root, "index_projects")
        if not project_name:
            self.project_id = None
            return

        response = self.session.get(url)
        validate_response(response)
        projects = response.json()["result"]
        project_id = get_project_id(projects, project_name)

        if not project_id:
            raise ProjectNotFoundError(
                f"the following ASM Project wasn't found: {project_name}."
            )

        self.project_id = project_id

    def get_graph_details(self, graph_id: str, links_limit: int) -> GraphDetails:
        """Get graph details by graph id

        Args:
            graph_id (str): graph id
            links_limit (int): maximum links amount to return

        Returns:
            GraphDetails: GraphDetails object

        """
        response = self.session.get(
            get_full_url(self.api_root, "get_graph_details", graph_id=graph_id)
        )

        validate_response(response)
        return parser.build_graph_details_object(
            response.json(), links_limit=links_limit
        )

    def search_graphs(self, query: str, sort_field: str, graphs_limit: int) -> [Graph]:
        """Search graphs

        Args:
            query (str): query filter to search for graphs
            sort_field (str): sort field for the graphs
            graphs_limit (int): maximum graphs amount to return

        Returns:
            [Graphs]: list of Graphs object

        """
        url = get_full_url(self.api_root, "search_graphs")
        params = {
            "filter": query,
            "order": sort_field,
            "limit": graphs_limit,
            "attributes": "graph_data",
        }

        return self.paginate_results(
            url=url,
            limit=graphs_limit,
            parser_method="build_graph_objects",
            params=params,
        )

    def paginate_results(
        self,
        url: str,
        limit: int,
        parser_method: str,
        params: dict[str, Any] | None = None,
        show_entity_status: bool = False,
    ) -> list[Any]:
        """Paginate results

        Args:
            url: url to send request to.
            limit: limit for the results.
            parser_method: parser method to build the result.
            params: request query params, defaults to None.
            show_entity_status: Return error message for entity.

        Returns:
            list[Any]: list of results

        """
        params = params or {}
        results = []
        response = None
        params["limit"] = min(limit, ITEMS_PER_PAGE)

        while True:
            url = parser.get_next_page_url(response.json()) if response else url

            if len(results) >= limit or not url:
                break

            params = {} if response else params
            response = self.session.get(url, params=params)
            validate_response(response, show_entity_status=show_entity_status)
            results.extend(
                getattr(parser, parser_method)(
                    parser.get_results_from_raw_data(response.json())
                )
            )

        return results[:limit]

    def update_alert(self, alert_id: str, status: str) -> DTMAlert:
        """Update alert status

        Args:
            alert_id (str): Alert id
            status (str): Status to update

        Returns:
            DTMAlert: DTMAlert object

        """
        return self.patch_dtm_alert(alert_id, payload={"status": status})

    def update_dtm_alert_tags(
        self, alert_id: str, tags: list[str], append: bool = False
    ) -> DTMAlert:
        """
        Adds tag to existing alert
        Args:
            alert_id (str): Alert id
            tags (str): Tags list
            append (bool): If true then tags will be appended to existing tags

        Returns:
            DTMAlert: DTMAlert object
        """

        if append:
            existing_tags = self.get_dtm_alert(alert_id=alert_id).raw_data.get(
                "tags", []
            )
            tags.extend(existing_tags)

        tags = list(set(tags))

        return self.patch_dtm_alert(alert_id, payload={"tags": tags})

    def update_analysis_text_on_alert(self, alert_id: str, text: str) -> None:
        """Updates the analysis text on an alert object

        Args:
            alert_id (str): Alert id
            text (str): Text of the analysis

        Returns:
            None

        """
        response = self.session.put(
            url=get_full_url(
                api_root=self.api_root,
                endpoint_id="set_dtm_alert_analysis",
                alert_id=alert_id.lower(),
            ),
            json={"analysis": text},
        )
        validate_response(response)

    def upload_file_to_alerts_analysis(
        self, alert_id: str, file_paths: list[str]
    ) -> None:
        """Uploads files to alert`s analysis

        Uses `contextlib.ExitStack` to guarantee that a dynamic number of
        successfully opened files are all properly closed.

        Args:
            alert_id (str): Alert id
            file_paths (list): List of the absolute file paths

        Returns:
            None
        """
        if not file_paths:
            return

        with contextlib.ExitStack() as stack:
            files = _build_multipart_files(stack, file_paths)

            response = self.session.post(
                get_full_url(
                    api_root=self.api_root,
                    endpoint_id="upload_file_to_alerts_analysis",
                    alert_id=alert_id,
                ),
                files=files,
            )
            validate_gti_response(response)

    def add_comment_to_entity(self, entity: Entity, comment: str):
        """Add vote to entity
        Args:
            entity: Siemplify entity
            comment: comment to add to entities
        return:
            Bool(True/False)
        """
        identifier = prepare_entity_for_manager(entity)
        endpoint_id = COMMENT_ENDPOINTS_MAPPING.get(entity.entity_type)
        if endpoint_id:
            url = get_full_url(self.api_root, endpoint_id, identifier=identifier)
        else:
            raise GoogleThreatIntelligenceExceptions("Not supported entity type")

        payload = {"data": {"type": "comment", "attributes": {"text": comment}}}
        response = self.session.post(url=url, json=payload)
        if response.status_code == 409:  # duplicate entries considered as success
            return True
        validate_response(response)

        return True

    def _get_list_dtm_monitor_page(
        self, sort_field: str, order: Order = Order.ASC, page_size: int = 20, page=None
    ):
        url = get_full_url(self.api_root, "list_dtm_monitors")
        params = {
            "sort": sort_field,
            "order": order.value,
            "page": page,
            "size": page_size,
        }
        response = self.session.get(url, params=params)
        validate_response(response)
        return response

    def _get_list_dtm_monitor_generator(
        self, sort_field: str, order: Order = Order.ASC, page_size: int = 10
    ) -> Generator[dict, None, None]:
        self.logger.info("Fetching first page of monitor list")
        response = self._get_list_dtm_monitor_page(sort_field, order, page_size)
        yield from response.json().get("monitors", [])
        while next_page_link := get_next_page_url(response.headers):
            response = self.session.get(next_page_link)
            yield from response.json().get("monitors", [])

    def get_dtm_monitor_id_by_name(
        self, monitor_names: list
    ) -> Generator[Any, None, None]:
        """Get monitor id by name
        Args:
            monitor_names (str): monitor name
        Returns:
            str: monitor id
        """
        monitors = self._get_list_dtm_monitor_generator("name")
        monitors = filter(lambda v: v["name"] in monitor_names, monitors)
        monitors = map(lambda v: v["id"], monitors)
        yield from monitors

    def get_dtm_alerts(
        self,
        timestamp: str,
        limit: int,
        siemplify: SiemplifyConnectorExecution,
        lowest_severity: str = "",
        monitor_ids: list[str] | None = None,
        monitor_names: list[str] | None = None,
        alert_types: list[str] | None = None,
        existing_ids: list[str] | None = None,
    ) -> list[DTMAlert]:
        """Get alerts

        Args:
            timestamp (str): timestamp filter to get alert from
            limit (int): limit for results
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
            lowest_severity (str): lowest severity filter
            monitor_ids (list[str] | None ): list of monitor ids filters
            monitor_names (list[str] | None ): list of monitor name filters
            alert_types (list[str] | None ): list of alert type filters
            existing_ids (list[str] | None ): list of ids to filter

        Returns:
            [DTMAlert]: list of DTMAlert dataclasses

        """
        url = get_full_url(self.api_root, "get_dtm_alerts")

        if monitor_names:
            self.logger.info("Fetching monitor ids by names")
            monitor_ids.extend(self.get_dtm_monitor_id_by_name(monitor_names))

        monitor_ids = list(set(monitor_ids))

        self.logger.info(f"Resolved monitor IDs: {monitor_ids}")
        params = {
            "since": timestamp,
            "size": max(limit, MAX_LIMIT),
            "severity": (
                SEVERITIES[SEVERITIES.index(lowest_severity.lower()):]
                if lowest_severity
                else SEVERITIES
            ),
            "monitor_id": monitor_ids,
            "alert_type": alert_types,
            "order": "asc",
            "refs": "true",
            "monitor_name": "true",
            "status": ALERT_STATUSES,
        }

        return self._paginate_results(url, limit, siemplify, existing_ids, params)

    def add_vote_to_entity(self, entity: Entity, vote: str):
        """Add vote to entity
        Args:
            entity: Siemplify entity
            vote: str
        return:
            Bool(True/False)
        """
        identifier = prepare_entity_for_manager(entity)
        endpoint_id = VOTE_ENDPOINTS_MAPPING.get(entity.entity_type)
        if endpoint_id:
            url = get_full_url(self.api_root, endpoint_id, identifier=identifier)
        else:
            raise GoogleThreatIntelligenceExceptions("Not supported entity type")

        payload = {"data": {"type": "vote", "attributes": {"verdict": vote.lower()}}}
        response = self.session.post(url=url, json=payload)
        # Action returns 409 when duplicate entries (considered as success)
        if response.status_code == 409:
            return True
        validate_response(response)
        return True

    def _paginate_results(
        self,
        full_url: str,
        limit: int,
        siemplify: SiemplifyConnectorExecution,
        existing_ids: [str] = None,
        params: dict | None = None,
    ) -> list[DTMAlert]:
        """Paginate the results

        Args:
            full_url (str): full url to send request to
            limit (int): limit for the results to fetch
            existing_ids ([str]): list of ids to filter
            params (dict): request params dict
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object

        Returns:
            [DTMAlert]: list of DTMAlert dataclasses

        """
        results, next_page_link, response = [], None, None

        while True:
            if response:
                if not next_page_link or (limit is not None and len(results) >= limit):
                    break

                full_url = next_page_link
                params = {}

            response = self.session.get(full_url, params=params)

            current_link = response.headers.get("link", "")
            if self.api_root not in current_link:
                updated_link = current_link.replace(MANDIANT_ROOT, GTI_ROOT)
                response.headers.update({"link": updated_link})

            validate_response(response)
            next_page_link = get_next_page_url(response.headers)

            results.extend(
                filter_old_alerts(
                    siemplify,
                    alerts=parser.build_dtm_alert_objects(response.json()),
                    existing_ids=set(existing_ids) if existing_ids else [],
                    id_key="alert_id",
                )
            )

        return results[:limit] if limit else results

    def get_asm_entity_by_id(self, entity_id) -> ASMEntity:
        """Fetches details of a given entity id.

        Args:
            entity_id: {str} entity id to fetch details of

        Returns:
            ASMEntity: ASMEntity object

        """
        url = get_full_url(self.api_root, "entity_full_details", entity_id=entity_id)

        response = self.session.get(url)
        validate_response(response)
        response_json = response.json()

        if not response_json["success"]:
            raise GoogleThreatIntelligenceExceptions(response_json["message"])

        return parser.build_asm_entity_object(response_json)

    def search_issues(
        self,
        limit: int,
        script_starting_time: int,
        execution_deadline: int,
        **kwargs,
    ) -> list[ASMIssue]:
        """Searches issues that match specified criteria up to limit.

        Args:
            limit: {int} Limitation of how much issues to fetch
            script_starting_time: {int} Script starting time
            execution_deadline: {int} Execution deadline
            kwargs: {Dict[str, Any]} the dictionary that contains all kwargs params
                                    specified for filtering, check
                                    build_query_string for details.

        Returns:
            [Issue]: list of Issue dataclasses

        """
        page_number = 0
        filtered_issues = []

        query_string = build_query_string(
            entity_name=kwargs.get("entity_name"),
            issue_ids=kwargs.get("issue_ids"),
            entity_ids=kwargs.get("entity_ids"),
            tags=kwargs.get("tags"),
            time_parameter=kwargs.get("time_parameter"),
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            status=kwargs.get("status"),
            lowest_severity=kwargs.get("lowest_severity"),
        )

        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="search_issues",
            query_string=query_string,
        )

        while True:
            if is_approaching_timeout(script_starting_time, execution_deadline):
                self.logger.info("Timeout is approaching. Action will gracefully exit")
                break

            issues, more_pages = self.search_issues_by_page(
                url=url,
                page_number=page_number,
                parser_method=parser.build_issue_objects,
            )
            filtered_issues.extend(issues)

            if len(filtered_issues) >= limit or not more_pages:
                self.logger.info(
                    f"Reached Maximum count of entities to process of {limit} !"
                )
                break

            page_number += 1

        return filtered_issues[:limit]

    def search_asm_entities(
        self,
        limit: int,
        script_starting_time: int,
        execution_deadline: int,
        **kwargs,
    ) -> list[ASMEntity]:
        """Searches ASM entities that match specified criteria up to limit.

        Args:
            limit: {int} Limitation of how much issues to fetch
            script_starting_time: {int} Script starting time
            execution_deadline: {int} Execution deadline
            kwargs: {Dict[str, Any]} the dictionary that contains all kwargs params
                    specified for filtering, check build_query_string for details.

        Returns:
            [ASMEntity]: list of Issue dataclasses

        """
        page_number = 0
        filtered_issues = []

        names = kwargs.get("entity_name", [])
        query_string = build_asm_entity_query_string(
            names=names,
            critical_or_high=kwargs.get("critical_or_high"),
            tags=kwargs.get("tags"),
            minimum_vulns=kwargs.get("vuln_count_gte"),
            minimum_issues=kwargs.get("issue_count_gte"),
        )

        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="search_entities",
            query_string=query_string,
        )

        while True:
            if is_approaching_timeout(script_starting_time, execution_deadline):
                self.logger.info("Timeout is approaching. Action will gracefully exit")
                break

            issues, more_pages = self.search_issues_by_page(
                url=url,
                page_number=page_number,
                parser_method=parser.build_asm_entity_objects,
            )
            filtered_issues.extend(issues)

            if len(filtered_issues) >= limit or not more_pages:
                self.logger.info(
                    f"Reached Maximum count of entities to process of {limit} !"
                )
                break

            page_number += 1

        return filtered_issues[:limit]

    def search_issues_by_page(self, url, page_number, parser_method, limit=None):
        """Searches issues that match query string criteria and returns
        specified page results.
        If the provided limit is less than the default page size,
        the default page size will be used instead.

        Params:
            url: {str} the url to fetch.
            page_number: {str} result page_number to fetch.

        Returns:
            Tuple(Hits {List[obj]}, More {bool})

        """
        response_json = self._fetch_search_page(url, page_number, limit)
        if response_json["success"]:
            return (
                parser_method(response_json["result"]["hits"]),
                response_json["result"]["more"],
            )

        self.logger.error(f"Failed to fetch data - {response_json['message']}")

        return [], False

    def _fetch_search_page(
        self,
        url: str,
        page_number: int,
        limit: int | None = None,
    ) -> SingleJson:
        """Fetches a single raw page of an ASM search.
        If the provided limit is less than the default page size,
        the default page size will be used instead.

        Args:
            url: the search url to fetch.
            page_number: result page number to fetch.
            limit: requested amount of results.

        Returns:
            The raw json response of the search endpoint.

        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        page_size = max(DEFAULT_PAGE_SIZE, limit) if limit else DEFAULT_PAGE_SIZE
        params = {"page_size": page_size, "page": page_number}

        response = self.session.get(url, params=params)
        validate_response(response)

        return response.json()

    def update_issue(self, issue_id: str, status: str) -> dict:
        """Updates issue in ASM with new status.

        Args:
            issue_id: issue id to update in ASM
            status: new issue status

        Returns:
            the updated issue data

        """
        data = {"status": status}
        url = get_full_url(
            api_root=self.api_root, endpoint_id="update_issue", issue_id=issue_id
        )

        response = self.session.post(url, json=data)
        validate_response(response)
        response_json = response.json()

        if not response_json["success"]:
            raise GoogleThreatIntelligenceExceptions(response_json["message"])

        return response_json

    def get_issues(
        self,
        severity: int,
        limit: int,
        last_seen_after: str,
        status_filter: list[str],
        issue_name_filter: set[str] = None,
        siemplify: SiemplifyConnectorExecution = None,
        existing_ids: list[str] | None = None,
        *,
        connector_starting_time: int | None = None,
        python_process_timeout: int | None = None,
    ) -> list[ASMIssue]:
        """Fetches a list of issues from ASM.

        Issues are searched in a sliding `last_seen` time window that starts at
        `last_seen_after`. A window without new issues is skipped and the next
        window is doubled (up to ASM_ISSUES_MAX_WINDOW_HOURS), so long periods
        without issues are crossed within a single connector iteration instead
        of one fixed window per iteration. A window holding more than
        ASM_ISSUES_WINDOW_RESULTS_CEILING issues is halved (down to
        ASM_ISSUES_MIN_WINDOW_HOURS) before being paginated to keep the amount
        of requests per iteration bounded.
        The end of the last window confirmed to hold no new issues is stored in
        `self.empty_scan_end`, so the progress can be persisted by the caller even
        when no issue is returned.

        Args:
            severity: lowest severity to fetch
            limit: max issues to fetch
            last_seen_after: reference time to fetch events
            issue_name_filter (set[str]): Issue names to filter by.
            status_filter (list[str]): Statuses to filter by.
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
            existing_ids (list[str] | None): list of ids to filter
            connector_starting_time (int | None): connector start time in unix ms.
                Used together with `python_process_timeout` to stop walking through
                empty windows when the connector timeout approaches.
            python_process_timeout (int | None): connector timeout in seconds

        Returns:
            List of ASMIssue objects

        """
        self.empty_scan_end = None
        existing_ids = set(existing_ids) if existing_ids else set()
        allow_list, block_list = parse_entity_filters(issue_name_filter)
        name_filter: Callable[[ASMIssue], bool] = prepare_entity_filter(
            extractor=lambda issue: issue.pretty_name,
            allow_list=allow_list,
            block_list=block_list,
        )

        window_start: str = last_seen_after
        window_hours: float = ASM_ISSUES_INITIAL_WINDOW_HOURS

        for _ in range(ASM_ISSUES_MAX_WINDOW_PROBES):
            now: datetime = datetime.utcnow()
            window_end: datetime = adjust_time(window_start, hours=window_hours, now=now)
            window_end_str: str = window_end.strftime(ASM_ISSUES_TIME_FORMAT)
            url: str = self._build_issues_search_url(
                last_seen_after=window_start,
                last_seen_before=window_end_str,
                severity=severity,
                status_filter=status_filter,
            )
            self.logger.info(
                f"Searching for issues last seen between {window_start} and "
                f"{window_end_str}"
            )
            first_page: SingleJson = self._fetch_issues_search_result(url, 0, limit)
            total: int = get_search_window_total(first_page)

            if (
                total > ASM_ISSUES_WINDOW_RESULTS_CEILING
                and window_hours > ASM_ISSUES_MIN_WINDOW_HOURS
            ):
                window_hours = max(window_hours / 2, ASM_ISSUES_MIN_WINDOW_HOURS)
                self.logger.info(
                    f"Found {total} issues in the window. Narrowing the window to "
                    f"{window_hours:g} hours."
                )
                continue

            issues: list[ASMIssue] = self._collect_new_issues(
                url,
                first_page,
                limit,
                siemplify=siemplify,
                existing_ids=existing_ids,
                name_filter=name_filter,
            )
            if len(issues) > limit:
                self.logger.info(
                    f"Returning the {limit} earliest of the {len(issues)} new issues by last "
                    "seen time."
                )
            if issues:
                return sorted(issues, key=lambda alert: alert.last_seen_ms)[:limit]

            self.logger.info(
                f"No new issues were found between {window_start} and "
                f"{window_end_str} (issues in window: {total})."
            )
            if window_end >= now:
                self.logger.info("Reached the current time. Stopping the search.")
                return []

            self.empty_scan_end = window_end_str
            if is_window_walk_timeout(connector_starting_time, python_process_timeout):
                self.logger.info(
                    "Approaching connector timeout. Stopping the search for issues "
                    f"at {window_end_str}."
                )
                return []

            window_start = window_end_str
            window_hours = min(window_hours * 2, ASM_ISSUES_MAX_WINDOW_HOURS)
            self.logger.info(f"Continuing the search with a {window_hours:g} hour window.")

        self.logger.info(
            f"Reached the maximum amount of {ASM_ISSUES_MAX_WINDOW_PROBES} search "
            f"windows for this iteration. Stopping the search for issues at "
            f"{self.empty_scan_end}."
        )
        return []

    def _build_issues_search_url(
        self,
        last_seen_after: str,
        last_seen_before: str,
        severity: int,
        status_filter: list[str],
    ) -> str:
        """Builds the ASM issues search url for the given `last_seen` window.

        Args:
            last_seen_after: start of the `last_seen` window
            last_seen_before: end of the `last_seen` window
            severity: lowest severity to fetch
            status_filter (list[str]): Statuses to filter by.

        Returns:
            The search issues url

        """
        query_string = build_query_for_single_params(
            last_seen_after=last_seen_after,
            last_seen_before=last_seen_before,
            severity_lte=severity,
        )
        status_query_list = (f"status_new:{status.lower()}" for status in status_filter)
        query_string += " ".join(status_query_list)

        return get_full_url(
            api_root=self.api_root,
            endpoint_id="search_issues",
            query_string=query_string,
        )

    def _fetch_issues_search_result(self, url: str, page_number: int, limit: int) -> SingleJson:
        """Fetches a single page of an ASM issues search and returns its result.

        Args:
            url: the search url to fetch.
            page_number: result page number to fetch.
            limit: requested amount of results.

        Returns:
            The `result` object of the search response (hits, more, total)

        Raises:
            GoogleThreatIntelligenceExceptions: if the API reports a failed search

        """
        response_json: SingleJson = self._fetch_search_page(url, page_number, limit)
        if not response_json["success"]:
            raise GoogleThreatIntelligenceExceptions(
                f"Failed to fetch issues - {response_json['message']}"
            )

        return response_json["result"]

    def _collect_new_issues(
        self,
        url: str,
        first_page: SingleJson,
        limit: int,
        *,
        siemplify: SiemplifyConnectorExecution,
        existing_ids: set[str],
        name_filter: Callable[[ASMIssue], bool],
    ) -> list[ASMIssue]:
        """Paginates through a search window and returns the issues that were not
        fetched before and pass the issue name filter.

        The ids of the collected issues are added to `existing_ids`, so an issue
        that shows up again on a later page of the window is not collected twice.

        Args:
            url: the search url of the window.
            first_page: already fetched first page result of the window.
            limit: requested amount of results.
            siemplify: SiemplifyConnectorExecution object.
            existing_ids: ids of already fetched issues.
            name_filter: predicate that checks the issue name filter.

        Returns:
            List of new ASMIssue objects

        """
        new_issues: list[ASMIssue] = []
        fetched_count: int = 0
        known_count: int = 0
        page_number: int = 0
        result: SingleJson = first_page

        while True:
            issues: list[ASMIssue] = parser.build_issue_objects(result.get("hits", []))
            unknown_issues: list[ASMIssue] = filter_old_alerts(
                siemplify,
                alerts=issues,
                existing_ids=existing_ids,
                id_key="issue_id",
            )
            page_issues: list[ASMIssue] = list(filter(name_filter, unknown_issues))
            existing_ids.update(issue.issue_id for issue in page_issues)
            new_issues.extend(page_issues)
            fetched_count += len(issues)
            known_count += len(issues) - len(unknown_issues)
            if not result.get("more"):
                break

            page_number += 1
            result = self._fetch_issues_search_result(url, page_number, limit)

        if fetched_count:
            self.logger.info(
                f"Issues in the window: {fetched_count} (already ingested: {known_count}, "
                f"filtered out by name: {fetched_count - known_count - len(new_issues)}, "
                f"new: {len(new_issues)})."
            )

        return new_issues

    def get_issue_details(self, issue_id: str) -> data_models.ASMIssue:
        """Fetches details of a given issue id

        Args:
            issue_id: issue id to fetch details of

        Returns:
            datamodels.ASMIssue object

        """
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})
        url = get_full_url(
            api_root=self.api_root, endpoint_id="get_issue_details", issue_id=issue_id
        )
        response = self.session.get(url)
        validate_response(response)

        response_json = response.json()
        if not response_json["success"]:
            raise GoogleThreatIntelligenceExceptions(
                f"Failed to fetch details of issue "
                f"{issue_id} - {response_json['message']}"
            )

        return parser.build_asm_issue_object(response_json.get("result", {}))

    def get_related_iocs(self, ioc_type, identifier, relationship, limit):
        """Fetches related iocs for entity
        Args:
            ioc_type: entity type
            identifier: entity identifier
            relationship: entity relationship
            limit: max iocs to fetch
        Returns:
            [RelatedIOC]: list of DTMAlert RelatedIOC
        """
        endpoint_id = (
            "get_iocs_for_threat_actors"
            if ioc_type == "collections"
            else "get_related_iocs"
        )

        url = get_full_url(
            api_root=self.api_root,
            endpoint_id=endpoint_id,
            type=ioc_type,
            id=identifier,
            relationship=relationship,
        )
        return self.paginate_results(
            url,
            limit or ITEMS_PER_PAGE,
            "build_related_ioc_objects",
        )

    def get_related_associations(
        self,
        collection_type: str,
        identifier: str,
        relationship: str = "associations",
        association_types: list = None,
        limit: int = ITEMS_PER_PAGE,
    ) -> list[data_models.AssociationItem]:
        """Fetches related associations for a given entity."""
        if not association_types:
            association_types = []

        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="get_iocs_for_threat_actors",
            type=collection_type,
            id=identifier,
            relationship=relationship,
        )

        params = {}
        if association_types:
            filter_expression = " OR ".join(
                [
                    f'collection_type:"{collection_type}"'
                    for collection_type in association_types
                ]
            )
            params["filter"] = f"({filter_expression})"

        return self.paginate_results(
            url=url,
            limit=limit,
            parser_method="build_association_items_objects",
            params=params,
        )

    def get_threat_actor(self, name: str) -> list[ThreatActor]:
        """Fetches a list of Threat Actors.

        Args:
            name: threat actor name

        Returns:
            List of ThreatActor objects

        """
        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="get_threat_actor",
        )
        params = {
            "filter": f'collection_type:threat-actor name: "{name}"',
        }

        return self.paginate_results(
            url,
            ITEMS_PER_PAGE,
            "build_threat_actor_objects",
            params=params,
        )

    def retrieve_ioc(
        self, ioc: str, ioc_type: str, is_private_submission=False
    ) -> requests.Response:
        """Retrieves information about an IOC from the appropriate endpoint."""
        request_endpoint = "get_ioc_details"
        if is_private_submission:
            request_endpoint = "private_get_ioc_details"

        url = get_full_url(
            api_root=self.api_root,
            endpoint_id=request_endpoint,
            ioc_type=ioc_type,
            ioc=ioc,
        )
        response = self.session.get(url)
        return response

    def get_ioc_details(
        self,
        ioc: str,
        ioc_type: str,
        show_entity_status: bool = False,
        is_private_submission=False,
        raw_response: bool = False,
    ):
        """Retrieves detailed information about a specific IOC.

        Args:
            ioc (str): The value of the IOC.
            ioc_type (str): The type of the IOC .
            show_entity_status (bool, optional): Return error message for entity
            is_private_submission (bool): Whether the file submission is private.
            raw_response (bool): Returns raw api response

        Returns:
            IOC: IOC object

        """
        response = self.retrieve_ioc(
            ioc=ioc,
            ioc_type=ioc_type,
            is_private_submission=is_private_submission,
        )
        validate_response(response, show_entity_status=show_entity_status)
        if raw_response:
            return response.json()
        return parser.build_ioc_object(response.json(), ioc_type=ioc_type, ioc=ioc)

    def get_comments(
        self,
        ioc_type: str,
        ioc: str,
        limit: int,
        show_entity_status: bool = False,
    ):
        """Retrieves comments for a given entity.

        Args:
            ioc_type: The type of indicator of compromise (IOC).
            ioc: The indicator of compromise value.
            limit: The maximum number of comments to return.
            show_entity_status: Whether to include error messages related to
                                the entity's status.

        Returns:
            A list of Comment instances.

        """
        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="get_comments",
            ioc_type=ioc_type,
            ioc=ioc,
        )
        return self.paginate_results(
            url=url,
            limit=limit,
            parser_method="build_comment_objects",
            show_entity_status=show_entity_status,
        )

    def get_vulnerability_details(
        self,
        entity_identifier: str,
    ) -> data_models.Vulnerability:
        """Get Actor details
        Args:
            entity_identifier: The identifier
        Returns:
            datamodels.Vulnerability object
        """
        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="vulnerability_details",
            vulnerability=entity_identifier,
        )
        response = self.session.get(
            url,
            params={"rating_types": "predicted,analyst,unrated"},
        )
        validate_response(response)

        return parser.build_vulnerability_obj(response.json())

    def get_widget(
        self,
        entity: str,
        show_entity_status: bool = False,
        theme_colors: dict = None
    ):
        """Get Widget for given entity
        Args:
            entity {str}: entity identifier
            theme_colors {dict}: theme colors
            show_entity_status {bool}:  Return error message for entity
        Return
            {str}: widget for given entity
        """
        url = get_full_url(self.api_root, "get_widget")
        params = {"query": entity, **(theme_colors or WIDGET_CHRONICLE_THEME_COLORS)}

        response = self.session.get(url, params=params)
        validate_response(response, show_entity_status=show_entity_status)
        response_json = response.json()

        widget_link = response_json.get("data", {}).get("url")
        widget_link += "/summary"
        if response_json.get("data", {}).get("found"):
            return widget_link, WidgetComponentPreprocessor(
                widget_link, self.session
            ).prepare_cached_widget()
        return None, None

    def get_sandbox_data(
        self,
        file_hash: str,
        sandbox: str,
        show_entity_status: bool = False,
    ):
        """Get sandbox data
        Args:
            hash {str}:  hash
            sandbox {str}:  sandbox name
            show_entity_status {bool}: {bool} return error message for entity
        Return
            Sandbox: Sandbox dataclasses
        """
        identifier = prepare_hash_identifier(file_hash)
        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="get_sandbox_data",
            hash=identifier,
            sandbox=sandbox,
        )
        response = self.session.get(url)
        validate_response(response, show_entity_status=show_entity_status)
        return parser.build_sandbox_object(response.json())

    def get_mitre(
        self,
        file_hash: str,
        show_entity_status: bool = False,
        lowest_mitre_severity: str = "INFO",
    ):
        """Get Mitre for given entity
        Args:
            file_hash {str}:  hash
            show_entity_status {bool}: {bool} Return error message for entity
            lowest_mitre_severity {str}: {str} lowest mitre severity
        Return
            Mitre: Mitre dataclasses
        """
        identifier = prepare_hash_identifier(file_hash)
        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="get_mitre",
            entity=identifier,
        )
        response = self.session.get(url)
        validate_response(response, show_entity_status=show_entity_status)
        mitre_data = fetch_mitre_data(response.json(), lowest_mitre_severity)
        return parser.build_mitre_object(mitre_data)

    def submit_url_for_analysis(
        self,
        url: str,
        show_entity_status: bool = False,
        private_submission: bool = False,
    ) -> str:
        """Submits a URL for analysis.

        Args:
            url: The URL to analyze.
            show_entity_status: Whether to return an error message for the entity.
            private_submission: if submitted url is private

        Returns:
            The analysis ID.

        """
        endpoint_id = "urls"
        if private_submission:
            endpoint_id = "private_urls"
        response = self.session.post(
            get_full_url(
                api_root=self.api_root,
                endpoint_id=endpoint_id,
            ),
            data={"url": url},
        )
        validate_response(response, show_entity_status=show_entity_status)
        return parser.get_analysis_id(response.json())

    @staticmethod
    def get_file_content(file_path: str) -> bytes | None:
        """Reads and returns the binary content of the file.

        Args:
            file_path: Path to the file.

        Returns:
            bytes: File content in binary mode.

        Raises:
            FileSubmissionError: If the file cannot be opened or read.

        """
        try:
            with open(file_path, "rb") as file_handler:
                return file_handler.read()
        except OSError as e:
            raise FileSubmissionError(f"Failed to open file '{file_path}': {e}") from e

    def submit_file_for_analysis(
        self,
        url: str,
        file_bytes: bytes,
        zip_password: str | None = None,
    ) -> str:
        """Get File Analysis ID

        Args:
            url: The url for sending the request.
            file_bytes: byte representation of a file
            zip_password:Password for the ZIP file, if required.

        Returns:
            The analysis ID.

        """
        files = {"file": file_bytes}
        data = {"password": zip_password} if zip_password else None

        response = self.session.post(url, files=files, data=data)
        validate_response(response=response, show_entity_status=True)

        return parser.get_analysis_id(response.json())

    def get_upload_url(self, is_private_submission: bool = False):
        """Retrieve the URL for uploading file.

        Args:
            is_private_submission: Whether the file submission is private.

        Result:
            The parser upload URL from the API response.

        """
        complete_url = get_full_url(
            api_root=self.api_root, endpoint_id="file-upload-url"
        )

        if is_private_submission:
            complete_url = get_full_url(
                api_root=self.api_root, endpoint_id="file-upload-url-private"
            )
        response = self.session.get(complete_url)
        validate_response(response=response, show_entity_status=True)
        return parser.get_upload_url(response.json())

    def submit_hash_for_analysis(
        self,
        file_hash: data_models.Hash,
        show_entity_status: bool = False,
    ) -> str:
        """Submits a hash for analysis.

        Args:
            file_hash: The hash to analyze.
            show_entity_status: Whether to return an error message for the entity.

        Returns:
            The analysis ID.

        """
        identifier = prepare_hash_identifier(file_hash)
        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="submit_hash_analysis",
            hash=identifier,
        )
        response = self.session.post(url)
        validate_response(response, show_entity_status=show_entity_status)
        return parser.get_analysis_id(response.json())

    def download_file_from_url(self, url: str) -> bytes:
        """Download a file from url."""
        response = self.session.get(url=url)
        validate_response(response)
        return response.content

    def check_analysis_status(
        self,
        analysis_id: str,
        show_entity_status: bool = False,
        is_private_submission: bool = False,
        get_file_hash: bool = False,
    ):
        """Checks the status of an analysis.

        Args:
            analysis_id (str): The ID of the analysis.
            show_entity_status (bool): Whether to return error messages related to
                                the entity's status.
            is_private_submission (bool): Whether the file submission is private.
            get_file_hash (bool): Whether to include the file hash in the request.

        Returns:
            str:The analysis ID.

        """
        url = get_full_url(
            api_root=self.api_root,
            endpoint_id="analyses",
            analysis_id=analysis_id,
        )
        if is_private_submission:
            url = get_full_url(
                api_root=self.api_root,
                endpoint_id="analyses-private",
                analysis_id=analysis_id,
            )

        response = self.session.get(url)
        validate_response(response, show_entity_status=show_entity_status)

        result = response.json()
        if get_file_hash:
            return parser.get_analysis_status(
                raw_data=result
            ), parser.get_hash_from_file_analysis(raw_data=result)

        return parser.get_analysis_status(raw_data=result)

    def search_iocs(self, query: str, limit: int) -> list[IOCSearchResult]:
        """Search IOCs.

        Args:
            query: search query to execute.
            limit: maximum amount of results to return.

        Returns:
            list[IOCSearchResult]: list of IOCSearchResult objects.

        """
        url = get_full_url(self.api_root, "search_ioc")
        params = {
            "query": query,
            "limit": limit,
        }

        response = self.session.get(url, params=params)
        validate_response(response)
        return parser.build_ioc_search_result_objects(response.json())

    def get_ioc_stream(
        self,
        limit: int,
        siemplify: SiemplifyConnectorExecution = None,
        existing_ids: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ):
        """Get objects from the IoC Stream

        Args:
            limit (int): limit for results
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
            existing_ids (list[str] | None): list of ids to filter
            filters (dict[str, Any] | None): dictionary of filters to apply

        Returns:
            list[Notification]: list of Notification objects

        """
        url = get_full_url(self.api_root, "ioc_stream")
        params = {
            "limit": MAX_NOTIFICATIONS_LIMIT,
            "order": "date+",
        }

        filter_parts = []
        if filters is not None:
            for k, v in filters.items():
                if isinstance(v, list):
                    part = " OR ".join([f"{k}:{val}" for val in v])
                    filter_parts.append(f"({part})")
                else:
                    filter_parts.append(f"{k}:{v}")

            params["filter"] = " ".join(filter_parts)

        return self._paginate_results_by_next_page_link(
            full_url=url,
            limit=limit,
            siemplify=siemplify,
            parser_method="build_notification_objects",
            existing_ids=existing_ids,
            params=params,
        )

    def _paginate_results_by_next_page_link(
        self,
        full_url: str,
        limit: int,
        siemplify: SiemplifyConnectorExecution,
        parser_method: str,
        existing_ids: list[str] | None = None,
        params: dict | None = None,
    ) -> list[Any]:
        """Paginate the results

        Args:
            full_url (str): full url to send request to
            limit (int): limit for the results to fetch
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
            parser_method (str): parser method to convert json to dataclass
            existing_ids (list[str] | None): list of ids to filter
            params (dict | None): request params dict

        Returns:
            list[Any]: list of any dataclasses

        """
        results, next_page_link, response = [], None, None
        existing_ids_set = set(existing_ids) if existing_ids else set()

        while True:
            if response:
                if not next_page_link or (limit is not None and len(results) >= limit):
                    break

                full_url = next_page_link
                params = {}

            response = self.session.get(full_url, params=params)
            validate_response(response)
            next_page_link = response.json().get("links", {}).get("next", "")
            alerts = getattr(parser, parser_method)(response.json())
            filtered_alerts = [
                alert
                for alert in alerts
                if not hasattr(alert, "pass_filter") or alert.pass_filter()
            ]

            results.extend(
                filter_old_alerts(
                    siemplify,
                    alerts=filtered_alerts,
                    existing_ids=existing_ids_set,
                    id_key="alert_id",
                )
            )

        return results[:limit] if limit else results

    def get_file(self, entity_hash: str) -> str:
        """Downloads a file based on its hash.

        Args:
            entity_hash (str): The hash of the file to download.

        Returns:
            str: The text content of the downloaded file.

        """
        url = get_full_url(self.api_root, "get_file", entity_hash=entity_hash)
        response = self.session.get(url)
        validate_response(response)
        return response.text

    # ASM
    def _set_session_asm_project_id(self) -> None:
        if self.project_id:
            self.session.headers.update({"PROJECT-ID": self.project_id})

    # ASM Notes
    def add_asm_note(self, item_type: ASMItemType, item_id: str, text: str) -> dict:
        """
        Adds note to existing item
        Args:
            item_type (enum):  ISSUE/ENTITY
            item_id (str): Id of an entity
            text (str): Note text

        Returns:
            dict: Response json
        """
        url = get_full_url(
            self.api_root, "asm_notes", item_type=item_type.value, item_id=item_id
        )
        self._set_session_asm_project_id()
        data = {"note_text": text}
        response = self.session.post(url, json=data)
        validate_response(response)
        response_json = response.json()
        if not response_json["success"]:
            raise GoogleThreatIntelligenceExceptions(response_json["message"])

        return response_json

    def patch_dtm_alert(self, alert_id: str, payload: dict) -> DTMAlert:
        """
        Update extisting alert
        Args:
            alert_id (str): Alert id
            payload (dict): Paylaad dictionary

        Returns:
            DTMAlert: Response DTMAlert
        """
        url = get_full_url(self.api_root, "update_dtm_alert", alert_id=alert_id)

        response = self.session.patch(url, json=payload)
        validate_response(response)

        return parser.build_dtm_alert_object(response.json())

    def get_dtm_alert(self, alert_id: str) -> DTMAlert:
        """
        Get DTM alert
        Args:
            alert_id (str): Alert id

        Returns:
            DTMAlert: Response DTMAlert
        """
        url = get_full_url(self.api_root, "update_dtm_alert", alert_id=alert_id)

        response = self.session.get(url)
        validate_response(response)

        return parser.build_dtm_alert_object(response.json())

    def _get_gti_base_api_root(self) -> str:
        """Derive the GTI base API root URL without /projects/... or /v1beta.

        Returns:
            The normalized base API root URL ending with a slash.

        """
        base: str = self.api_root.split("/projects/")[0]
        if "/v1beta" in base:
            base = base.split("/v1beta")[0]
        return base.rstrip("/") + "/"

    def _extract_gti_project_id(self, project_id: str | None = None) -> str:
        """Extract or validate the target project ID.

        Args:
            project_id: Optional explicit Google Cloud Project ID.

        Returns:
            Target project ID.

        Raises:
            GoogleThreatIntelligenceExceptions: If project ID is not found.

        """
        target_project_id: str | None = project_id
        if "projects/" in self.api_root:
            target_project_id = (
                self.api_root.split("projects/")[-1].strip("/").split("/")[0]
            )

        if not target_project_id:
            raise GoogleThreatIntelligenceExceptions("Project ID is required in API Root URL.")

        return target_project_id

    def _exchange_gti_access_token(self, gti_api_key: str) -> str:
        """Exchange GTI API key for an OAuth access token.

        Args:
            gti_api_key: GTI API Key.

        Returns:
            OAuth access token.

        Raises:
            GoogleThreatIntelligenceExceptions: If API Key is missing.

        """
        if not gti_api_key:
            raise GoogleThreatIntelligenceExceptions("API Key or Access Token is required for GTI API.")

        token_res: requests.Response = self.session.post(
            GTI_IDP_TOKEN_URL,
            json={"api_key": gti_api_key},
            headers={"Content-Type": "application/json"},
            verify=self.session.verify,
        )
        validate_response(token_res)
        return token_res.json().get("access_token", "")

    def _build_gti_start_time_filter(self, start_time: int | float | str | None) -> str | None:
        """Build ISO-formatted filter string for start_time.

        Args:
            start_time: Lower bound timestamp to filter alerts.

        Returns:
            Filter string condition or None.

        """
        if not start_time:
            return None

        if isinstance(start_time, (int, float)):
            ts_sec: float = start_time / 1000.0 if start_time > 1e11 else float(start_time)
            dt: datetime = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
        else:
            try:
                ts_ms: int = convert_string_to_unix_time(str(start_time))
                dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            except (ValueError, TypeError):
                clean_str: str = str(start_time).strip()
                if " " in clean_str and "T" not in clean_str:
                    clean_str = clean_str.replace(" ", "T")
                dt = datetime.fromisoformat(clean_str)

        start_iso: str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f'audit.update_time>="{start_iso}"'

    def _build_gti_filter(
        self,
        start_time: int | float | str | None = None,
        alert_types: list[str] | None = None,
    ) -> str | None:
        """Build CEL filter query combining start_time and alert types.

        Args:
            start_time: Start time parameter.
            alert_types: List of allowed alert detail types.

        Returns:
            CEL filter string or None.

        """
        filter_parts: list[str] = []
        time_filter: str | None = self._build_gti_start_time_filter(start_time)
        if time_filter:
            filter_parts.append(time_filter)

        if alert_types:
            clean_types: list[str] = [t.strip().lower() for t in alert_types if t and t.strip()]
            if clean_types:
                type_clauses: list[str] = [f'detail.detail_type = "{t}"' for t in clean_types]
                if len(type_clauses) == 1:
                    filter_parts.append(type_clauses[0])
                else:
                    filter_parts.append(f"({' OR '.join(type_clauses)})")

        return " AND ".join(filter_parts) if filter_parts else None

    def _fetch_individual_findings(
        self,
        findings: list[str],
        access_token: str,
        target_project_id: str,
    ) -> list[SingleJson]:
        """Fetch individual finding payloads when batch search is unavailable.

        Args:
            findings: List of finding resource names.
            access_token: Cached OAuth access token.
            target_project_id: Target Google Cloud Project ID.

        Returns:
            List of finding payloads.

        """
        finding_details: list[SingleJson] = []
        for finding_name in findings:
            try:
                finding_data: SingleJson = self.get_gti_finding(
                    finding_name=finding_name,
                    access_token=access_token,
                    target_project_id=target_project_id,
                )
                if finding_data:
                    finding_details.append(finding_data)
            except (
                GoogleThreatIntelligenceExceptions,
                requests.exceptions.RequestException,
            ) as err:
                if self.logger:
                    self.logger.error(f"Failed to fetch finding {finding_name}: {err}")
        return finding_details

    def _enrich_gti_alert_findings(
        self,
        raw_alert: SingleJson,
        access_token: str,
        target_project_id: str,
    ) -> list[SingleJson]:
        """Fetch finding details for a specific raw alert.

        Attempts high-performance batch retrieval via findings:search first.
        Falls back to individual GET /findings/{id} if needed.

        Args:
            raw_alert: Raw alert payload.
            access_token: Cached OAuth access token.
            target_project_id: Target Google Cloud Project ID.

        Returns:
            List of finding payloads.

        """
        alert_name: str = raw_alert.get("name", "")
        if alert_name:
            try:
                searched_findings: list[SingleJson] = self.search_gti_findings_by_alert(
                    alert_name=alert_name,
                    target_project_id=target_project_id,
                    access_token=access_token,
                )
                if searched_findings:
                    return searched_findings
            except (
                GoogleThreatIntelligenceExceptions,
                requests.exceptions.RequestException,
            ) as err:
                if self.logger:
                    self.logger.warn(
                        f"findings:search failed for {alert_name}, "
                        f"falling back to individual calls: {err}"
                    )

        findings: list[str] = raw_alert.get("findings", [])
        if not findings:
            return []

        return self._fetch_individual_findings(findings, access_token, target_project_id)

    def _fetch_single_document(self, doc_name: str, access_token: str, target_project_id: str) -> SingleJson | None:
        """Fetch a single document payload by resource name.

        Args:
            doc_name: Document resource name.
            access_token: Cached OAuth access token.
            target_project_id: Target Google Cloud Project ID.

        Returns:
            Document JSON payload or None on error.

        """
        try:
            return self.get_gti_alert_document(
                document_name=doc_name,
                access_token=access_token,
                target_project_id=target_project_id,
            )
        except (
            GoogleThreatIntelligenceExceptions,
            requests.exceptions.RequestException,
        ) as err:
            if self.logger:
                self.logger.error(f"Failed to fetch document {doc_name}: {err}")
            return None

    def _enrich_gti_alert_documents(
        self,
        raw_alert: SingleJson,
        access_token: str,
        target_project_id: str,
        finding_details: list[SingleJson] | None = None,
    ) -> list[SingleJson]:
        """Fetch full document details for all document references in an alert and findings.

        Args:
            raw_alert: Raw alert payload.
            access_token: Cached OAuth access token.
            target_project_id: Target Google Cloud Project ID.
            finding_details: Finding payloads for this alert.

        Returns:
            List of document payloads.

        """
        document_details: list[SingleJson] = []
        alert_name: str = raw_alert.get("name", "")

        raw_refs: list[str] = _collect_document_refs(raw_alert.get("detail"))
        for finding in (finding_details or []):
            raw_refs.extend(_collect_document_refs(finding.get("detail")))

        seen_docs: set[str] = set()
        for ref in raw_refs:
            if not ref or not isinstance(ref, str):
                continue
            doc_name: str = ref if ref.startswith("projects/") else f"{alert_name}/documents/{ref}"
            if doc_name in seen_docs:
                continue
            seen_docs.add(doc_name)

            doc_data: SingleJson | None = self._fetch_single_document(doc_name, access_token, target_project_id)
            if doc_data:
                document_details.append(doc_data)

        return document_details

    def _is_alert_filtered(self, raw: SingleJson, existing_ids: set[str], min_threshold: int | None) -> bool:
        """Check if raw alert should be skipped based on existing IDs or severity.

        Args:
            raw: Raw alert dictionary.
            existing_ids: Set of previously processed alert IDs.
            min_threshold: Minimum severity threshold value.

        Returns:
            True if alert should be skipped, False otherwise.

        """
        alert_id: str = raw.get("name", "")
        if alert_id in existing_ids:
            if self.logger:
                self.logger.info(
                    f"The alert {alert_id} skipped since it has been fetched before"
                )
            return True
        alert_sev: str = data_models.extract_gti_alert_severity(raw)
        return (
            min_threshold is not None
            and SEVERITY_MAPPING.get(alert_sev.lower(), 40) < min_threshold
        )

    def _process_single_raw_alert(
        self,
        raw: SingleJson,
        *,
        target_project_id: str,
        access_token: str,
        existing_ids_set: set[str],
        min_threshold: int | None,
    ) -> data_models.GTIAlert | None:
        """Filter and enrich a single raw GTI alert payload.

        Args:
            raw: Raw alert dictionary.
            target_project_id: Google Cloud Project ID.
            access_token: Cached OAuth access token.
            existing_ids_set: Set of already processed alert IDs.
            min_threshold: Minimum severity threshold integer.

        Returns:
            Constructed GTIAlert object, or None if skipped/filtered.

        """
        if self._is_alert_filtered(raw, existing_ids_set, min_threshold):
            return None

        finding_details: list[SingleJson] = self._enrich_gti_alert_findings(raw, access_token, target_project_id)
        document_details: list[SingleJson] = self._enrich_gti_alert_documents(
            raw,
            access_token,
            target_project_id,
            finding_details=finding_details,
        )
        return data_models.GTIAlert.from_json(
            raw,
            findings_details=finding_details,
            documents_details=document_details,
        )

    def _process_gti_alerts_page(
        self,
        alerts_raw: list[SingleJson],
        *,
        target_project_id: str,
        access_token: str,
        existing_ids_set: set[str],
        min_threshold: int | None,
        limit: int | None,
        all_alerts: list[data_models.GTIAlert],
    ) -> None:
        """Filter and enrich a single page of raw GTI alerts.

        Args:
            alerts_raw: List of raw alert payloads from the API.
            target_project_id: Google Cloud Project ID.
            access_token: Cached OAuth access token.
            existing_ids_set: Set of already processed alert IDs to skip.
            min_threshold: Minimum severity threshold integer.
            limit: Maximum alerts to accumulate.
            all_alerts: Target accumulator list for constructed GTIAlert objects.

        """
        for raw in alerts_raw:
            if limit and len(all_alerts) >= limit:
                break

            alert_obj: data_models.GTIAlert | None = self._process_single_raw_alert(
                raw,
                target_project_id=target_project_id,
                access_token=access_token,
                existing_ids_set=existing_ids_set,
                min_threshold=min_threshold,
            )
            if alert_obj:
                all_alerts.append(alert_obj)

            if limit and len(all_alerts) >= limit:
                break

    def _build_gti_alerts_request_params(
        self,
        start_time: int | float | str | None,
        alert_types: list[str] | None,
    ) -> SingleJson:
        """Build query parameters for the GTI alerts API request.

        Args:
            start_time: Start time for alert filtering.
            alert_types: Allowed alert detail types for CEL filtering.

        Returns:
            Dictionary of query parameters.

        """
        params: SingleJson = {
            "orderBy": "audit.update_time asc",
            "pageSize": DEFAULT_PAGE_SIZE,
        }
        filter_str: str | None = self._build_gti_filter(start_time, alert_types)
        if filter_str:
            params["filter"] = filter_str
        return params

    def _prepare_gti_alerts_request(
        self,
        gti_api_key: str,
        project_id: str | None,
        start_time: int | float | str | None,
        alert_types: list[str] | None,
    ) -> tuple[str, str, str, dict[str, str], SingleJson]:
        """Prepare URL, headers, and parameters for GTI alerts query.

        Args:
            gti_api_key: GTI API Key.
            project_id: Target project ID override.
            start_time: Start time filter.
            alert_types: Detail types filter.

        Returns:
            Tuple of (target_project_id, access_token, url, headers, params).

        """
        target_project_id: str = self._extract_gti_project_id(project_id)
        access_token: str = self._exchange_gti_access_token(gti_api_key)
        url: str = get_full_url(self._get_gti_base_api_root(), "get_gti_alerts", project_id=target_project_id)
        headers: dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "x-goog-user-project": target_project_id,
            "Content-Type": "application/json",
        }
        params: SingleJson = self._build_gti_alerts_request_params(start_time, alert_types)
        return target_project_id, access_token, url, headers, params

    def _fetch_gti_alerts_page(
        self,
        url: str,
        headers: dict[str, str],
        params: SingleJson,
    ) -> tuple[list[SingleJson], str | None]:
        """Execute a single page GET request for GTI alerts.

        Args:
            url: Full API endpoint URL.
            headers: Request HTTP headers.
            params: Request query parameters.

        Returns:
            Tuple of (raw alerts list, nextPageToken).

        """
        res: requests.Response = self.session.get(url, headers=headers, params=params, verify=self.session.verify)
        validate_response(res)
        res_json: SingleJson = res.json()
        return res_json.get("alerts", []), res_json.get("nextPageToken")

    def get_gti_alerts(
        self,
        gti_api_key: str,
        *,
        project_id: str | None = None,
        lowest_severity: str | None = None,
        start_time: int | float | str | None = None,
        limit: int | None = None,
        existing_ids: list[str] | set[str] | None = None,
        alert_types: list[str] | None = None,
    ) -> list[data_models.GTIAlert]:
        """Fetch Google Threat Intelligence (GTI) alerts using GTI API Key token exchange."""
        target_project_id, access_token, url, headers, params = self._prepare_gti_alerts_request(
            gti_api_key,
            project_id,
            start_time,
            alert_types,
        )
        all_alerts: list[data_models.GTIAlert] = []
        page_token: str | None = None
        min_threshold: int | None = (
            SEVERITY_MAPPING.get(lowest_severity.lower(), 0) if lowest_severity else None
        )
        existing_ids_set: set[str] = set(existing_ids) if existing_ids else set()

        while True:
            if page_token:
                params["pageToken"] = page_token

            alerts_raw, page_token = self._fetch_gti_alerts_page(url, headers, params)
            self._process_gti_alerts_page(
                alerts_raw,
                target_project_id=target_project_id,
                access_token=access_token,
                existing_ids_set=existing_ids_set,
                min_threshold=min_threshold,
                limit=limit,
                all_alerts=all_alerts,
            )

            if not page_token or not alerts_raw or (limit and len(all_alerts) >= limit):
                break

        return all_alerts[:limit] if (limit and len(all_alerts) >= limit) else all_alerts

    def search_gti_findings_by_alert(
        self,
        alert_name: str,
        target_project_id: str | None = None,
        access_token: str | None = None,
        gti_api_key: str | None = None,
    ) -> list[SingleJson]:
        """Search findings associated with an alert using findings:search.

        Args:
            alert_name: Alert resource name (e.g. projects/{project}/alerts/{id}).
            target_project_id: Google Cloud Project ID.
            access_token: Cached OAuth access token if available.
            gti_api_key: GTI API Key if token not provided.

        Returns:
            List of finding payload dictionaries.

        """
        proj_id: str = target_project_id or self._extract_gti_project_id()
        resolved_token: str = access_token or self._exchange_gti_access_token(gti_api_key or "")
        clean_alert_name: str = alert_name.lstrip("/")
        url: str = get_full_url(self._get_gti_base_api_root(), "search_gti_findings", project_id=proj_id)
        headers: dict[str, str] = {
            "Authorization": f"Bearer {resolved_token}",
            "x-goog-user-project": proj_id,
            "Content-Type": "application/json",
        }
        escaped_alert_name: str = clean_alert_name.replace('"', '\\"')
        params: dict[str, str] = {"query": f'has_alert("name=\\"{escaped_alert_name}\\"")'}
        res: requests.Response = self.session.get(url, headers=headers, params=params, verify=self.session.verify)
        validate_response(res)
        return res.json().get("findings", [])

    def get_gti_finding(
        self,
        finding_name: str,
        gti_api_key: str | None = None,
        access_token: str | None = None,
        target_project_id: str | None = None,
    ) -> SingleJson:
        """Fetch details of a specific GTI finding.

        Args:
            finding_name: Finding resource name (e.g. projects/{project}/findings/{id}).
            gti_api_key: GTI API Key.
            access_token: Cached OAuth access token if available.
            target_project_id: Google Cloud Project ID if not present in api_root.

        Returns:
            Raw finding JSON payload.

        Raises:
            GoogleThreatIntelligenceExceptions: If project ID is missing, token exchange
                fails, or the request returns an error.

        """
        if not finding_name or not finding_name.strip():
            raise GoogleThreatIntelligenceExceptions("Finding name is required.")

        proj_id: str = self._extract_gti_project_id(target_project_id)
        resolved_token: str = access_token or self._exchange_gti_access_token(gti_api_key or "")
        clean_finding_name: str = _strip_gti_resource_prefix(finding_name)
        url: str = get_full_url(
            self._get_gti_base_api_root(),
            "get_gti_finding",
            finding_name=clean_finding_name,
        )

        headers: dict[str, str] = {
            "Authorization": f"Bearer {resolved_token}",
            "x-goog-user-project": proj_id,
            "Content-Type": "application/json",
        }

        res: requests.Response = self.session.get(url, headers=headers, verify=self.session.verify)
        validate_response(res)
        return res.json()

    def get_gti_alert_document(
        self,
        document_name: str,
        gti_api_key: str | None = None,
        access_token: str | None = None,
        target_project_id: str | None = None,
    ) -> SingleJson:
        """Fetch details of a specific GTI alert document.

        Args:
            document_name: Document resource name
                (e.g. projects/{project}/alerts/{alert}/documents/{id}).
            gti_api_key: GTI API Key.
            access_token: Cached OAuth access token if available.
            target_project_id: Google Cloud Project ID if not present in api_root.

        Returns:
            Raw document JSON payload.

        Raises:
            GoogleThreatIntelligenceExceptions: If project ID is missing, token exchange
                fails, or the request returns an error.

        """
        if not document_name or not document_name.strip():
            raise GoogleThreatIntelligenceExceptions("Document name is required.")

        proj_id: str = self._extract_gti_project_id(target_project_id)
        resolved_token: str = access_token or self._exchange_gti_access_token(gti_api_key or "")
        clean_doc_name: str = _strip_gti_resource_prefix(document_name)
        url: str = get_full_url(
            self._get_gti_base_api_root(),
            "get_gti_alert_document",
            document_name=clean_doc_name,
        )

        headers: dict[str, str] = {
            "Authorization": f"Bearer {resolved_token}",
            "x-goog-user-project": proj_id,
            "Content-Type": "application/json",
        }

        res: requests.Response = self.session.get(url, headers=headers, verify=self.session.verify)
        validate_response(res)
        return res.json()

    def _build_agent_session_url(self, endpoint_id: str, session_id: str | None = None) -> str:
        """Build an agentspace sessions URL with the session ID safely encoded."""
        encoded_session_id = urllib.parse.quote(session_id, safe="") if session_id else session_id

        return get_full_url(self.api_root, endpoint_id, session_id=encoded_session_id)

    def _post_agent_message(
        self,
        url: str,
        prompt: str,
        file_paths: list[str] | None = None,
    ) -> requests.Response:
        """Send the prompt and optional attachments to an agentspace session as multipart/form-data."""
        with contextlib.ExitStack() as stack:
            multipart_fields = [
                ("message", (None, prompt)),
                *_build_multipart_files(stack, file_paths or []),
            ]
            response = self.session.post(url, files=multipart_fields)

        validate_agent_session_response(response)

        return response

    def post_agent_prompt(
        self,
        prompt: str,
        session_id: str | None = None,
        file_paths: list[str] | None = None,
    ) -> SingleJson:
        """Send a prompt to the Google Threat Intelligence Agent and return the updated session.

        Posting a message is synchronous, so the returned session contains the agent's final
        response once processing finished. The session ID header is used when the body has no ID.
        """
        endpoint_key = "post_session_message" if session_id else "create_agent_session"
        url = self._build_agent_session_url(endpoint_key, session_id)

        response = self._post_agent_message(url, prompt, file_paths)
        session_data: SingleJson = response.json()
        data = session_data.setdefault("data", {})
        if not data.get("id"):
            data["id"] = response.headers.get(AGENT_SESSION_ID_HEADER, "")

        return session_data

    def delete_agent_session(self, session_id: str) -> None:
        """Delete an agentic session by ID."""
        response = self.session.delete(
            self._build_agent_session_url("delete_agent_session", session_id),
            headers=AGENT_JSON_ACCEPT_HEADERS,
            timeout=AGENT_REQUEST_TIMEOUT_IN_SECONDS,
        )
        validate_agent_session_response(response)


def _build_multipart_files(
    stack: contextlib.ExitStack,
    file_paths: list[str],
) -> list[tuple[str, tuple[str, BinaryIO, str]]]:
    """Open the files in the given stack and build their multipart/form-data `files` fields.

    Args:
        stack: The exit stack that closes the opened files.
        file_paths: The paths of the files to attach.

    Returns:
        The `files` fields, one per file.
    """
    return [
        (
            "files",
            (
                os.path.basename(file_path),
                stack.enter_context(open(file_path, "rb")),
                "application/octet-stream",
            ),
        )
        for file_path in file_paths
    ]
