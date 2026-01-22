"""Provides the Legacy API client implementation for interacting with Chronicle SOAR."""

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

from datetime import datetime, timezone

from TIPCommon.rest.custom_types import HttpMethod

from TIPCommon.consts import ACTION_NOT_SUPPORTED_PLATFORM_VERSION_MSG

from TIPCommon.exceptions import NotSupportedPlatformVersion

from .base_soar_api import BaseSoarApi
from ...consts import DATAPLANE_1P_HEADER
from ...utils import temporarily_remove_header

if TYPE_CHECKING:
    import requests
    from TIPCommon.types import SingleJson


class LegacySoarApi(BaseSoarApi):
    """Chronicle SOAR API client using legacy endpoints."""

    def save_attachment_to_case_wall(self) -> requests.Response:
        """Save an attachment to the case wall using legacy API."""
        endpoint = "/cases/AddEvidence/"
        payload = {
            "CaseIdentifier": self.params.case_id,
            "Base64Blob": self.params.base64_blob,
            "Name": self.params.name,
            "Description": self.params.description,
            "Type": self.params.file_type,
            "IsImportant": self.params.is_important,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def get_entity_data(self) -> requests.Response:
        """Get entity data using legacy API."""
        endpoint = "/entities/GetEntityData"
        payload = {
            "entityIdentifier": self.params.entity_identifier,
            "entityType": self.params.entity_type,
            "entityEnvironment": self.params.entity_environment,
            "lastCaseType": self.params.last_case_type,
            "caseDistributionType": self.params.case_distribution_type,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def get_full_case_details(self) -> requests.Response:
        """Get full case details using legacy API."""
        endpoint = f"/cases/GetCaseFullDetails/{self.params.case_id}"
        query_params = {"format": getattr(self.params, "format", "snake")}
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def get_case_insights(self) -> requests.Response:
        """Get case insights using legacy API."""
        self.params.format = "camel"
        return self.get_full_case_details()

    def get_installed_integrations_of_environment(self) -> requests.Response:
        """Get installed integrations of environment using legacy API."""
        endpoint = "/integrations/GetEnvironmentInstalledIntegrations"
        payload = {
            "name": (
                "*"
                if self.params.environment == "Shared Instances"
                else self.params.environment
            )
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_connector_cards(self) -> requests.Response:
        """Get connector cards using legacy API"""
        endpoint = "/connectors/cards"
        query_params = {"format": "snake"}
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def get_federation_cases(self) -> requests.Response:
        """Get federation cases using legacy API"""
        endpoint = "/federation/cases"
        params = {"continuationToken": self.params.continuation_token}

        return self._make_request(HttpMethod.GET, endpoint, params=params)

    def patch_federation_cases(self) -> requests.Response:
        """Get federation cases using legacy API"""
        endpoint = "/federation/cases/batch-patch"
        headers = {"AppKey": self.params.api_key} if self.params.api_key else None
        payload = {"cases": self.params.cases_payload}
        return self._make_request(
            HttpMethod.PATCH,
            endpoint,
            json_payload=payload,
            headers=headers,
        )

    def get_workflow_instance_card(self) -> requests.Response:
        """Get workflow instance card using legacy API"""
        endpoint = "/cases/GetWorkflowInstancesCards"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def pause_alert_sla(self) -> requests.Response:
        """Pause alert sla"""
        endpoint = "/cases/PauseAlertSla"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "message": self.params.message,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def resume_alert_sla(self) -> requests.Response:
        """Resume alert sla"""
        endpoint = "/cases/ResumeAlertSla"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "message": self.params.message,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_case_overview_details(self) -> requests.Response:
        """Get case overview details"""
        case_id = self.params.case_id
        endpoint = f"/dynamic-cases/GetCaseDetails/{case_id}"
        return self._make_request(HttpMethod.GET, endpoint).json()

    def remove_case_tag(self) -> requests.Response:
        """Remove case tag"""
        endpoint = "/cases/RemoveCaseTag"
        payload = {
            "caseId": self.params.case_id,
            "tag": self.params.tag,
            "alertIdentifier": self.params.alert_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def change_case_description(self) -> requests.Response:
        """Change case description"""
        endpoint = "/cases/ChangeCaseDescription?format=snake"
        payload = {
            "case_id": self.params.case_id,
            "description": self.params.description,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def set_alert_priority(self) -> requests.Response:
        """Set alert priority"""
        endpoint = "/sdk/UpdateAlertPriority"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "priority": self.params.priority,
            "alertName": self.params.alert_name,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def set_case_score_bulk(self) -> requests.Response:
        """Set case score bulk"""
        endpoint = "/sdk/cases/score"
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
        endpoint = "/store/GetIntegrationFullDetails"
        payload = {
            "integrationIdentifier": self.params.integration_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def _get_all_integration_instances(self) -> list[SingleJson]:
        """
        Private helper method to fetch all integration instances from the API.
        This encapsulates the common API call logic.
        """
        endpoint = "/integrations/GetOptionalIntegrationInstances"
        payload = {
            "environments": self.params.environments,
            "integrationIdentifier": self.params.integration_identifier
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_integration_instance_details_by_id(self) -> requests.Response:
        """Get integration instance details by instance id"""
        return self._get_all_integration_instances()

    def get_integration_instance_details_by_name(self) -> requests.Response:
        """Get integration instance details by instance name"""
        return self._get_all_integration_instances()

    def get_users_profile(self) -> requests.Response:
        """Get users profile"""
        endpoint = "/settings/GetUserProfiles"
        payload = {
            "searchTerm": self.params.search_term,
            "filterRole": self.params.filter_by_role,
            "requestedPage": self.params.requested_page,
            "pageSize": self.params.page_size,
            "shouldHideDisabledUsers": self.params.should_hide_disabled_users,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_investigator_data(self) -> requests.Response:
        """Get investigator data"""
        case_id = self.params.case_id
        endpoint = f"/investigator/GetInvestigatorData/{case_id}"
        return self._make_request(HttpMethod.GET, endpoint)

    def remove_entities_from_custom_list(self) -> requests.Response:
        """Remove entities from custom list"""
        endpoint = "/sdk/RemoveEntitiesFromCustomList"
        payload = self.params.list_entities_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_entities_to_custom_list(self) -> requests.Response:
        """Add entities to custom list"""
        endpoint = "/sdk/AddEntitiesToCustomList"
        payload = self.params.list_entities_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_traking_list_record(self) -> requests.Response:
        """Get traking list record"""
        endpoint = "/settings/GetTrackingListRecords"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_traking_list_records_filtered(self) -> requests.Response:
        """Get traking list records filtered"""
        endpoint = "/settings/GetTrackingListRecordsFiltered"
        payload = {
            "environments": [self.chronicle_soar.environment],
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def execute_bulk_assign(self) -> requests.Response:
        """Execute bulk assign"""
        endpoint = "/cases/ExecuteBulkAssign"
        payload = {
            "casesIds": self.params.case_ids,
            "userName": self.params.user_name
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def execute_bulk_close_case(self) -> requests.Response:
        """Execute bulk close case"""
        endpoint = "/cases/ExecuteBulkCloseCase"
        payload = {
            "casesIds": self.params.case_ids,
            "closeReason": self.params.close_reason,
            "rootCause": self.params.root_cause,
            "closeComment": self.params.close_comment
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_users_profile_cards(self) -> requests.Response:
        """Get users profile cards."""
        endpoint = "/settings/GetUserProfileCards"
        payload = {
            "searchTerm": self.params.search_term,
            "requestedPage": self.params.requested_page,
            "pageSize": self.params.page_size,
            "filterRole": self.params.filter_by_role,
            "filterDisabledUsers": self.params.filter_disabled_users,
            "filterSupportUsers": self.params.filter_support_users,
            "fetchOnlySupportUsers": self.params.fetch_only_support_users,
            "filterPermissionTypes": self.params.filter_permission_types,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_security_events(self) -> requests.Response:
        """Get security events"""
        return self.get_full_case_details()

    def get_entity_cards(self) -> requests.Response:
        """Get entity cards"""
        return self.get_full_case_details()

    def pause_case_sla(
        self, case_id: int, message: str | None = None
    ) -> requests.Response:
        raise NotSupportedPlatformVersion(ACTION_NOT_SUPPORTED_PLATFORM_VERSION_MSG)

    def resume_case_sla(self, case_id: int) -> requests.Response:
        raise NotSupportedPlatformVersion(ACTION_NOT_SUPPORTED_PLATFORM_VERSION_MSG)

    def rename_case(self) -> requests.Response:
        """Rename case"""
        endpoint = "/cases/RenameCase"
        payload = {
            "caseId": self.params.case_id,
            "title": self.params.case_title,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_comment_to_entity(self) -> requests.Response:
        """Add comment to entity"""
        endpoint = "/entities/AddNote?format=camel"
        payload = {
            "author": self.params.author,
            "content": self.params.content,
            "entityIdentifier": self.params.entity_identifier,
            "id": self.params.entity_id,
            "entityEnvironment": self.params.entity_environment,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def assign_case_to_user(self) -> requests.Response:
        """Assign case to user"""
        endpoint = "/cases/AssignUserToCase"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "userId": self.params.assign_to,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_email_template(self) -> requests.Response:
        """Get email template"""
        endpoint = "/settings/GetEmailTemplateRecords?format=camel"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_siemplify_user_details(self) -> requests.Response:
        """Get siemplify user details"""
        endpoint = "/settings/GetUserProfiles"
        payload = {
            "searchTerm": self.params.search_term,
            "filterRole": self.params.filter_by_role,
            "requestedPage": self.params.requested_page,
            "pageSize": self.params.page_size,
            "shouldHideDisabledUsers": self.params.should_hide_disabled_users
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_domain_alias(self) -> requests.Response:
        """Get domain alias"""
        endpoint = "/settings/GetDomainAliases?format=camel"
        payload = {
            "searchTerm": "",
            "requestedPage": self.params.page_count,
            "pageSize": 100
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_tags_to_case_in_bulk(self) -> requests.Response:
        """Add tags to case in bulk"""
        endpoint = "/cases/ExecuteBulkAddCaseTag"
        payload = {
            "casesIds": self.params.case_ids,
            "tags": self.params.tags
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_installed_jobs(self) -> requests.Response:
        """Get installed jobs."""
        endpoint: str = "/jobs/GetInstalledJobs"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_all_case_overview_details(self) -> requests.Response:
        """Get case overview details"""
        self.params.format = "camel"
        return self.get_full_case_details().json()

    def get_entity_expand_cards(self) -> requests.Response:
        """Get entity cards"""
        return self.get_full_case_details()

    def get_case_wall_records(self) -> requests.Response:
        """Get case wall records"""
        return self.get_full_case_details()

    def get_attachments_metadata(self) -> requests.Response:
        """Get attachments metadata."""
        return self.get_full_case_details()

    def add_attachment_to_case_wall(self) -> requests.Response:
        """Add attachment to case wall."""
        endpoint: str = "/sdk/AddAttachment"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.attachment.__dict__,
            params={"format": "snake"},
        )

    def create_entity(self) -> requests.Response:
        """Create entity using ExtendCaseGraph"""
        endpoint: str = "/investigator/ExtendCaseGraph"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.entity_to_create.to_json(),
        )

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def import_simulator_custom_case(self) -> requests.Response:
        """Import Simulated Custom Case"""
        endpoint: str = "/attackssimulator/ImportCustomCase"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.simulated_case_data,
        )

    def add_or_update_case_task_v5(self) -> requests.Response:
        """Add or Update Case Task for Platform version 5."""
        endpoint: str = "/cases/AddOrUpdateCaseTask"
        payload = {
            "owner": self.params.owner,
            "name": self.params.content,
            "dueDate": "",
            "dueDateUnixTimeMs": self.params.due_date_unix_in_ms,
            "caseId": self.params.case_id,
        }
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=payload,
        )

    def add_or_update_case_task_v6(self) -> requests.Response:
        """Add or Update Case Task for Platform version 6."""
        endpoint: str = "/sdk/AddOrUpdateCaseTask"
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
        endpoint: str = "/playbooks/AttacheWorkflowToCase"
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
        endpoint: str = "/search/CaseSearchEverything"
        return self._make_request(
            HttpMethod.POST,
            endpoint,
            json_payload=self.params.search_payload,
            params={"format": "camel"},
        )

    def get_case_activities(self) -> requests.Response:
        """Get case activities using legacy API."""
        endpoint: str = f"/cases/insights/{self.params.case_id}"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_cases_by_timestamp_filter(self) -> list[SingleJson]:
        """Get cases by timestamp filter"""
        all_cases: list[SingleJson] = []
        current_page = 0
        page_size = 1000

        start_time_s = self.params.start_time / 1000.0
        start_dt_object = datetime.fromtimestamp(start_time_s, tz=timezone.utc)
        start_time_iso = start_dt_object.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        end_time_s = self.params.end_time / 1000.0
        end_dt_object = datetime.fromtimestamp(end_time_s, tz=timezone.utc)
        end_time_iso = end_dt_object.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        while True:
            endpoint = "/search/CaseSearchEverything?format=camel"
            payload = {
                "pageSize": page_size,
                "startTime": start_time_iso,
                "endTime": end_time_iso,
                "environments": self.params.environment,
                "requestedPage": current_page,
                "timeRangeFilter": self.params.time_range_filter,
            }

            response = self._make_request(
                HttpMethod.POST, endpoint, json_payload=payload
            )

            results = response.json().get("results")

            if not results:
                break

            all_cases.extend(results)
            current_page += 1

        return all_cases
