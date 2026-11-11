"""Manager for Jira API using Jira's python package"""
from __future__ import annotations

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence

from jira import Issue, JIRAError
import requests

from soar_sdk.SiemplifyLogger import SiemplifyLogger

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.base.utils import NewLineLogger
from TIPCommon.types import SingleJson
from scc_enterprise.core import JiraDatamodels
from scc_enterprise.core import JiraParser as parser
from scc_enterprise.core.JiraApiClient import JiraApiClient
from scc_enterprise.core.JiraConstants import DATETIME_FORMAT, MAX_RESULTS, UNAUTHORIZED
from scc_enterprise.core.JiraExceptions import JiraManagerError


class JiraManager:
    """Manage Jira API using Jira's python package"""

    def __init__(
        self,
        server_addr: str,
        username: str,
        api_token: str,
        verify_ssl: bool = False,
        logger: SiemplifyLogger | NewLineLogger | None = None,
    ) -> None:
        try:
            # Connect to JIRA instance with given credentials
            self.jira = JiraApiClient(
                server=server_addr,
                basic_auth=(username, api_token),
                options={"verify": verify_ssl},
                max_retries=0,
            )
            self.jira.myself()
            self.is_cloud = self.jira.deploymentType in ("Cloud",)


        except JIRAError as error:
            if error.status_code == UNAUTHORIZED:
                # Bad credentials
                raise JiraManagerError(
                    f"Unable to authenticate with {server_addr}, "
                    f"check given credentials."
                ) from error

            # Unknown JIRAError
            raise JiraManagerError(
                f"Unable to connect to {server_addr}: {error} {error.text}"
            ) from error

        except Exception as error:
            raise JiraManagerError(
                f"Unable to connect to {server_addr}: {error}"
            ) from error

        self.parser = parser
        self.logger = logger
        self.__create_issue = JiraDatamodels.CreateIssue

    @staticmethod
    def fix_format(filter_values: str | Iterable[str]) -> str:
        """Fix JQL query parameters.

        Args:
            filter_values: Filter values to create Jira query from

        Returns:
            String of formatted JQL query
        """
        try:
            # Fix formats - instead of ['name', 'name'] should be "'name', 'name'"
            filter_values = ", ".join(f"'{filter_val}'" for filter_val in filter_values)
        except TypeError:
            # Fix formats - instead of 'name,name' should be "'name', 'name'"
            filter_values = ", ".join(
                f"'{filter_val}'" for filter_val in filter_values.split(",")
            )
        return filter_values

    def get_issue_status_id(
        self, status_name: str, issue: str | int | Issue
    ) -> str | None:
        """Get the status ID of an Issue

        Args:
            status_name: The name of the status
            issue: ID or key of the issue to get the transitions from

        Returns:
            str | None: The status ID if it was found else None.
        """
        statuses = self.jira.transitions(issue)
        for status in statuses:
            if status_name == status.get("name"):
                return status["id"]

        return None

    def search_issues_by_keys(
        self,
        project_key_list: list[str],
        issue_type_list: list[str],
        fields: list[str],
        key_list: Sequence[str],
    ) -> list[Issue]:
        """Search issues by keys.

        Args:
            project_key_list (list[str]): Project key in which the issue is created
            issue_type_list (list[str]): Issue type name list.
                F.ex: Epic, Task, Bug or custom
            fields (list[str]): Fields to return in issue body
            key_list (Sequence[str]): Issue's key list.

        Returns:
            list[Issue]: List of Issue datamodels
        """
        try:
            issues: list[Issue] = []
            query: str = (
                f"project in ({self.fix_format(project_key_list)}) AND "
                f"issueType in ({self.fix_format(issue_type_list)})"
            )

            for index in range(0, len(key_list), MAX_RESULTS):
                keys_to_search: Sequence[str] = key_list[index : index + MAX_RESULTS]
                _query: str = f"{query} AND key in ({self.fix_format(keys_to_search)})"
                fetched_issues: list[Issue] = []

                if getattr(self, "is_cloud", False):
                    fetched_issues = self._fetch_via_cloud(query=_query, fields=fields)
                else:
                    start_offset: int = 0
                    while len(fetched_issues) < len(keys_to_search):
                        if self.logger:
                            self.logger.info(
                                f"Fetching more issues. Start offset {start_offset}. "
                                f"Fetched total of {len(issues)}"
                            )

                        _fetched: list[Issue] = self.parser.build_issue_obj_list(
                            issue.raw
                            for issue in self.jira.search_issues(
                                _query,
                                startAt=start_offset,
                                maxResults=MAX_RESULTS,
                                fields=fields,
                            )
                        )
                        if not _fetched:
                            break

                        fetched_issues.extend(_fetched)
                        start_offset += len(_fetched)

                issues.extend(fetched_issues)

            return issues

        except (JIRAError, requests.HTTPError) as error:
            status_code = getattr(
                error,
                "status_code",
                getattr(getattr(error, "response", None), "status_code", None)
            )
            if status_code == UNAUTHORIZED:
                # Unauthorized request to create an issue
                raise JiraManagerError(
                    "Credentials are invalid or no permission to search for issues."
                ) from error

            # Unknown error
            error_text = getattr(error, "text", str(error))
            raise JiraManagerError(error_text) from error

    def search_issues(
        self,
        project_key_list: list[str],
        issue_type_list: list[str],
        fields: list[str],
        updated_from: int | None = None,
    ) -> list[JiraDatamodels.Issue]:
        """Search issues by filters.

        Args:
            project_key_list: Project key in which the issue is created
            issue_type_list: Issue type name list.
                F.ex: Epic, Task, Bug or custom
            fields: Fields to return in issue body
            updated_from: Issue's updated from

        Returns:
             List of Issue datamodels
        """
        query = (
            f"project in ({self.fix_format(project_key_list)}) AND "
            f"issueType in ({self.fix_format(issue_type_list)})"
        )

        if updated_from is not None:
            updated_after_datetime = datetime.fromtimestamp(
                updated_from // NUM_OF_MILLI_IN_SEC
            ).strftime(DATETIME_FORMAT)
            query += f" AND updated >= '{updated_after_datetime}'"

        return self._fetch_issues_by_chunks(query, fields)

    def _fetch_issues_by_chunks(
        self,
        query: str,
        fields: list[str],
    ) -> list[Issue]:
        """Fetch all issues by chunks of MAX_RESULTS.

        Args:
            query (str): Query to filter issues with
            fields (list[str]): Fields to retrieve

        Raises:
            JiraManagerError: if request fails

        Returns:
            list[Issue]: List of Issue datamodels
        """
        issues: list[Issue] = []

        try:
            if getattr(self, "is_cloud", False):
                return list(self._fetch_via_cloud(query=query, fields=fields))

            start_offset: int = 0
            while True:
                if self.logger:
                    self.logger.info(
                        f"Fetching more issues. Start offset {start_offset}. "
                        f"Fetched total of {len(issues)}"
                    )

                _fetched: list[Issue] = self.parser.build_issue_obj_list(
                    issue.raw
                    for issue in self.jira.search_issues(
                        query,
                        startAt=start_offset,
                        maxResults=MAX_RESULTS,
                        fields=fields,
                    )
                )
                if not _fetched:
                    break

                issues.extend(_fetched)
                start_offset += len(_fetched)

                if len(_fetched) < MAX_RESULTS:
                    break

            return issues

        except (JIRAError, requests.HTTPError) as error:
            status_code = getattr(
                error,
                "status_code",
                getattr(getattr(error, "response", None), "status_code", None),
            )
            if status_code == UNAUTHORIZED:
                # Unauthorized request to create an issue
                raise JiraManagerError(
                    "Credentials are invalid or no permission to search for issues."
                ) from error

            # Unknown error
            error_text = getattr(error, "text", str(error))
            raise JiraManagerError(error_text) from error

    def _fetch_via_cloud(
        self,
        query: str,
        fields: list[str] | None,
    ) -> Iterable[Issue]:
        next_page_token: str | None = None
        fields_str: str | None = ",".join(fields) if fields else None
        has_next_page = True

        while has_next_page:
            raw_batch: SingleJson = self.jira.enhanced_search_issues(
                jql_str=query,
                max_results=MAX_RESULTS,
                next_page_token=next_page_token,
                fields=fields_str,
            )

            if raw_issues := raw_batch.get("issues"):
                yield from self.parser.build_issue_obj_list(raw_issues)

            next_page_token = raw_batch.get("nextPageToken")
            has_next_page = bool(next_page_token)

    def update_issue(
        self,
        issue_key: str,
        status: str | None = None,
        fields: SingleJson | None = None,
    ) -> None:
        """Update an issue.

        Args:
            issue_key: issue key
            status: issue status
            fields: a dict containing field names and the values to use.
        """
        try:
            issue = self.jira.issue(issue_key)
            if status is not None:
                status_id = self.get_issue_status_id(status, issue)
                if not status_id:
                    raise JiraManagerError("Bad status, issue status was not updated.")

                self.jira.transition_issue(issue, status_id, fields=fields)

            else:
                create_issue = self.build_issue_from_api_response(
                    issue.fields.project.id, issue.fields.issuetype.id, issue.raw
                )
                create_issue.update_issue(fields_dict=fields)
                issue.update(fields=create_issue.create_json(self.logger))

        except JIRAError as error:
            if error.status_code == UNAUTHORIZED:
                # Unauthorized request to create an issue
                raise JiraManagerError(
                    "Credentials are invalid or no permission to update an issue."
                ) from error

            # Unknown error
            raise JiraManagerError(error.text) from error

    def add_comment(self, issue_key: str, comment: str) -> str:
        """Add a new comment to a given issue.

        Args:
            issue_key: issue key
            comment: comment content

        Returns:
            The new comment's ID
        """
        try:
            new_comment = self.jira.add_comment(issue_key, comment)
            return new_comment.id

        except JIRAError as error:
            if error.status_code == UNAUTHORIZED:
                # Unauthorized request to create an issue
                raise JiraManagerError(
                    "Credentials are invalid or no permission to add a comment."
                ) from error

            # Unknown error
            raise JiraManagerError(error.text) from error

    def get_issue_comments_since_time(
        self, issue_key: str, last_modification_unix_time_ms: int
    ) -> list[JiraDatamodels.Issue.Comment]:
        """Get issue comments that were updated after certain modification time.

        Args:
            issue_key: The issue key to get comments from
            last_modification_unix_time_ms:
                Last modification unix time in milliseconds

        Returns:
            List of issue comments datamodels of comments that were updated
            after last_modification_unix_time_ms parameter
        """
        issue = self.parser.build_issue_obj(
            self.jira.issue(issue_key, fields="comment").raw
        )
        return [
            comment
            for comment in issue.comments
            if comment.updated_ms >= last_modification_unix_time_ms
        ]

    def get_project_by_key(self, project_key: str) -> JiraDatamodels.Project:
        """Get project info by its key.

        Args:
            project_key: Projects key to search by
        Returns:
            Project
        """
        try:
            project = self.jira.project(project_key)
            return self.parser.build_project_obj(project.raw)

        except JIRAError as error:
            if error.status_code == UNAUTHORIZED:
                # Unauthorized request to create an issue
                raise JiraManagerError(
                    "Credentials are invalid or no permission to search for issues."
                ) from error

            if "No project could be found with key" in error.text:
                raise KeyError(error.text) from error

            # Unknown error
            raise JiraManagerError(error.text) from error

    def create_project(
        self,
        workflow_: JiraDatamodels.BulkCreateWorkflows,
        project: JiraDatamodels.CreateProject,
    ) -> JiraDatamodels.Project:
        """Creates a new company managed project in JIRA with associated
        resources.

        Args:
            workflow_: Workflow to be used in project creation
            project: Create Project data model

        Returns:
            Project data model
        """
        _workflow_scheme_name = f"{project.name} Workflow Scheme"
        workflow_scheme = next(
            filter(
                lambda ws: ws["name"] == _workflow_scheme_name,
                self.jira.workflowscheme(),
            ),
            None,
        )

        if workflow_scheme is None:
            self.logger.info("Workflow doesn't exist, creating ...")

            workflow = self.parser.build_workflow_obj(
                self.jira.bulk_create_workflows(**workflow_.to_json())["workflows"][0]
            )
            workflow_scheme = self.jira.create_workflow_scheme(
                name=f"{project.name} Workflow Scheme", default_workflow=workflow.name
            )

        _project = self.jira.create_project_extended(
            assignee_type=project.assignee_type,
            key=project.key,
            name=project.name,
            lead_account_id=project.lead_account_id,
            description=project.description,
            project_type_key=project.project_type_key,
            workflow_scheme=workflow_scheme["id"],
        )

        return self.get_project_by_key(_project["key"])

    def create_and_assign_issue_type(
        self, project: JiraDatamodels.Project, issue_type_: JiraDatamodels.IssueType
    ) -> JiraDatamodels.IssueType:
        """Create an issue type and assign it to the project.

        Args:
            project: Project data model
            issue_type_: Issue type data model

        Returns:
            Created issue type
        """
        try:
            issue_type = self.parser.build_issue_type_obj(
                self.jira.issue_type_by_name(issue_type_.name).raw
            )
        except KeyError:
            issue_type = self.parser.build_issue_type_obj(
                self.jira.create_issue_type(
                    name=issue_type_.name,
                    description=issue_type_.description,
                    hierarchy_level=issue_type_.hierarchy_level,
                )
            )

        issue_type_scheme, created = self.get_or_create_issue_type_scheme(
            project=project, issue_type=issue_type
        )

        # No point in trying to add issue type to scheme if it was just created
        # or if issue type already there
        if (
            created
            or issue_type.id in issue_type_scheme.issue_type_ids
            or issue_type.id == issue_type_scheme.default_issue_type
        ):
            self.logger.info(
                f"Issue type {issue_type.id} already exists in the"
                f" issue type scheme {issue_type_scheme.id}."
            )
            return issue_type

        try:
            self.jira.add_issue_types_to_issue_type_scheme(
                issue_type_scheme_id=issue_type_scheme.id, issue_type_id=issue_type.id
            )
        except JIRAError as e:
            already_added_error = e.status_code == 400 and (
                "are already present in the issue type scheme"
                in e.response.json().get("errorMessages", [""])[0]
            )
            if not already_added_error:
                raise

            self.logger.info(
                f"Issue type {issue_type.id} already exists in the"
                f" issue type scheme {issue_type_scheme.id}."
            )

        return issue_type

    def get_or_create_issue_type_scheme(
        self, project: JiraDatamodels.Project, issue_type: JiraDatamodels.IssueType
    ) -> tuple[JiraDatamodels.IssueTypeScheme, bool]:
        """Get or create an issue type scheme for project.

        Args:
            project: Project data model
            issue_type: Issue type to be used if scheme needs to be created

        Returns:
            Parsed Issue type scheme data model and True if created
        """
        created = False

        _issue_type_scheme_name = f"{project.name} - Issue type Scheme"
        _issue_type_scheme = next(
            filter(
                lambda its: its["name"] == _issue_type_scheme_name,
                self.jira.issue_type_schemes_search(query=_issue_type_scheme_name),
            ),
            None,
        )

        if _issue_type_scheme is None:
            self.logger.info("Issue type scheme was not found, creating...")
            _issue_type_scheme = self.jira.create_issue_type_scheme(
                name=_issue_type_scheme_name,
                default_issue_type_id=issue_type.id,
                issue_type_ids=[issue_type.id],
            )

            self.jira.assign_issue_type_scheme_to_project(
                issue_type_scheme_id=_issue_type_scheme["issueTypeSchemeId"],
                project_id=project.id,
            )
            created = True

        return (self.parser.build_issue_type_scheme_obj(_issue_type_scheme), created)

    def get_custom_field_data(
        self, custom_field: JiraDatamodels.CustomField
    ) -> JiraDatamodels.CustomField:
        """Get a custom field data from Jira

        Args:
            custom_field: Custom field data model

        Returns:
            JiraDatamodels.CustomField: A custom filed objects populated with
                data form Jira
        """
        try:
            custom_field_data = self.jira.get_field_by_name(custom_field.name)
        except KeyError:
            custom_field_data = self.jira.create_custom_field(
                name=custom_field.name,
                description=custom_field.description,
                _type=custom_field.type,
            )

        return self.parser.build_custom_field_obj(custom_field_data)

    def create_or_update_custom_field(
        self,
        custom_field_: JiraDatamodels.CustomField,
        associated_project: str,
        associated_issue_type: str,
    ) -> JiraDatamodels.CustomField:
        """Create or update custom field in Jira.

        Args:
            custom_field_: Custom field data model
            associated_project: Associated project ID
            associated_issue_type: Associated issue type ID

        Returns:
            Created / Updated Custom field
        """
        custom_field = self.get_custom_field_data(custom_field_)
        _custom_field_context = self.jira.custom_field_context(custom_field.id)
        if _custom_field_context is None:
            self.logger.info("Custom field context not found, populating ...")
            _custom_field_context = self.jira.create_custom_field_context(
                custom_field_id=custom_field.id,
                name=f"{custom_field.name} context",
                issue_type_ids=[associated_issue_type],
                project_ids=[associated_project],
            )

        custom_field_context = self.parser.build_custom_field_context_obj(
            _custom_field_context
        )
        try:
            self.jira.assign_custom_field_context_to_project(
                custom_field_id=custom_field.id,
                custom_field_context_id=custom_field_context.id,
                associated_project=associated_project,
            )
        except JIRAError as e:
            if "These projects are already associated" not in e.text:
                raise

        try:
            self.jira.add_issue_types_to_context(
                custom_field_id=custom_field.id,
                custom_field_context_id=custom_field_context.id,
                associated_issue_type=associated_issue_type,
            )
        except JIRAError as e:
            if "These issue types are already associated" not in e.text:
                raise

        if custom_field_.options:
            self.sync_custom_field_options(
                custom_field_id=custom_field.id,
                custom_field_context_id=custom_field_context.id,
                options=custom_field_.options,
            )

        return custom_field

    def sync_custom_field_options(
        self,
        custom_field_id: str,
        custom_field_context_id: str,
        options: list[JiraDatamodels.CustomFieldOption],
    ) -> None:
        """Sync custom field options.

        Args:
            custom_field_id (str): Custom field ID
            custom_field_context_id: Custom field context ID
            options: Custom field options
        """
        existing_options_values = {
            option["value"]
            for option in self.jira.custom_field_context_options(
                custom_field_id=custom_field_id,
                custom_field_context_id=custom_field_context_id,
            )
        }

        new_options = [
            option.to_json()
            for option in options
            if option.value not in existing_options_values
        ]
        if not new_options:
            self.logger.info(
                f"There are no new options to be added to the custom field "
                f"{custom_field_id}"
            )
            return

        self.jira.add_custom_field_context_options(
            custom_field_id=custom_field_id,
            custom_field_context_id=custom_field_context_id,
            options=new_options,
        )

    def create_or_update_issue_type_screen(
        self,
        screen_name: str,
        screen_scheme_name: str,
        screen_fields_mapping: dict[str, Iterable[str]],
        project: JiraDatamodels.Project,
        issue_type_id: str,
    ) -> None:
        """Create or update issue type screen for given issue type and project

        Args:
            screen_name: Screen name
            screen_scheme_name: Screen scheme name
            screen_fields_mapping: Screen tabs to Fields mapping
            project: Project data model
            issue_type_id: Issue type ID
        """

        # Fetch or create screen specifically for our issue type
        screen_id = next(
            filter(lambda sc: sc["name"] == screen_name, self.jira.screens()), {}
        ).get("id")
        if screen_id is None:
            screen_id = self.jira.create_screen(screen_name)["id"]

        self.sync_screen_fields(
            screen_id=screen_id, screen_fields_mapping=screen_fields_mapping
        )

        # Fetch screen scheme or create if it doesn't exist
        screen_scheme_id = next(
            filter(
                lambda ss: ss["name"] == screen_scheme_name,
                self.jira.screen_schemes(query=screen_scheme_name),
            ),
            {},
        ).get("id")
        if screen_scheme_id is None:
            screen_scheme_id = self.jira.create_screen_scheme(
                name=screen_scheme_name, screens={"default": screen_id}
            )["id"]

        self.map_issue_type_to_screen_scheme(
            screen_scheme_id=str(screen_scheme_id),
            project=project,
            issue_type_id=issue_type_id,
        )

    def sync_screen_fields(
        self, screen_id: str, screen_fields_mapping: dict[str, Iterable[str]]
    ) -> None:
        """Sync screen fields for given screen (using fields tab).

        Args:
            screen_id: Screen's ID
            screen_fields_mapping: Screen tabs to Fields mapping
        """
        screen_tabs = sorted(self.jira.screens_tabs(screen_id), key=lambda st: st["id"])

        for screen_tab_name, field_names in screen_fields_mapping.items():
            # Fetch screen tabs (by default there should be only Fields tab)
            filtered_screen_tabs = (
                sc
                for sc in screen_tabs
                if sc["name"] == screen_tab_name or screen_tab_name is None
            )
            screen_tab_id = next(filtered_screen_tabs, {}).get("id")
            if screen_tab_id is None:
                screen_tab_id = self.jira.create_screen_tab(screen_id, screen_tab_name)[
                    "id"
                ]

            # Fetch existing in tab fields and then add missing ones
            screen_tab_fields_set = set(
                _field["name"]
                for _field in self.jira.screen_tab_fields(
                    screen_id=screen_id, screen_tab_id=screen_tab_id
                )
            )
            for field_name in field_names:
                if field_name in screen_tab_fields_set:
                    self.logger.info(
                        f"Field {field_name} was already added to tab screen,"
                        f"skipping..."
                    )
                    continue

                field_id = self.jira.get_field_by_name(field_name)["id"]
                self.jira.add_field_to_screen_tab(
                    screen_id=screen_id, screen_tab_id=screen_tab_id, field_id=field_id
                )

    def get_or_create_issue_type_screen_scheme(
        self, screen_scheme_id: str, issue_type_id: str, project: JiraDatamodels.Project
    ) -> tuple[str, bool]:
        """Get or create issue type screen scheme.

        Args:
            screen_scheme_id: Screen scheme id to be used for mapping
            issue_type_id: Issue type ID
            project: Project that needs to be assigned

        Returns:
            Screen Scheme ID and True if it was created
        """
        created = False
        _issue_type_screen_scheme_name = f"{project.name} - Issue type Screen Scheme"

        _issue_type_screen_scheme = next(
            filter(
                lambda itss: itss["name"] == _issue_type_screen_scheme_name,
                self.jira.issue_type_screen_scheme_search(
                    query=_issue_type_screen_scheme_name
                ),
            ),
            None,
        )

        if _issue_type_screen_scheme is None:
            self.logger.info("Issue type screen scheme was not found, creating...")

            _issue_type_screen_scheme = self.jira.create_issue_type_screen_scheme(
                name=_issue_type_screen_scheme_name,
                issue_type_mappings=[
                    {"issueTypeId": "default", "screenSchemeId": screen_scheme_id},
                    {"issueTypeId": issue_type_id, "screenSchemeId": screen_scheme_id},
                ],
            )

            self.jira.assign_issue_type_screen_scheme_to_project(
                project_id=project.id,
                issue_type_screen_scheme_id=_issue_type_screen_scheme["id"],
            )

            created = True

        return (str(_issue_type_screen_scheme["id"]), created)

    def map_issue_type_to_screen_scheme(
        self, screen_scheme_id: str, project: JiraDatamodels.Project, issue_type_id: str
    ) -> None:
        """Map issue type to a screen for given project ID

        Args:
            screen_scheme_id: Screen Scheme ID
            project: Project ID
            issue_type_id: Issue type ID
        """
        # Fetch already defined for project Issue Type Screen Scheme

        issue_type_screen_scheme_id, created = (
            self.get_or_create_issue_type_screen_scheme(
                screen_scheme_id=screen_scheme_id,
                issue_type_id=issue_type_id,
                project=project,
            )
        )

        # No reason to check mapping if issue type screen scheme was just
        # created.
        if created:
            return

        # Update mapping to have issue_type mapped to its screen scheme
        issue_type_screen_scheme_mapping = next(
            filter(
                lambda _map: (
                    _map["issueTypeId"] == issue_type_id
                    and _map["screenSchemeId"] == screen_scheme_id
                ),
                self.jira.issue_type_screen_scheme_mapping(issue_type_screen_scheme_id),
            ),
            None,
        )
        if issue_type_screen_scheme_mapping is None:
            self.jira.append_mapping_to_issue_type_screen_scheme(
                issue_type_screen_scheme_id=issue_type_screen_scheme_id,
                issue_type_id=issue_type_id,
                screen_scheme_id=screen_scheme_id,
            )

    def get_create_meta(
        self, project_id: str, issue_type_id: str
    ) -> list[JiraDatamodels.CreateFieldMetadata]:
        """Retrieve the creation metadata for the given issue type and project.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID

        Returns:
            The creation metadata objects
        """
        # We have a createmeta method in jira sdk, but used endpoint is
        # deprecated and probably will be removed in near future.
        # So we'll use a new one instead.
        return self.parser.build_create_field_metadatas(
            self.jira.create_field_metadata_for_project_and_issue_type(
                project_id=project_id, issue_type_id=issue_type_id
            )
        )

    def configure_create_issue(self, project_id: str, issue_type_id: str) -> None:
        """Configure the CreateIssue data model if not configured already.

        CreateIssue needs to be populated with fresh custom fields metadata
        before we can validate and create an issue.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID
        """
        if self.__create_issue.is_configured():
            return

        self.logger.info("Create issue metadata was not fetched yet, fetching ...")
        self.__create_issue.set_fields_metadata(
            self.get_create_meta(project_id, issue_type_id)
        )

    def create_issue(
        self, project_id: str, issue_type_id: str, issue_fields: SingleJson
    ) -> JiraDatamodels.CreateIssue:
        """Create an issue with the fields specified in kwargs.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID
            issue_fields: Issue fields dict - field_name: field_value

        Raises:
            ValueError: If the issue fields are invalid

        Returns:
            The created issue data model
        """
        issue_fields.update({"Issue Type": issue_type_id, "Project": project_id})
        issue = self.build_issue_from_field_names(
            project_id=project_id,
            issue_type_id=issue_type_id,
            issue_fields=issue_fields,
        )

        return self.__create_issue.build_from_api_response(
            self.jira.create_issue(fields=issue.create_json(self.logger)).raw
        )

    def get_field_id_by_name(
        self, project_id: str, issue_type_id: str, field_name: str
    ) -> str:
        """Get an issue field ID by its name based on issue create meta.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID
            field_name: Issue fields name

        Returns:
            The field id
        """
        self.configure_create_issue(project_id, issue_type_id)
        return self.__create_issue.get_field_id_by_name(field_name)

    def build_issue_from_api_response(
        self, project_id: str, issue_type_id: str, issue_fields: SingleJson
    ) -> JiraDatamodels.CreateIssue:
        """Build CreateIssue data model based on field_id: field_value dict.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID
            issue_fields: Issue fields dict - field_id: field_value

        Returns:
            CreateIssue data model
        """
        self.configure_create_issue(project_id, issue_type_id)
        return self.__create_issue.build_from_api_response(issue_fields)

    def build_issue_from_field_names(
        self, project_id: str, issue_type_id: str, issue_fields: SingleJson
    ) -> JiraDatamodels.CreateIssue:
        """Build CreateIssue data model based on field_name: field_value dict.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID
            issue_fields: Issue fields dict - field_name: field_value

        Returns:
            CreateIssue data model
        """
        self.configure_create_issue(project_id, issue_type_id)
        return self.__create_issue.build_from_field_names(issue_fields)
