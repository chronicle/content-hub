"""Provides the 1P API client implementation for interacting with Chronicle SOAR."""

# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

from TIPCommon.rest.custom_types import HttpMethod

from ...consts import DATAPLANE_1P_HEADER, DEFAULT_1P_PAGE_SIZE
from ...utils import escape_odata_literal, safe_json_for_204, temporarily_remove_header
from .base_soar_api import BaseSoarApi

if TYPE_CHECKING:
    import requests

    from TIPCommon.types import SingleJson


_PAGE_SIZE = 1000


class OnePlatformSoarApi(BaseSoarApi):
    """Chronicle SOAR API client using 1P endpoints."""

    def save_attachment_to_case_wall(self) -> requests.Response:
        """Save an attachment to the case wall using 1P API."""
        payload = {
            "caseAttachment": {
                "attachmentId": 0,
                "attachmentBase64": self.params.base64_blob,
                "fileType": self.params.file_type,
                "fileName": self.params.name,
            },
            "comment": self.params.description,
            "isImportant": self.params.is_important,
        }
        if getattr(self.chronicle_soar, "alert_id", None):
            payload["alertIdentifier"] = self.chronicle_soar.alert_id

        endpoint = f"/cases/{self.params.case_id}/comments"
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def get_entity_data(self) -> requests.Response:
        """Get entity data using 1P API."""
        payload = {
            "identifier": self.params.entity_identifier,
            "type": self.params.entity_type,
            "environment": self.params.entity_environment,
            "lastCaseType": self.params.last_case_type,
            "caseDistributionType": self.params.case_distribution_type,
        }
        endpoint = "/uniqueEntities:fetchFull"
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_full_case_details(self) -> requests.Response:
        """Get full case details using explicit expand parameters.

        Expand behavior:
            - case_expand controls /cases endpoint
            - alert_expand controls /caseAlerts endpoint when case_type="alert"
        """
        case_type = self.params.case_type
        case_id = self.params.case_id

        if case_type == "alert":
            params = self._build_expand_params(getattr(self.params, "alert_expand", None))
            endpoint = f"/cases/{case_id}/caseAlerts"
        else:
            params = self._build_expand_params(getattr(self.params, "case_expand", None))
            endpoint = f"/cases/{case_id}"

        return self._make_request(HttpMethod.GET, endpoint, params=params)

    def get_case_insights(self) -> requests.Response:
        """Get case insights using 1P API."""
        endpoint = f"/cases/{self.params.case_id}/activities"
        query_params = {
            "$filter": "activityType eq 'CaseInsight'",
            "pageSize": DEFAULT_1P_PAGE_SIZE,
        }
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def get_installed_integrations_of_environment(self) -> requests.Response:
        """Get installed integrations of environment using legacy API."""
        endpoint = f"/integrations/{self.params.integration_identifier}/integrationInstances"
        name = "*" if self.params.environment == "Shared Instances" else self.params.environment
        params = {"$filter": f"environment eq '{escape_odata_literal(name)}'"}
        return self._make_request(HttpMethod.GET, endpoint, params=params)

    def get_connector_cards(self) -> requests.Response:
        """Get connector cards using legacy API"""
        endpoint = f"/integrations/{self.params.integration_name}/connectors/-/connectorInstances"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_federation_cases(self) -> requests.Response:
        """Get federation cases using legacy API"""
        endpoint = "/legacyFederatedCases:legacyFetchCasesToSync"
        params = {"pageToken": self.params.continuation_token}
        return self._make_request(HttpMethod.GET, endpoint, params=params)

    def patch_federation_cases(self) -> requests.Response:
        """Patch federation cases using legacy API"""
        endpoint = "/legacyFederatedCases:legacyBatchPatchFederatedCases"
        headers = {"AppKey": self.params.api_key} if self.params.api_key else None
        payload = {"cases": self.params.cases_payload}

        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=payload,
            headers=headers,
        )

    def get_workflow_instance_card(self) -> requests.Response:
        """Get workflow instance card using legacy API"""
        endpoint = "/legacyPlaybooks:legacyGetWorkflowInstancesCards?format=camel"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def pause_alert_sla(self) -> requests.Response:
        """Pause alert sla"""
        alert = self.get_case_alerts().json()
        alert_id = alert.get("caseAlerts")[0].get("id")
        endpoint = f"/cases/{self.params.case_id}/caseAlerts/{alert_id}:pauseSla"
        payload = {
            "message": self.params.message,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def resume_alert_sla(self) -> requests.Response:
        """Resume alert sla"""
        alert = self.get_case_alerts().json()
        alert_id = alert.get("caseAlerts")[0].get("id")
        endpoint = f"/cases/{self.params.case_id}/caseAlerts/{alert_id}:resumeSla"
        payload = {
            "message": self.params.message,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def _get_case_details(self) -> SingleJson:
        """Fetch case details using explicit case_expand."""
        params = self._build_expand_params(getattr(self.params, "case_expand", None))
        case_id = self.params.case_id
        endpoint = f"/cases/{case_id}"
        return self._make_request(
            HttpMethod.GET,
            endpoint,
            params=params,
        ).json()

    def _get_case_alerts(self) -> list:
        """Fetch case alert cards using explicit alert_expand."""
        params = self._build_expand_params(getattr(self.params, "alert_expand", None))
        case_id = self.params.case_id
        endpoint = f"/cases/{case_id}/caseAlerts"
        response = self._make_request(
            HttpMethod.GET,
            endpoint,
            params=params,
        ).json()

        return response.get("caseAlerts", [])

    def get_case_overview_details(self) -> SingleJson:
        """Get full case overview including case details and alert cards.

        Expand is explicitly controlled by:
            - self.params.case_expand
            - self.params.alert_expand
        """
        case_data = self._get_case_details()
        case_data["alertCards"] = self._get_case_alerts()
        return case_data

    def remove_case_tag(self) -> requests.Response:
        """Remove case tag"""
        endpoint = f"/cases/{self.params.case_id}:removeTag"
        payload = {
            "caseId": self.params.case_id,
            "tag": self.params.tag,
            "alertIdentifier": self.params.alert_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def change_case_description(self) -> requests.Response:
        """Change case description"""
        endpoint = f"/cases/{self.params.case_id}"
        payload = {"description": self.params.description}
        return self._make_request(HttpMethod.PATCH, endpoint, json_payload=payload)

    def set_alert_priority(self) -> requests.Response:
        """Set alert priority"""
        endpoint = "/legacySdk:legacyUpdateAlertPriority"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "priority": self.params.priority,
            "alertName": self.params.alert_name,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def set_case_score_bulk(self) -> requests.Response:
        """Set case score bulk"""
        endpoint = "/legacySdk:legacyUpdateCaseScore"
        payload = {
            "caseScores": [
                {
                    "caseId": self.params.case_id,
                    "score": self.params.score,
                }
            ],
        }
        return self._make_request(HttpMethod.PATCH, endpoint, json_payload=payload)

    def get_integration_full_details(self) -> requests.Response:
        """Get integration full details"""
        endpoint = f"/marketplaceIntegrations/{self.params.integration_identifier}"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_integration_instance_details_by_id(self) -> requests.Response:
        """Get integration instance details by instance id"""
        endpoint = (
            f"/integrations/{self.params.integration_identifier}/integrationInstances/"
            f"{self.params.instance_id}"
        )

        return self._make_request(HttpMethod.GET, endpoint)

    def get_integration_instance_details_by_name(self) -> SingleJson:
        """Get integration instance details by instance name"""
        endpoint = f"/integrations/{self.params.integration_identifier}/integrationInstances"
        instance_name = escape_odata_literal(self.params.instance_display_name)
        query_params = {"$filter": f"displayName eq '{instance_name}'"}

        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def get_users_profile(self) -> requests.Response:
        """Get users profile"""
        endpoint = "/legacySoarUsers"
        display_name = escape_odata_literal(self.params.display_name)
        query_params = {"$filter": f"displayName eq '{display_name}'"}
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def get_case_alerts(self) -> requests.Response:
        """Get case alerts"""
        endpoint = f"/cases/{self.params.case_id}/caseAlerts"
        query_params: dict[str, str] = {}
        if self.params.alert_identifier is not None:
            alert_identifier = escape_odata_literal(self.params.alert_identifier)
            query_params = {"$filter": f"identifier eq '{alert_identifier}'"}
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def get_investigator_data(self) -> requests.Response:
        """Get investigator data"""
        case_id = self.params.case_id
        alert_data = self.get_alert_id_by_alert_identifier()
        if alert_data.status_code == 204:
            alert_data._content = b"{}"
            return alert_data

        alert_id = alert_data.json()["caseAlerts"][0].get("id")
        endpoint = f"/cases/{case_id}/caseAlerts/{alert_id}/involvedEvents:formatted"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_alert_id_by_alert_identifier(self) -> requests.Response:
        """Get alert id by alert identifier"""
        endpoint = f"/cases/{self.params.case_id}/caseAlerts"
        alert_identifier = escape_odata_literal(self.params.alert_identifier)
        query_params = {"$filter": f"identifier eq '{alert_identifier}'"}
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    # TODO : Not avialable in 1p so we will implement when api avialble
    def remove_entities_from_custom_list(self) -> requests.Response:
        """Remove entities from custom list"""
        endpoint = "/sdk/RemoveEntitiesFromCustomList"
        payload = self.params.list_entities_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    # TODO : Not avialable in 1p so we will implement when api avialble
    def add_entities_to_custom_list(self) -> requests.Response:
        """Add entities to custom list"""
        endpoint = "/sdk/AddEntitiesToCustomList"
        payload = self.params.list_entities_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def _paginate_results(self, initial_endpoint: str, root_response_key: str) -> list[SingleJson]:
        """Handles paginated API requests, managing tokens and aggregating results.
        Avoids infinite loops by using a controlled loop condition.

        Args:
            initial_endpoint (str): The initial API endpoint to fetch data from.
            root_response_key (str): The key in the response JSON where records are stored.

        Returns:
            list[SingleJson]: A list of all records retrieved across paginated responses.
        """
        all_records = []
        next_token = None
        current_endpoint = initial_endpoint

        while True if next_token is None else bool(next_token):
            endpoint_with_token = (
                f"{current_endpoint}&pageToken={next_token}" if next_token else current_endpoint
            )

            response_data = {}
            try:
                response = self._make_request(HttpMethod.GET, endpoint_with_token)
                response.raise_for_status()
                response_data = response.json()
            except Exception as e:
                print(f"Error fetching page: {e}")
                break

            current_records = response_data.get(root_response_key, [])
            all_records.extend(current_records)

            next_token = response_data.get("nextPageToken")
            if not next_token:
                break

        return all_records

    def _build_tracking_list_filter_string(
        self,
        category_names: str | list[str] | None,
        entity_id: str | None,
        environment: str | None = None,
    ) -> str:
        """Builds the OData filter string for tracking list records.

        The filter structure is: [environment AND] [category OR block AND]
        [entityIdentifier].
        """
        filter_parts = []

        if environment:
            filter_parts.append(f"environments eq '[\"{environment}\"]'")

        if category_names:
            if isinstance(category_names, str):
                category_names = [name.strip() for name in category_names.split(",")]

            if category_names:
                category_filters = [f"category eq '{name}'" for name in category_names]

                category_or_block = " or ".join(category_filters)
                category_filter_string = f"({category_or_block})"

                filter_parts.append(category_filter_string)

        if entity_id:
            filter_parts.append(f"entityIdentifier eq '{entity_id}'")

        if not filter_parts:
            return ""

        return " and ".join(filter_parts)

    def get_traking_list_record(self) -> SingleJson:
        """Get traking list record and handles pagination with combined filters.

        The filter combines environment (AND) with category (OR, grouped)
        and entityIdentifier (AND).
        """
        category_names = self.params.category_name
        entity_id = self.params.entity_id

        filter_string = self._build_tracking_list_filter_string(category_names, entity_id)

        base_endpoint = "/system/settings/customLists"

        if filter_string:
            initial_endpoint = f"{base_endpoint}?$filter={filter_string}&pageSize={_PAGE_SIZE}"
        else:
            initial_endpoint = f"{base_endpoint}?pageSize={_PAGE_SIZE}"

        return self._paginate_results(
            initial_endpoint=initial_endpoint,
            root_response_key="customLists"
        )

    def get_traking_list_records_filtered(self) -> SingleJson:
        """Get all tracking list records, filtering by environment AND optional
        category/entity
        filters, and handles pagination.
        """
        environment = self.params.environment or self.chronicle_soar.environment

        category_names = self.params.category_name
        entity_id = self.params.entity_id

        filter_string = self._build_tracking_list_filter_string(
            category_names, entity_id, environment=environment
        )

        base_endpoint = "/system/settings/customLists"

        if filter_string:
            initial_endpoint = f"{base_endpoint}?$filter={filter_string}&pageSize={_PAGE_SIZE}"
        else:
            initial_endpoint = f"{base_endpoint}?pageSize={_PAGE_SIZE}"

        return self._paginate_results(
            initial_endpoint=initial_endpoint,
            root_response_key="customLists"
        )

    def execute_bulk_assign(self) -> requests.Response:
        """Execute bulk assign"""
        endpoint = "/cases:executeBulkAssign"
        payload = {"casesIds": self.params.case_ids, "userName": self.params.user_name}
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def execute_bulk_close_case(self) -> requests.Response:
        """Execute bulk close case"""
        endpoint = "/cases:executeBulkClose"
        payload = {
            "casesIds": self.params.case_ids,
            "closeReason": self.params.close_reason,
            "rootCause": self.params.root_cause,
            "closeComment": self.params.close_comment,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_users_profile_cards(self) -> requests.Response:
        """Get users profile cards."""
        endpoint = "/legacySoarUsers"
        return self._make_request(HttpMethod.GET, endpoint)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def get_security_events(self) -> requests.Response:
        """Get security events"""
        endpoint = (
            f"/cases/{self.params.case_id}/caseAlerts/"
            f"{self.params.alert_id}/involvedEvents:formatted"
        )
        return self._make_request(HttpMethod.GET, endpoint)

    def get_entity_cards(self) -> requests.Response:
        """Get entity cards"""
        endpoint = f"/cases/{self.params.case_id}/caseAlerts/-/involvedEntities:fetchCards"
        return self._make_request(HttpMethod.GET, endpoint)

    def pause_case_sla(self, case_id: int, message: str | None = None) -> requests.Response:
        """Send an api request to pause case sla for a given case"""
        endpoint = f"/cases/{case_id}:pauseSla"
        request_payload = {"caseId": case_id}
        if message:
            request_payload["message"] = message

        return self._make_request(HttpMethod.POST, endpoint, json_payload=request_payload)

    def resume_case_sla(self, case_id: int) -> requests.Response:
        """Send an api request to resume case sla for a given case"""
        endpoint = f"/cases/{case_id}:resumeSla"
        request_payload = {"caseId": case_id}
        return self._make_request(HttpMethod.POST, endpoint, json_payload=request_payload)

    def rename_case(self) -> requests.Response:
        """Rename case"""
        endpoint = f"/cases/{self.params.case_id}"
        payload = {"displayName": self.params.case_title}
        return self._make_request(HttpMethod.PATCH, endpoint, json_payload=payload)

    def add_comment_to_entity(self) -> requests.Response:
        """Add comment to entity"""
        endpoint = "/uniqueEntities:addNote"
        payload = {
            "author": self.params.author,
            "content": self.params.content,
            "entityIdentifier": self.params.entity_identifier,
            "entityType": self.params.entity_type,
            "entityEnvironment": self.params.entity_environment,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def assign_case_to_user(self) -> requests.Response:
        """Assign case to user"""
        endpoint = "/cases:executeBulkAssign"
        payload = {"casesIds": [self.params.case_id], "userName": self.params.assign_to}
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_email_template(self) -> requests.Response:
        """Get email template"""
        endpoint = "/system/settings/emailTemplates"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_siemplify_user_details(self) -> requests.Response:
        """Get siemplify user details"""
        endpoint = "/legacySoarUsers"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_domain_alias(self) -> requests.Response:
        """Get domain alias"""
        endpoint = "/system/settings/domains"
        return self._make_request(HttpMethod.GET, endpoint)

    def add_tags_to_case_in_bulk(self) -> requests.Response:
        """Add tags to case in bulk"""
        endpoint = "/cases:executeBulkAddTag"
        payload = {"casesIds": self.params.case_ids, "tags": self.params.tags}
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def get_installed_jobs(self) -> requests.Response:
        """Get installed jobs."""
        endpoint: str = "/integrations/-/jobs/-/jobInstances/"
        if self.params.job_instance_id:
            endpoint += f"{self.params.job_instance_id}"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_case_wall_records(self) -> requests.Response:
        """Get case wall records using 1P API.

        Expand behavior:
            - self.params.wall_expand controls expand query.
            - Uses "expand" query param (not "expand").
        """
        endpoint = f"/cases/{self.params.case_id}/caseWallRecords"

        expand = getattr(self.params, "wall_expand", None)

        params = {"pageSize": DEFAULT_1P_PAGE_SIZE}
        if expand:
            params["expand"] = ",".join(expand)

        return self._make_request(HttpMethod.GET, endpoint, params=params)

    def get_entity_expand_cards(self) -> requests.Response:
        """Get entity expand cards using 1P API.

        Expand behavior:
            - self.params.entity_expand controls "expand" query.
        """
        endpoint = f"/cases/{self.params.case_id}/caseAlerts/-/involvedEntities"

        expand = getattr(self.params, "entity_expand", None)
        params = self._build_expand_params(expand)

        return self._make_request(HttpMethod.GET, endpoint, params=params)

    def get_all_case_overview_details(self) -> SingleJson:
        """Get full case overview including:
            - Case details
            - Alert cards
            - Security events
            - Wall data
            - Entity cards

        Expand behavior (explicit and separated):
            - self.params.case_expand   → /cases
            - self.params.alert_expand  → /caseAlerts
            - self.params.wall_expand   → /caseWallRecords
            - self.params.entity_expand → /involvedEntities

        No implicit expansion is performed.
        """
        case_data = self.get_case_overview_details()

        security_events = self._make_request(
            HttpMethod.GET, f"/cases/{self.params.case_id}/caseAlerts/-/involvedEvents:formatted"
        ).json()

        events_by_alert: SingleJson = {}
        for event in security_events:
            alert_id = event.get("alertIdentifier")
            if alert_id:
                events_by_alert.setdefault(alert_id, []).append(event)

        for alert in case_data.get("alertCards", []):
            alert["securityEventCards"] = events_by_alert.get(alert.get("identifier"), [])

        wall_response = self.get_case_wall_records()
        wall_data = safe_json_for_204(wall_response, default_for_204={})
        case_data["wallData"] = wall_data.get("caseWallRecords", [])

        entity_response = self.get_entity_expand_cards()
        entity_data = safe_json_for_204(entity_response, default_for_204={})
        case_data["involvedEntities"] = entity_data.get("involvedEntities", [])

        entity_cards_response = self.get_entity_cards()
        entity_cards_data = safe_json_for_204(entity_cards_response, default_for_204={})
        case_data["entityCards"] = entity_cards_data.get("cards", [])

        return case_data

    def _build_expand_params(self, expand: list[str] | None) -> dict | None:
        """Build explicit expand query parameters.

        Rules:
            - None or empty list → no expand query.
            - ["*"] → expand all fields.
            - ["field1", "field2"] → expand selected fields only.

        Returns:
            dict | None: {"expand": "a,b"} or None

        """
        if not expand:
            return None

        return {"expand": ",".join(expand)}

    def get_attachments_metadata(self) -> requests.Response:
        """Get attachments metadata."""
        endpoint: str = f"/cases/{self.params.case_id}/caseComments"
        query_params = {
            "$expand": "caseAttachment",
            "$filter": (
                "caseAttachment/fileName ne null and caseAttachment/fileType "
                "ne null and isDeleted eq false"
            ),
        }
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def add_attachment_to_case_wall(self) -> requests.Response:
        """Add attachment to case wall."""
        endpoint: str = "/legacySdk:legacyAddAttachment"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.attachment.__dict__,
            params={"format": "snake"},
        )

    def create_entity(self) -> requests.Response:
        """Create entity using ExtendCaseGraph"""
        endpoint: str = "/legacyCases:investigatorExtendCaseGraph"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.entity_to_create.to_json(),
        )

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def import_simulator_custom_case(self) -> requests.Response:
        """Import Simulated Custom Case"""
        endpoint: str = "/legacyCases:importCustomCase"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.simulated_case_data,
        )

    def add_or_update_case_task_v5(self) -> requests.Response:
        """Add or Update Case Task for Platform version 5."""
        endpoint: str = "/tasks"
        payload = {
            "title": self.params.title,
            "content": self.params.content,
            "dueTime": self.params.due_date_unix_in_ms,
            "assignee": self.params.owner,
            "caseId": self.params.case_id,
        }
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=payload,
        )

    def add_or_update_case_task_v6(self) -> requests.Response:
        """Add or Update Case Task for Platform version 6."""
        endpoint: str = "/legacySdk:legacyAddOrUpdateCaseTask"
        payload = {
            "owner": self.params.owner,
            "content": self.params.content,
            "dueDate": "",
            "dueDateUnixTimeMs": self.params.due_date_unix_in_ms,
            "title": self.params.title,
            "caseId": self.params.case_id,
        }
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=payload,
        )

    def attach_playbook_to_the_case(self) -> requests.Response:
        """Attach playbook to the case."""
        endpoint: str = "/legacyPlaybooks:legacyAttachWorkflowToCase"
        payload = {
            "cyberCaseId": self.params.case_id,
            "alertGroupIdentifier": self.params.alert_group_identifier,
            "alertIdentifier": self.params.alert_identifier,
            "shouldRunAutomatic": self.params.should_run_automatic,
            "wfName": self.params.playbook_name,
        }
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=payload,
            params={"format": "camel"},
        )

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def search_cases_by_everything(self) -> requests.Response:
        """Get Cases search by everything."""
        endpoint: str = "/legacySearches:legacyCaseSearchEverything"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.search_payload,
            params={"format": "camel"},
        )

    def get_case_activities(self) -> requests.Response:
        """Get case activities using 1P API."""
        endpoint: str = f"/cases/{self.params.case_id}/activities"
        query_params: SingleJson = self.params.query_params or {}
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def get_cases_by_timestamp_filter(self) -> list[SingleJson]:
        """Get cases by timestamp filter"""
        environment = "".join(self.params.environment)
        filter_string = f"updateTime gt {self.params.start_time} and environment eq '{environment}'"
        if getattr(self.params, "case_ids", []) and self.params.case_ids:
            ids_filter: str
            ids_filter = ", ".join([str(case_id) for case_id in self.params.case_ids])
            case_ids_filter: str = f"id in ({ids_filter})"
            filter_string += f" and ({case_ids_filter})"

        base_endpoint = "/cases"
        initial_endpoint = (
            f"{base_endpoint}?$filter={filter_string}"
            "&$select=id, updateTime"
            "&$expand=tags"
            f"&pageSize={_PAGE_SIZE}"
            "&$orderBy=updateTime asc"
        )
        return self._paginate_results(initial_endpoint=initial_endpoint, root_response_key="cases")
