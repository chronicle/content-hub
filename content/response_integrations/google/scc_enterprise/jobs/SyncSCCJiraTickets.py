"""BiDi Sync job SOAR <-> Jira"""
from __future__ import annotations

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon import extraction
from TIPCommon import validation
from TIPCommon import consts
from scc_enterprise.core import JiraConstants
from scc_enterprise.core import JiraDatamodels
from scc_enterprise.core import SCCEnterpriseDatamodels
from scc_enterprise.core import SCCEnterpriseUtils
from scc_enterprise.core.BaseSoarItsmJob import SyncSoarITSM
from scc_enterprise.core.JiraManager import JiraManager
from scc_enterprise.core.SCCEnterpriseConsts import NOT_AVAILABLE, RESOLVED_STATUS, SYNC_SCC_JIRA_TICKETS


@dataclasses.dataclass
class JiraAuthParams:
    api_root: str
    username: str
    api_token: str
    verify_ssl: bool

    @classmethod
    def build_from_job(cls, chronicle_soar: SiemplifyJob) -> JiraAuthParams:
        """Build integration auth params from SOAR job object."""
        return cls(
            api_root=extraction.extract_job_param(
                chronicle_soar, param_name="API Root", is_mandatory=True
            ),
            username=extraction.extract_job_param(
                chronicle_soar, param_name="Username", is_mandatory=True
            ),
            api_token=extraction.extract_job_param(
                chronicle_soar, param_name="API Token", is_mandatory=True
            ),
            verify_ssl=extraction.extract_job_param(
                chronicle_soar,
                param_name="Verify SSL",
                is_mandatory=True,
                input_type=bool,
            ),
        )


class SyncSCCJiraTicketsJob(SyncSoarITSM[JiraDatamodels.Issue, JiraManager]):
    """Implementation of SyncSoarITSM using ServiceNow"""

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_job)
        self.params.max_hours_backwards = validator.validate_non_negative(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )

    def _init_api_clients(self) -> JiraManager:
        """Initialize the Jira manager."""
        jira_auth_params = JiraAuthParams.build_from_job(self.soar_job)
        return JiraManager(
            server_addr=jira_auth_params.api_root,
            username=jira_auth_params.username,
            api_token=jira_auth_params.api_token,
            verify_ssl=jira_auth_params.verify_ssl,
            logger=self.soar_job.LOGGER,
        )

    def _get_environment_for_case_filter(self) -> str:
        return self.params.environment

    def _get_max_hours_backwards(self) -> int:
        return self.params.max_hours_backwards

    def _get_bulk_ticket_id_to_details_map(
        self,
        ticket_ids: Sequence[str] | None = None,
        last_run_timestamp: int | None = None,
    ) -> Mapping[str, JiraDatamodels.Issue]:
        source_link_field_id = self.api_client.get_field_id_by_name(
            project_id=JiraConstants.SCCE_PROJECT_KEY,
            issue_type_id=(
                self.api_client.jira.issue_type_by_name(
                    JiraConstants.CUSTOM_ISSUE_TYPE_NAME
                ).id
            ),
            field_name="Source Link",
        )
        read_mask = [
            "key",
            "assignee",
            "updated",
            "description",
            "status",
            "priority",
            "comment",
            source_link_field_id,
        ]

        if last_run_timestamp:
            issues = self.api_client.search_issues(
                project_key_list=[JiraConstants.SCCE_PROJECT_NAME],
                issue_type_list=[JiraConstants.CUSTOM_ISSUE_TYPE_NAME],
                updated_from=last_run_timestamp,
                fields=read_mask,
            )

        else:
            issues = self.api_client.search_issues_by_keys(
                project_key_list=[JiraConstants.SCCE_PROJECT_NAME],
                issue_type_list=[JiraConstants.CUSTOM_ISSUE_TYPE_NAME],
                key_list=ticket_ids,
                fields=read_mask,
            )

        issues_mapping = {}
        for issue in issues:
            issue.case_uri = issue.raw_fields.get(source_link_field_id) or ""
            issues_mapping[issue.key] = issue

        return {issue.key: issue for issue in issues}

    def _get_ticket_id_to_details_map(
        self, ticket_id: str
    ) -> Mapping[str, JiraDatamodels.Issue]:
        return self._get_bulk_ticket_id_to_details_map([ticket_id])

    def _get_bulk_ticket_id_to_comments_map(
        self, tickets: Iterable[JiraDatamodels.Issue]
    ) -> Mapping[str, list[str]]:
        return {
            issue.key: [comment.body for comment in issue.comments] for issue in tickets
        }

    def _get_ticket_id_to_comments_map(
        self, ticket: JiraDatamodels.Issue
    ) -> Mapping[str, list[str]]:
        return self._get_bulk_ticket_id_to_comments_map([ticket])

    def _add_comment_to_ticket(self, comment: str, ticket_id: str) -> None:
        self.api_client.add_comment(ticket_id, comment)

    def _close_ticket(self, ticket_id: str) -> None:
        self.api_client.update_issue(ticket_id, status=RESOLVED_STATUS)

    def _get_ticket_case_uri(self, ticket: JiraDatamodels.Issue) -> str:
        return ticket.case_uri

    def _get_ticket_status(self, ticket: JiraDatamodels.Issue) -> str:
        return ticket.status

    def _set_ticket_status(self, ticket: JiraDatamodels.Issue, new_status: str) -> None:
        ticket.status = new_status

    def _set_ticket_update_time(
        self, ticket: JiraDatamodels.Issue, update_time: datetime
    ) -> None:
        update_timestamp = update_time.timestamp()
        ticket.updated_ms = int(update_timestamp) * consts.NUM_OF_MILLI_IN_SEC

    def _update_ticket_description(self, ticket_id: str, description: str) -> None:
        self.api_client.update_issue(ticket_id, fields={"Description": description})

    def _update_ticket_severity(self, ticket_id: str, severity: str) -> None:
        self.api_client.update_issue(issue_key=ticket_id, fields={"Severity": severity})

    def _create_description_table(
        self, findings: list[SCCEnterpriseDatamodels.FindingContext]
    ) -> str:
        return SCCEnterpriseUtils.create_jwm_table(
            findings, self._soar_job.platform_url
        )

    def _update_description_table(self, table: str, description: str) -> str:
        return SCCEnterpriseUtils.update_jira_wiki_desc_table(table, description)

    def _parse_ticket_details_for_scc(
        self, ticket: JiraDatamodels.Issue, **additional_keys
    ) -> SCCEnterpriseDatamodels.ITSMTicketDetailsForSCC:
        assignee = ticket.raw_data["fields"].get("assignee", NOT_AVAILABLE)
        if not isinstance(assignee, str) and isinstance(assignee, dict):
            assignee = assignee.get("displayName", NOT_AVAILABLE)

        ticket_details = SCCEnterpriseDatamodels.ITSMTicketDetailsForSCC(
            id_=ticket.key,
            assignee=assignee or NOT_AVAILABLE,  # assignee can exist but be ""
            description=ticket.raw_data["fields"]["description"],
            uri=None,
            status=ticket.status,
            update_time=ticket.updated_ms // consts.NUM_OF_MILLI_IN_SEC,
            **additional_keys,
        )

        # Updating the attr if exists or creating it if not
        ticket_details.additional_keys["priority"] = ticket.priority

        return ticket_details


def main() -> None:
    sync_job = SyncSCCJiraTicketsJob(
        script_name=SYNC_SCC_JIRA_TICKETS,
        integration_name=JiraConstants.INTEGRATION_NAME,
    )
    sync_job.start()


if __name__ == "__main__":
    main()
