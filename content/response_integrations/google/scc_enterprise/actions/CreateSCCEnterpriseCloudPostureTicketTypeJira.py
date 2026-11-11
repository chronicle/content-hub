from __future__ import annotations

import datetime

from jira import JIRAError

from TIPCommon.extraction import extract_action_param
from TIPCommon.base.action import Action
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core import JiraConstants
from scc_enterprise.core import JiraCustomFields
from scc_enterprise.core import JiraDatamodels
from scc_enterprise.core.JiraManager import JiraManager


class CreateSCCEnterpriseCloudPostureTicketTypeJira(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Created/updated “{SCCEnterpriseConsts.INTEGRATION_NAME} Cloud Posture "
            "Tickets” issue type in Jira."
        )

    def _init_api_clients(self) -> JiraManager:
        return JiraManager(
            server_addr=self.params.api_root,
            username=self.params.username,
            api_token=self.params.api_token,
            verify_ssl=self.params.verify_ssl,
            logger=self.soar_action.LOGGER,
        )

    def _extract_action_parameters(self) -> None:
        # Manager set up params
        self.params.api_root = extract_action_param(
            self.soar_action, param_name="API Root", print_value=True
        )
        self.params.username = extract_action_param(
            self.soar_action, param_name="Username", print_value=True
        )
        self.params.api_token = extract_action_param(
            self.soar_action,
            param_name="API Token",
            remove_whitespaces=False,
            print_value=False,
        )
        self.params.verify_ssl = extract_action_param(
            self.soar_action, param_name="Verify SSL", input_type=bool
        )

    def _perform_action(self, _=None) -> None:

        try:
            project = self.api_client.get_project_by_key(JiraConstants.SCCE_PROJECT_KEY)
        except KeyError:
            self.logger.info("Project was not found, creating a new project")

            _project = JiraDatamodels.CreateProject(
                key=JiraConstants.SCCE_PROJECT_KEY,
                description=JiraConstants.SCCE_PROJECT_DESCRIPTION,
                name=JiraConstants.SCCE_PROJECT_NAME,
                lead_account_id=self.api_client.jira.current_user(),
            )
            _workflow = JiraDatamodels.BulkCreateWorkflows.from_status_mapping(
                name=JiraConstants.SCCE_WORKFLOW_NAME,
                status_mapping=JiraCustomFields.JIRA_STATUS_MAPPING,
            )

            project = self.api_client.create_project(
                workflow_=_workflow, project=_project
            )

        issue_type = next(
            filter(
                lambda it: it.name == JiraConstants.CUSTOM_ISSUE_TYPE_NAME,
                project.issue_types,
            ),
            None,
        )
        if issue_type is None:
            self.logger.info("Custom issue type was not created yet, creating ...")
            issue_type = self.api_client.create_and_assign_issue_type(
                project=project,
                issue_type_=JiraDatamodels.IssueType(
                    name=JiraConstants.CUSTOM_ISSUE_TYPE_NAME,
                    description=JiraConstants.CUSTOM_ISSUE_TYPE_DESCRIPTION,
                ),
            )

        self.create_or_update_custom_fields(
            project_id=project.id, issue_type_id=issue_type.id
        )

        self.logger.info(
            f"Successfully synced custom fields for project {project.name}"
            f" and issue type {issue_type.name}"
        )

        self.create_or_update_screens(project, issue_type.id)
        self.logger.info(
            f"Successfully synced custom screens for project {project.name}"
            f" and issue type {issue_type.name}"
        )

        dummy_due_date = (
            datetime.datetime.now() - datetime.timedelta(days=14)
        ).isoformat()
        test_ticket_data = {
            "Assignee": {"id": self.api_client.jira.current_user()},
            "Summary": "Posture Test Ticket",
            "Description": (
                f"This is a test {JiraConstants.CUSTOM_ISSUE_TYPE_NAME} "
                f"generated with {self.soar_action.script_name} action."
            ),
            "Severity": "Info",
            "Cloud Environment": "Other",
            "Due date": dummy_due_date,
        }

        try:
            _test_ticket = self.api_client.create_issue(
                project_id=project.id,
                issue_type_id=issue_type.id,
                issue_fields=test_ticket_data,
            )
            self.logger.info(
                f"Added a test entry {_test_ticket['Summary']} "
                f"to project {project.name}"
            )
            self.json_results = _test_ticket.display_json()

        except JIRAError as e:
            self.logger.error(
                f"Failed creating jira test ticket, error is {e}."
            )

    def create_or_update_custom_fields(
        self, project_id: str, issue_type_id: str
    ) -> dict[str, str]:
        """Create or update custom jira fields for given project and issue type.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID

        Returns:
            Custom fields mapping - name: custom field id
        """
        custom_fields = {}

        for field in JiraCustomFields.ISSUE_CUSTOM_FIELDS_JSON:
            _custom_field = JiraDatamodels.CustomField(**field)
            custom_field = self.api_client.create_or_update_custom_field(
                custom_field_=_custom_field,
                associated_project=project_id,
                associated_issue_type=issue_type_id,
            )
            custom_fields[custom_field.name] = custom_field.id

        return custom_fields

    def create_or_update_screens(
        self, project: JiraDatamodels.Project, issue_type_id: str
    ) -> None:
        """Create or update screens for given project and issue type.

        Args:
            project: Project data model
            issue_type_id: Issue type ID
        """
        self.api_client.create_or_update_issue_type_screen(
            screen_name=JiraConstants.CUSTOM_ISSUE_TYPE_SCREEN_NAME,
            screen_scheme_name=(JiraConstants.CUSTOM_ISSUE_TYPE_SCREEN_SCHEME_NAME),
            screen_fields_mapping=JiraCustomFields.FIELD_TABS_MAPPING,
            project=project,
            issue_type_id=issue_type_id,
        )


def main() -> None:
    CreateSCCEnterpriseCloudPostureTicketTypeJira(
        SCCEnterpriseConsts.JIRA_BOOTSTRAP
    ).run()


if __name__ == "__main__":
    main()
