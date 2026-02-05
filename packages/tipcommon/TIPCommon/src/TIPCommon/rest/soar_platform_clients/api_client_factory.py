"""Factory for creating SOAR API clients based on platform capabilities."""

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

from TIPCommon.utils import platform_supports_1p_api

from .legacy_soar_api import LegacySoarApi
from .one_platform_soar_api import OnePlatformSoarApi

if TYPE_CHECKING:
    import requests

    from TIPCommon.types import ChronicleSOAR

from typing import Protocol


class SoarApiClient(Protocol):
    """Defines the interface for a SOAR API client.

    This protocol ensures that any SOAR API client implementation will have
    the necessary methods defined.
    """

    def save_attachment_to_case_wall(self) -> requests.Response:
        """Save an attachment to the case wall.

        Parameters for the attachment (like case_id, blob, name, etc.)
        are expected to be set on the client instance's `params` attribute
        before calling this method.
        """

    def get_entity_data(self) -> requests.Response:
        """Get entity data."""

    def get_full_case_details(self) -> requests.Response:
        """Get full case details."""

    def get_case_insights(self) -> requests.Response:
        """Get case insights."""

    def get_installed_integrations_of_environment(self) -> requests.Response:
        """Get installed integrations of environment."""

    def get_connector_cards(self) -> requests.Response:
        """Get connector cards."""

    def get_federation_cases(self) -> requests.Response:
        """Get federation cases"""

    def get_workflow_instance_card(self) -> requests.Response:
        """Get workflow instance card"""

    def patch_federation_cases(self) -> requests.Response:
        """Patch federation cases"""

    def pause_alert_sla(self) -> requests.Response:
        """Pause alert sla"""

    def resume_alert_sla(self) -> requests.Response:
        """Resume alert sla"""

    def get_case_overview_details(self) -> requests.Response:
        """Get case overview details"""

    def remove_case_tag(self) -> requests.Response:
        """Remove case tag"""

    def change_case_description(self) -> requests.Response:
        """Change case description"""

    def set_alert_priority(self) -> requests.Response:
        """Set alert priority"""

    def set_case_score_bulk(self) -> requests.Response:
        """Set case score bulk"""

    def get_integration_full_details(self) -> requests.Response:
        """Get integration full details"""

    def get_users_profile(self) -> requests.Response:
        """Get users profile"""

    def get_integration_instance_details_by_id(self) -> requests.Response:
        """Get integration instance details by id"""

    def get_integration_instance_details_by_name(self) -> requests.Response:
        """Get integration instance details by name"""

    def remove_entities_from_custom_list(self) -> requests.Response:
        """Remove entities from custom list"""

    def add_entities_to_custom_list(self) -> requests.Response:
        """Add entities to custom list"""

    def get_traking_list_record(self) -> requests.Response:
        """Get traking list record"""

    def get_traking_list_records_filtered(self) -> requests.Response:
        """Get traking list records filtered"""

    def case_search_everything(self) -> requests.Response:
        """Case search everthing"""

    def account_login(self) -> requests.Response:
        """Account login"""

    def execute_bulk_assign(self) -> requests.Response:
        """Execute bulk assign"""

    def execute_bulk_close_case(self) -> requests.Response:
        """Execute bulk close case"""

    def get_users_profile_cards(self) -> requests.Response:
        """Get users profile cards"""

    def get_security_events(self) -> requests.Response:
        """Get security events"""

    def get_entity_cards(self) -> requests.Response:
        """Get entity cards"""

    def pause_case_sla(
        self,
        case_id: int,
        message: str | None = None,
    ) -> requests.Response:
        """Pause Case SLA"""

    def resume_case_sla(self, case_id: int) -> requests.Response:
        """Resume Case SLA"""

    def rename_case(self) -> requests.Response:
        """Rename case"""

    def add_comment_to_entity(self) -> requests.Response:
        """Add comment to entity"""

    def assign_case_to_user(self) -> requests.Response:
        """Assign case to user"""

    def get_email_template(self) -> requests.Response:
        """Get email template"""

    def get_siemplify_user_details(self) -> requests.Response:
        """Get siemplify user details"""

    def get_domain_alias(self) -> requests.Response:
        """Get domain alias"""

    def add_tags_to_case_in_bulk(self) -> requests.Response:
        """Add tags to case in bulk"""

    def get_installed_jobs(self) -> requests.Response:
        """Get installed jobs."""

    def get_all_case_overview_details(self) -> requests.Response:
        """Get all case overview details"""

    def get_entity_expand_cards(self) -> requests.Response:
        """Get entity cards"""

    def get_case_wall_records(self) -> requests.Response:
        """Get case wall records"""

    def get_attachments_metadata(self) -> requests.Response:
        """Get attachments metadata."""

    def add_attachment_to_case_wall(self) -> requests.Response:
        """Add attachment to case wall."""

    def create_entity(self) -> requests.Response:
        """Create entity using ExtendCaseGraph"""

    def import_simulator_custom_case(self) -> requests.Response:
        """Import Simulated Custom Case"""

    def add_or_update_case_task_v5(self) -> requests.Response:
        """Add or Update Case Task for Platform version 5."""

    def add_or_update_case_task_v6(self) -> requests.Response:
        """Add or Update Case Task for Platform version 6."""

    def attach_playbook_to_the_case(self) -> requests.Response:
        """Attach playbook to the case."""

    def search_cases_by_everything(self) -> requests.Response:
        """Get Cases search by everything."""

    def get_case_activities(self) -> requests.Response:
        """Get case activities."""

    def get_cases_by_timestamp_filter(self) -> requests.Response:
        """Get cases by timestamp filter"""

    def get_email_templates(self) -> requests.Response:
        """Get email templates"""

    def get_system_version(self) -> requests.Response:
        """Get domain alias"""

    def get_environment_group_names(self) -> requests.Response:
        """Get environment group names"""

    def get_env_dynamic_parameters(self) -> requests.Response:
        """Get env dynamic parameters"""

    def add_dynamic_env_param(self) -> requests.Response:
        """Add dynamic env param"""

    def install_integration(self) -> requests.Response:
        """Install integration"""

    def export_package(self) -> requests.Response:
        """Export package"""

    def get_integration_instance_settings(self) -> requests.Response:
        """Get integration instance settings"""

    def create_integrations_instance(self) -> requests.Response:
        """Create integrations instance"""

    def get_domains(self) -> requests.Response:
        """Get domains"""

    def update_domain(self) -> requests.Response:
        """Update domain"""

    def get_environment_names(self) -> requests.Response:
        """Get environment names"""

    def get_environments(self) -> requests.Response:
        """Get environments"""

    def import_environment(self) -> requests.Response:
        """Import environment"""

    def save_integration_instance_settings(self) -> requests.Response:
        """Save integration instance settings"""

    def import_simulated_case(self) -> requests.Response:
        """Import simulated case"""

    def add_case_tag(self) -> requests.Response:
        """Add case tag"""

    def add_case_stage(self) -> requests.Response:
        """Add case stage"""

    def get_case_alert(self) -> requests.Response:
        """Get case alert"""

    def add_close_reason(self) -> requests.Response:
        """Add close reason"""

    def get_networks(self) -> requests.Response:
        """Get networks"""

    def update_network(self) -> requests.Response:
        """Update network"""

    def get_custom_lists(self) -> requests.Response:
        """Get custom lists"""

    def update_custom_list(self) -> requests.Response:
        """Update custom list"""

    def update_blocklist(self) -> requests.Response:
        """Update blocklist"""

    def update_sla_record(self) -> requests.Response:
        """Update sla record"""

    def save_playbook(self) -> requests.Response:
        """Save playbook"""

    def get_playbooks_workflow_menu_cards(self) -> requests.Response:
        """Get playbooks workflow menu cards"""

    def get_playbooks_workflow_menu_cards_with_env(self) -> requests.Response:
        """Get playbooks workflow menu cards with environment filter."""

    def get_playbook_workflow_menu_cards_by_identifier(self) -> requests.Response:
        """Get playbook workflow menu cards by identifier."""

    def get_playbook_workflow_menu_cards_by_identifier_with_env(
        self,
    ) -> requests.Response:
        """Get playbook workflow menu cards by identifier with environment filter."""

    def get_installed_connectors(self) -> requests.Response:
        """Get installed connectors."""

    def get_visual_families(self) -> requests.Response:
        """Get custom visual families."""

    def get_visual_family_by_id(self) -> requests.Response:
        """Get custom visual family by ID."""

    def get_ontology_records(self) -> requests.Response:
        """Get ontology records"""

    def get_case_tags(self) -> requests.Response:
        """Get case tags"""

    def get_case_stages(self) -> requests.Response:
        """Get case stages"""

    def get_case_close_reasons(self) -> requests.Response:
        """Get case close reasons"""

    def get_block_lists_details(self) -> requests.Response:
        """Get block lists details"""

    def get_sla_records(self) -> requests.Response:
        """Get sla records"""

    def add_tags_to_case_in_bulk(self) -> requests.Response:
        """Add tags to case in bulk"""

    def get_all_model_block_records(self) -> requests.Response:
        """Get all model block records"""

    def get_company_logo(self) -> requests.Response:
        """Get company logo"""

    def get_case_title_settings(self) -> requests.Response:
        """Get case title settings"""

    def save_case_title_settings(self) -> requests.Response:
        """Save case title settings"""

    def add_or_update_company_logo(self) -> requests.Response:
        """Add or update company logo"""

    def attache_workflow_to_case(self) -> requests.Response:
        """AttacheWorkflowToCase"""

    def import_custom_case(self) -> requests.Response:
        """Import custom case"""

    def get_environment_action_definition(self) -> requests.Response:
        """Get environment action definition"""

    def export_simulated_case(self) -> requests.Response:
        """Export simulated cases"""

    def get_case_insights_comment_evidence(self) -> requests.Response:
        """Get case insights using 1P API."""

    def get_bearer_token(self) -> requests.Response:
        """Get bearer token."""

    def update_api_record(self) -> requests.Response:
        """Update api record."""

    def get_store_data(self) -> requests.Response:
        """Get store data."""

    def import_package(self) -> requests.Response:
        """Import package."""

    def update_ide_item(self) -> requests.Response:
        """Update ide item."""

    def get_ide_cards(self) -> requests.Response:
        """Get ide cards."""

    def get_ide_item(self) -> requests.Response:
        """Get ide item."""

    def add_custom_family(self) -> requests.Response:
        """Add custom family."""

    def get_mapping_rules(self) -> requests.Response:
        """Get mapping rules."""

    def add_mapping_rules(self) -> requests.Response:
        """Add mapping rules."""

    def set_mappings_visual_family(self) -> requests.Response:
        """Set mappings visual family."""

    def export_playbooks(self) -> requests.Response:
        """Export playbooks."""

    def import_playbooks(self) -> requests.Response:
        """Import playbooks."""

    def create_playbook_category(self) -> requests.Response:
        """Create playbook category."""

    def get_playbook_categories(self) -> requests.Response:
        """Get playbook categories."""

    def update_connector(self) -> requests.Response:
        """Update connector."""

    def add_job(self) -> requests.Response:
        """Add job."""

    def add_email_template(self) -> requests.Response:
        """Add email template."""

    def get_denylists(self) -> requests.Response:
        """Get denylists."""

    def get_simulated_cases(self) -> requests.Response:
        """Get simulated cases."""


def get_soar_client(chronicle_soar: ChronicleSOAR) -> SoarApiClient:
    """Get the appropriate SOAR API client based on platform support.

    Args:
        chronicle_soar: The ChronicleSOAR SDK object.

    Returns:
        An instance of a SOAR API client (either OnePlatformSoarApi or LegacySoarApi).

    """
    if platform_supports_1p_api():
        return OnePlatformSoarApi(chronicle_soar)

    return LegacySoarApi(chronicle_soar)
