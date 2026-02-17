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

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from TIPCommon.consts import ACTION_NOT_SUPPORTED_PLATFORM_VERSION_MSG
from TIPCommon.exceptions import NotSupportedPlatformVersion
from TIPCommon.rest.custom_types import HttpMethod

from ...consts import DATAPLANE_1P_HEADER
from ...utils import temporarily_remove_header
from .base_soar_api import BaseSoarApi

if TYPE_CHECKING:
    import requests

    from TIPCommon.types import SingleJson


class LegacySoarApi(BaseSoarApi):
    """Chronicle SOAR API client using legacy endpoints."""

    def save_attachment_to_case_wall(self) -> requests.Response:
        """Save an attachment to the case wall using legacy API."""
        endpoint: str = "/cases/AddEvidence/"
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
        endpoint: str = "/entities/GetEntityData"
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
        endpoint: str = "/integrations/GetEnvironmentInstalledIntegrations"
        payload = {
            "name": (
                "*" if self.params.environment == "Shared Instances" else self.params.environment
            )
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_connector_cards(self) -> requests.Response:
        """Get connector cards using legacy API"""
        endpoint: str = "/connectors/cards"
        query_params = {"format": "snake"}
        return self._make_request(HttpMethod.GET, endpoint, params=query_params)

    def get_federation_cases(self) -> requests.Response:
        """Get federation cases using legacy API"""
        endpoint: str = "/federation/cases"
        params = {"continuationToken": self.params.continuation_token}

        return self._make_request(HttpMethod.GET, endpoint, params=params)

    def patch_federation_cases(self) -> requests.Response:
        """Get federation cases using legacy API"""
        endpoint: str = "/federation/cases/batch-patch"
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
        endpoint: str = "/cases/GetWorkflowInstancesCards"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def pause_alert_sla(self) -> requests.Response:
        """Pause alert sla"""
        endpoint: str = "/cases/PauseAlertSla"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "message": self.params.message,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def resume_alert_sla(self) -> requests.Response:
        """Resume alert sla"""
        endpoint: str = "/cases/ResumeAlertSla"
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
        endpoint: str = "/cases/RemoveCaseTag"
        payload = {
            "caseId": self.params.case_id,
            "tag": self.params.tag,
            "alertIdentifier": self.params.alert_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def change_case_description(self) -> requests.Response:
        """Change case description"""
        endpoint: str = "/cases/ChangeCaseDescription?format=snake"
        payload = {
            "case_id": self.params.case_id,
            "description": self.params.description,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def set_alert_priority(self) -> requests.Response:
        """Set alert priority"""
        endpoint: str = "/sdk/UpdateAlertPriority"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "priority": self.params.priority,
            "alertName": self.params.alert_name,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def set_case_score_bulk(self) -> requests.Response:
        """Set case score bulk"""
        endpoint: str = "/sdk/cases/score"
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
        endpoint: str = "/store/GetIntegrationFullDetails"
        payload = {
            "integrationIdentifier": self.params.integration_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def _get_all_integration_instances(self) -> list[SingleJson]:
        """Private helper method to fetch all integration instances from the API.
        This encapsulates the common API call logic.
        """
        endpoint: str = "/integrations/GetOptionalIntegrationInstances"
        payload = {
            "environments": self.params.environments,
            "integrationIdentifier": self.params.integration_identifier,
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
        endpoint: str = "/settings/GetUserProfiles"
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
        endpoint: str = "/sdk/RemoveEntitiesFromCustomList"
        payload = self.params.list_entities_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_entities_to_custom_list(self) -> requests.Response:
        """Add entities to custom list"""
        endpoint: str = "/sdk/AddEntitiesToCustomList"
        payload = self.params.list_entities_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_traking_list_record(self) -> requests.Response:
        """Get traking list record"""
        endpoint: str = "/settings/GetTrackingListRecords"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_traking_list_records_filtered(self) -> requests.Response:
        """Get traking list records filtered"""
        endpoint: str = "/settings/GetTrackingListRecordsFiltered"
        payload = {
            "environments": [self.chronicle_soar.environment],
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def execute_bulk_assign(self) -> requests.Response:
        """Execute bulk assign"""
        endpoint: str = "/cases/ExecuteBulkAssign"
        payload = {"casesIds": self.params.case_ids, "userName": self.params.user_name}
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    @temporarily_remove_header(DATAPLANE_1P_HEADER)
    def execute_bulk_close_case(self) -> requests.Response:
        """Execute bulk close case"""
        endpoint: str = "/cases/ExecuteBulkCloseCase"
        payload = {
            "casesIds": self.params.case_ids,
            "closeReason": self.params.close_reason,
            "rootCause": self.params.root_cause,
            "closeComment": self.params.close_comment,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_users_profile_cards(self) -> requests.Response:
        """Get users profile cards."""
        endpoint: str = "/settings/GetUserProfileCards"
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

    def pause_case_sla(self, case_id: int, message: str | None = None) -> requests.Response:
        raise NotSupportedPlatformVersion(ACTION_NOT_SUPPORTED_PLATFORM_VERSION_MSG)

    def resume_case_sla(self, case_id: int) -> requests.Response:
        raise NotSupportedPlatformVersion(ACTION_NOT_SUPPORTED_PLATFORM_VERSION_MSG)

    def rename_case(self) -> requests.Response:
        """Rename case"""
        endpoint: str = "/cases/RenameCase"
        payload = {
            "caseId": self.params.case_id,
            "title": self.params.case_title,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_comment_to_entity(self) -> requests.Response:
        """Add comment to entity"""
        endpoint: str = "/entities/AddNote?format=camel"
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
        endpoint: str = "/cases/AssignUserToCase"
        payload = {
            "caseId": self.params.case_id,
            "alertIdentifier": self.params.alert_identifier,
            "userId": self.params.assign_to,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_email_template(self) -> requests.Response:
        """Get email template"""
        endpoint: str = "/settings/GetEmailTemplateRecords?format=camel"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_siemplify_user_details(self) -> requests.Response:
        """Get siemplify user details"""
        endpoint: str = "/settings/GetUserProfiles"
        payload = {
            "searchTerm": self.params.search_term,
            "filterRole": self.params.filter_by_role,
            "requestedPage": self.params.requested_page,
            "pageSize": self.params.page_size,
            "shouldHideDisabledUsers": self.params.should_hide_disabled_users,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_domain_alias(self) -> requests.Response:
        """Get domain alias"""
        endpoint: str = "/settings/GetDomainAliases?format=camel"
        payload = {"searchTerm": "", "requestedPage": self.params.page_count, "pageSize": 100}
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_tags_to_case_in_bulk(self) -> requests.Response:
        """Add tags to case in bulk"""
        endpoint: str = "/cases/ExecuteBulkAddCaseTag"
        payload = {"casesIds": self.params.case_ids, "tags": self.params.tags}
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
        start_dt_object = datetime.fromtimestamp(start_time_s, tz=UTC)
        start_time_iso = start_dt_object.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        end_time_s = self.params.end_time / 1000.0
        end_dt_object = datetime.fromtimestamp(end_time_s, tz=UTC)
        end_time_iso = end_dt_object.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        while True:
            endpoint: str = "/search/CaseSearchEverything?format=camel"
            payload = {
                "pageSize": page_size,
                "startTime": start_time_iso,
                "endTime": end_time_iso,
                "environments": self.params.environment,
                "requestedPage": current_page,
                "timeRangeFilter": self.params.time_range_filter,
            }

            response = self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

            results = response.json().get("results")

            if not results:
                break

            all_cases.extend(results)
            current_page += 1

        return all_cases

    def get_bearer_token(self) -> requests.Response:
        """Get bearer token."""
        endpoint: str = "/auth/login"
        payload = {
            "password": self.params.smp_password,
            "username": self.params.smp_username,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def update_api_record(self) -> requests.Response:
        """Update api record."""
        endpoint: str = "/settings/addOrUpdateAPIKeyRecord"
        return self._make_request(
            HttpMethod.POST, endpoint, json_payload=self.params.api_record
        )

    def get_store_data(self) -> SingleJson:
        """Get store data."""
        endpoint_integrations = "/store/GetIntegrationsStoreData"
        endpoint_powerups = "/store/GetPowerUpsStoreData"

        integrations_data = self._make_request(
            HttpMethod.GET,
            endpoint_integrations
        ).json()

        powerups_data = self._make_request(
            HttpMethod.GET,
            endpoint_powerups
        ).json()

        combined_response = {
            "integrations": (
                    integrations_data.get("integrations", [])
                    + powerups_data.get("integrations", [])
            )
        }

        return combined_response

    def import_package(self) -> requests.Response:
        """Import package."""
        endpoint: str = "/ide/ImportPackage"
        data = {
            "data": self.params.b64_blob,
            "integrationIdentifier": self.params.integration_name,
            "isCustom": True,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=data)

    def update_ide_item(self) -> requests.Response:
        """Update ide item."""
        endpoint: str = "/ide/AddOrUpdateItem"
        return self._make_request(
            HttpMethod.POST, endpoint, json_payload=self.params.input_json
        )

    def get_ide_cards(self) -> requests.Response:
        """Get ide cards."""
        endpoint: str = "/ide/GetIdeItemCards"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_ide_item(self) -> requests.Response:
        """Get ide item."""
        endpoint: str = "/ide/GetIdeItem"
        query = {
            "itemId": self.params.item_id,
            "ideItemType": self.params.item_type,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=query)

    def add_custom_family(self) -> requests.Response:
        """Add custom family."""
        endpoint: str = "/ontology/AddOrUpdateVisualFamily"
        return self._make_request(
            HttpMethod.POST, endpoint, json_payload=self.params.visual_family
        )

    def get_mapping_rules(self) -> requests.Response:
        """Get mapping rules."""
        endpoint: str = "/ontology/GetMappingRulesForSettings"
        payload = {
            "source": self.params.source,
            "product": self.params.product,
            "eventName": self.params.event_name,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_mapping_rules(self) -> requests.Response:
        """Add mapping rules."""
        endpoint: str = "/ontology/AddOrUpdateMappingRules"
        return self._make_request(
            HttpMethod.POST, endpoint, json_payload=self.params.mapping_rule
        )

    def set_mappings_visual_family(self) -> requests.Response:
        """Set mappings visual family."""
        endpoint: str = "/ontology/AddOrUpdateProductToVisualizationFamilyRecord"
        payload = {
            "source": self.params.source,
            "product": self.params.product or "",
            "eventName": self.params.event_name,
            "visualFamily": self.params.visual_family,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def export_playbooks(self) -> requests.Response:
        """Export playbooks."""
        endpoint: str = "/playbooks/ExportDefinitions"
        payload = {"identifiers": self.params.definitions}
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def import_playbooks(self) -> requests.Response:
        """Import playbooks."""
        endpoint: str = "/playbooks/ImportDefinitions"
        return self._make_request(
            HttpMethod.POST, endpoint, json_payload=self.params.playbooks
        )

    def create_playbook_category(self) -> requests.Response:
        """Create playbook category."""
        endpoint: str = "/playbooks/AddOrUpdatePlaybookCategory"
        req = {
            "categoryState": 0,
            "id": 0,
            "isDefaultCategory": False,
            "name": self.params.name,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=req)

    def get_playbook_categories(self) -> requests.Response:
        """Get playbook categories."""
        endpoint: str = "/playbooks/GetWorkflowCategories"
        return self._make_request(HttpMethod.GET, endpoint)

    def update_connector(self) -> requests.Response:
        """Update connector."""
        endpoint: str = "/connectors/AddOrUpdateConnector"
        return self._make_request(
            HttpMethod.POST, endpoint, json_payload=self.params.connector_data
        )

    def add_job(self) -> requests.Response:
        """Add job."""
        endpoint: str = "/jobs/SaveOrUpdateJobData"
        return self._make_request(HttpMethod.POST, endpoint, json_payload=self.params.job)

    def add_email_template(self) -> requests.Response:
        """Add email template."""
        endpoint: str = "/settings/AddEmailTemplateRecords"
        return self._make_request(
            HttpMethod.POST, endpoint, json_payload=self.params.template
        )

    def get_denylists(self) -> requests.Response:
        """Get denylists."""
        endpoint: str = "/settings/GetAllModelBlockRecords"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_simulated_cases(self) -> requests.Response:
        """Get simulated cases."""
        endpoint: str = "/attackssimulator/GetCustomCases"
        return self._make_request(HttpMethod.GET, endpoint)

    def export_simulated_case(self) -> requests.Response:
        """Export simulated cases"""
        name = self.params.name
        endpoint = f"/attackssimulator/ExportCustomCase/{name}"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_case_insights_comment_evidence(self) -> requests.Response:
        """Get case insights using legacy API."""
        endpoint = f"/cases/insights/{self.params.case_id}"
        return self._make_request(HttpMethod.GET, endpoint)

    def save_case_title_settings(self) -> requests.Response:
        """Save case title settings."""
        endpoint: str = "/settings/SaveCaseTitleSettings"
        payload = [{
            "value": self.params.value,
            "order": 0,
        }]
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_or_update_company_logo(self) -> requests.Response:
        """Add or update company logo."""
        endpoint: str = "/settings/AddOrUpdateCompanyLogo"
        payload = self.params.logo_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def attache_workflow_to_case(self) -> requests.Response:
        """Attache workflow to case"""
        endpoint: str = "/playbooks/AttachWorkflowToCase"
        payload = {
            "cyberCaseId": self.params.case_id,
            "alertGroupIdentifier": self.params.alert_group_identifier,
            "alertIdentifier": self.params.alert_identifier,
            "wfName": self.params.wf_name,
            "shouldRunAutomatic": True,
            "originalWorkflowDefinitionIdentifier": self.params.original_wf_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def import_custom_case(self) -> requests.Response:
        """Import custom case"""
        endpoint: str = "/attackssimulator/ImportCustomCase"
        payload = self.params.case_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def case_search_everything(self) -> requests.Response:
        """Case search everything"""
        endpoint: str = "/search/CaseSearchEverything"
        payload = self.params.search_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_environment_action_definition(self) -> requests.Response:
        """Get environment action definition"""
        endpoint: str = "/settings/GetEnvironmentActionDefinitions"
        payload = self.params.environment_action_data
        return self._make_request(HttpMethod.GET, endpoint, json_payload=payload)

    def get_all_model_block_records(self) -> requests.Response:
        """Get all model block records."""
        endpoint: str = "settings/GetAllModelBlockRecords"
        return self.get_page_results(endpoint)

    def get_company_logo(self) -> requests.Response:
        """Get company logo."""
        endpoint: str = "settings/GetCompanyLogo"
        return self.get_page_results(endpoint)

    def get_case_title_settings(self) -> requests.Response:
        """Get case title settings."""
        endpoint: str = "/settings/GetCaseTitleSettings"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_system_version(self) -> requests.Response:
        """Get system version"""
        endpoint: str = "/settings/GetSystemVersion"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_environment_group_names(self) -> requests.Response:
        """Get environment group names"""
        endpoint: str = "/environment-groups"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_env_dynamic_parameters(self) -> requests.Response:
        """Get environment dynamic parameters"""
        endpoint: str = "/settings/GetDynamicParameters"
        return self._make_request(HttpMethod.GET, endpoint)

    def add_dynamic_env_param(self) -> requests.Response:
        """Add dynamic environment parameter"""
        endpoint: str = "/settings/AddOrUpdateDynamicParameters"
        payload = {
            "id": self.params.id,
            "name": self.params.name,
            "type": self.params.type,
            "defaultValue": self.params.default_value,
            "optionalValues": self.params.optional_json,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def install_integration(self) -> requests.Response:
        """Install integration"""
        endpoint: str = "/store/DownloadAndInstallIntegrationFromLocalStore"
        payload = {
            "name": self.params.integration_name,
            "identifier": self.params.integration_identifier,
            "version": self.params.version,
            "isCertified": self.params.is_certified,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def export_package(self) -> requests.Response:
        """Export package"""
        endpoint = (
            f"/ide/ExportPackage/{self.params.integration_identifier}"
        )
        return self._make_request(HttpMethod.GET, endpoint)

    def get_integration_instance_settings(self) -> requests.Response:
        """Get integration instance settings"""
        endpoint = (
            "/integrations/GetIntegrationInstanceSettings/"
            f"{self.params.instance_id}"
        )
        return self._make_request(HttpMethod.GET, endpoint)

    def create_integrations_instance(self) -> requests.Response:
        """Create integrations instance"""
        endpoint: str = "/integrations/CreateIntegrationInstance"
        payload = {
            "environment": self.params.environment,
            "integrationIdentifier": self.params.integration_identifier,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_page_results(self, url):
        payload = {"searchTerm": "", "requestedPage": 0, "pageSize": 100}
        res = self._make_request(HttpMethod.POST, url, json_payload=payload)
        results = res.json()["objectsList"]
        if res.json()["metadata"]["totalNumberOfPages"] > 1:
            for page in range(res.json()["metadata"]["totalNumberOfPages"] - 1):
                payload["requestedPage"] = page + 1
                res = self._make_request(HttpMethod.POST, url, json_payload=payload)
                results.extend(res.json()["objectsList"])

        return results

    def get_domains(self) -> requests.Response:
        """Get domains"""
        return self.get_page_results("/settings/GetDomainAliases")

    def update_domain(self) -> requests.Response:
        """Update domain"""
        endpoint: str = "/settings/AddOrUpdateDomainAliasesRecords"
        payload = self.params.domain_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_environment_names(self) -> requests.Response:
        """Get environment names"""
        return self.get_page_results("/settings/GetEnvironmentNames")

    def get_environments(self) -> requests.Response:
        """Get environments"""
        return self.get_page_results("/settings/GetEnvironments")

    def import_environment(self) -> requests.Response:
        """Import environment"""
        endpoint: str = "/settings/AddOrUpdateEnvironmentRecords"
        payload = self.params.environment_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def save_integration_instance_settings(self) -> requests.Response:
        """Save integration instance settings"""
        endpoint: str = "/store/SaveIntegrationConfigurationProperties"
        payload = {
            "instanceIdentifier": self.params.identifier,
            **self.params.integration_data,
        }
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def import_simulated_case(self) -> requests.Response:
        """Update domain"""
        endpoint: str = "/attackssimulator/ImportCustomCase"
        payload = self.params.case_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_case_tag(self) -> requests.Response:
        """Add case tag"""
        endpoint: str = "/settings/AddTagDefinitionsRecords"
        payload = self.params.case_tag
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def add_case_stage(self) -> requests.Response:
        """Add case stage"""
        endpoint: str = "/settings/AddCaseStageDefinitionRecord"
        payload = self.params.case_stage
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_case_alert(self) -> requests.Response:
        """Get case alert"""
        endpoint: str = "/settings/GetRootCauseCloseRecords"
        return self._make_request(HttpMethod.GET, endpoint)

    def add_close_reason(self) -> requests.Response:
        """Add close reason"""
        endpoint: str = "/settings/AddOrUpdateRootCauseClose"
        payload = self.params.close_reason
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_networks(self) -> requests.Response:
        """Get networks"""
        return self.get_page_results("/settings/GetNetworkDetails")

    def update_network(self) -> requests.Response:
        """Update network"""
        endpoint: str = "/settings/AddOrUpdateNetworkDetailsRecords"
        payload = self.params.network_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_custom_lists(self) -> requests.Response:
        """Get custom lists"""
        endpoint: str = "/settings/GetTrackingListRecords"
        return self._make_request(HttpMethod.GET, endpoint)

    def update_custom_list(self) -> requests.Response:
        """Update custom list"""
        endpoint: str = "/settings/AddorUpdateTrackingListRecords"
        payload = self.params.tracking_list
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def update_blocklist(self) -> requests.Response:
        """Update blocklist"""
        endpoint: str = "/settings/AddOrUpdateModelBlockRecords"
        payload = self.params.blocklist_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def update_sla_record(self) -> requests.Response:
        """Update sla record"""
        endpoint: str = "/settings/AddSlaDefinitionsRecord"
        payload = self.params.sla_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def save_playbook(self) -> requests.Response:
        """Save playbook"""
        endpoint: str = "/playbooks/SaveWorkflowDefinitions"
        payload = self.params.playbook_data
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_playbooks_workflow_menu_cards(self) -> requests.Response:
        """Get playbooks workflow menu cards."""
        endpoint: str = "/playbooks/GetWorkflowMenuCards"
        payload: list[int] = self.params.api_payload
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_playbooks_workflow_menu_cards_with_env(self) -> requests.Response:
        """Get playbooks workflow menu cards with environment filter."""
        endpoint: str = "/playbooks/GetWorkflowMenuCardsWithEnvFilter"
        payload: list[int] = self.params.api_payload
        return self._make_request(HttpMethod.POST, endpoint, json_payload=payload)

    def get_playbook_workflow_menu_cards_by_identifier(self) -> requests.Response:
        """Get playbook workflow menu cards by identifier."""
        endpoint: str = (
            "/playbooks/GetWorkflowFullInfoByIdentifier/"
            f"{self.params.playbook_identifier}"
        )
        return self._make_request(HttpMethod.GET, endpoint)

    def get_playbook_workflow_menu_cards_by_identifier_with_env(
            self,
    ) -> requests.Response:
        """Get playbook workflow menu cards by identifier with environment filter."""
        endpoint: str = (
            "/playbooks/GetWorkflowFullInfoWithEnvFilterByIdentifier/"
            f"{self.params.playbook_identifier}"
        )
        return self._make_request(HttpMethod.GET, endpoint)

    def get_installed_jobs(self) -> requests.Response:
        """Get installed jobs."""
        endpoint: str = "/jobs/GetInstalledJobs"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_installed_connectors(self) -> requests.Response:
        """Get installed connectors."""
        endpoint: str = "/connectors/GetConnectorsData"
        return self._make_request(
            HttpMethod.GET,
            endpoint
        ).json()["installedConnectors"]

    def get_visual_families(self) -> requests.Response:
        """Get custom visual families."""
        endpoint: str = "/ontology/GetVisualFamilies"
        return self._make_request(HttpMethod.GET, endpoint)

    def get_visual_family_by_id(self) -> requests.Response:
        """Get custom visual family by ID."""
        endpoint: str = (
            f"/ontology/GetFamilyData/{self.params.family_id}"
        )
        return self._make_request(HttpMethod.GET, endpoint)

    def get_ontology_records(self) -> requests.Response:
        """Get ontology records"""
        endpoint: str = "/ontology/GetOntologyStatusRecords"
        return self.get_page_results(endpoint)

    def get_case_tags(self) -> requests.Response:
        """Get case tags"""
        endpoint: str = "/settings/GetTagDefinitionsRecords"
        return self.get_page_results(endpoint)

    def get_case_stages(self) -> requests.Response:
        """Get case stages"""
        endpoint: str = "/settings/GetCaseStageDefinitionRecords"
        return self.get_page_results(endpoint)

    def get_case_close_reasons(self) -> requests.Response:
        """Get case close reasons"""
        return self.get_case_alert()

    def get_block_lists_details(self) -> requests.Response:
        """Get block lists details"""
        endpoint: str = "/settings/GetBlockListDetails"
        return self.get_page_results(endpoint)

    def get_sla_records(self) -> requests.Response:
        """Get sla records"""
        endpoint = "/settings/GetSlaDefinitionsRecords"
        return self._make_request(HttpMethod.GET, endpoint)
