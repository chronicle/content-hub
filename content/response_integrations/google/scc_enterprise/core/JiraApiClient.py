from __future__ import annotations

import requests

from jira import JIRA, JIRAError

from TIPCommon.types import SingleJson


class JiraApiClient(JIRA):
    """This class extends JIRA to add support for additional
    endpoints reusing same session.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session.headers.update({"Accept": "application/json"})

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise JIRAError(status_code=response.status_code, request=response)

    def create_issue_type(
        self, name: str, description: str | None = None, hierarchy_level: int = 0
    ) -> SingleJson:
        """Creates an issue type.

        Args:
            name: Issue type name [requited, unique]
            description: Issue type description
            hierarchy_level: enum 0 - base, -1 - subtask

        Returns:
            Issue type json
        """

        _uri = self._get_url("issuetype")
        json_payload = {
            "name": name,
            "description": description,
            "hierarchyLevel": hierarchy_level,
        }
        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)

        return response.json()

    def project_issue_type_schemes(self, project_id: str) -> list[SingleJson]:
        """Fetches a list of Issue type scheme jsons for a given project

        Args:
            project_id: Project ID

        Returns:
            List of Issue type scheme json
        """

        _uri = self._get_url("issuetypescheme/project")
        response = self._session.get(_uri, params={"projectId": project_id})
        self._raise_for_status(response)

        if "values" not in response.json():
            raise JIRAError(
                status_code=response.status_code, response=response, url=_uri
            )

        return response.json()["values"]

    def add_issue_types_to_issue_type_scheme(
        self, issue_type_scheme_id: str, issue_type_id: str
    ) -> None:
        """Adds issue types to a given issue type scheme.

        Args:
            issue_type_scheme_id: Issue type scheme ID
            issue_type_id: Issue type ID
        """
        _uri = self._get_url(f"issuetypescheme/{issue_type_scheme_id}/issuetype")
        json_payload = {"issueTypeIds": [issue_type_id]}
        response = self._session.put(_uri, json=json_payload)
        self._raise_for_status(response)

    def get_field_by_name(self, name: str) -> SingleJson:
        """Gets a field by its name.

        Args:
            name: fields name

        Returns:
            fields object

        Raises:
            KeyError if custom field does not exist
        """

        _uri = self._get_url("field/search")
        response = self._session.get(_uri, params={"query": name})
        self._raise_for_status(response)

        result = next(
            filter(lambda item: item["name"] == name, response.json()["values"]), None
        )

        if result is None:
            raise KeyError(f"Custom field with name {name} does not exist")
        return result

    def create_custom_field(
        self, name: str, description: str = None, _type: str = None
    ) -> SingleJson:
        """Create a custom field.

        Args:
            name: Custom fields name
            description: Custom fields description
            _type: Custom fields type

        Returns:
            Custom fields object

        Raises:
            KeyError if custom field does not exist
        """

        _uri = self._get_url("field")
        json_payload = {"name": name, "description": description, "type": _type}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)

        return response.json()

    def custom_field_context(self, custom_field_id: str) -> SingleJson | None:
        """Get custom fields context.

        Args:
            custom_field_id: Custom field ID

        Returns:
            Custom Field context object
        """
        _uri = self._get_url(f"field/{custom_field_id}/context")
        response = self._session.get(_uri)
        self._raise_for_status(response)

        return response.json()["values"][0] if response.json()["values"] else None

    def create_custom_field_context(
        self,
        custom_field_id: str,
        name: str,
        issue_type_ids: list[str],
        project_ids: list[str],
    ) -> SingleJson:
        """Create custom field context.

        Args:
            custom_field_id: Custom field ID
            name: Custom field context name
            issue_type_ids: List of issue types
            project_ids: List of project IDs

        Returns:
            Custom Field context JSON object
        """
        _uri = self._get_url(f"field/{custom_field_id}/context")
        json_payload = {
            "issueTypeIds": issue_type_ids,
            "name": name,
            "projectIds": project_ids,
        }

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)
        return response.json()

    def assign_custom_field_context_to_project(
        self,
        custom_field_id: str,
        custom_field_context_id: str,
        associated_project: str,
    ) -> None:
        """Assign custom field context to a project.

        Args:
            custom_field_id: Custom field ID
            custom_field_context_id: Custom field ID
            associated_project: Project ID
        """

        _uri = self._get_url(
            f"field/{custom_field_id}/context/{custom_field_context_id}/project"
        )
        json_payload = {"projectIds": [associated_project]}

        response = self._session.put(_uri, json=json_payload)
        self._raise_for_status(response)

    def add_issue_types_to_context(
        self,
        custom_field_id: str,
        custom_field_context_id: str,
        associated_issue_type: str,
    ) -> None:
        """Add issue type to custom field context.

        Args:
            custom_field_id: Custom field ID
            custom_field_context_id: Custom field ID
            associated_issue_type: Issue type ID
        """

        _uri = self._get_url(
            f"field/{custom_field_id}/context/{custom_field_context_id}/" f"issuetype"
        )
        json_payload = {"issueTypeIds": [associated_issue_type]}

        response = self._session.put(_uri, json=json_payload)
        self._raise_for_status(response)

    def custom_field_context_options(
        self, custom_field_id: str, custom_field_context_id: str
    ) -> list[SingleJson]:
        """Add issue type to custom field context.

        Args:
            custom_field_id: Custom field ID
            custom_field_context_id: Custom field ID

        Returns:
            List of field context options
        """

        _uri = self._get_url(
            f"field/{custom_field_id}/context/{custom_field_context_id}/" f"option"
        )
        response = self._session.get(_uri)
        self._raise_for_status(response)

        if "values" not in response.json():
            raise JIRAError(
                status_code=response.status_code, response=response, url=_uri
            )

        return response.json()["values"]

    def add_custom_field_context_options(
        self,
        custom_field_id: str,
        custom_field_context_id: str,
        options: list[SingleJson],
    ) -> None:
        """Add new options to custom field context

        Args:
            custom_field_id: Custom field ID
            custom_field_context_id: Custom field context ID
            options: List of options to add
        """

        _uri = self._get_url(
            f"field/{custom_field_id}/context/{custom_field_context_id}/" f"option"
        )
        json_payload = {"options": options}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)

    def create_screen(self, screen_name: str) -> SingleJson:
        """Create a new screen.

        Args:
            screen_name: Screen name

        Returns:
            A screen json object
        """
        _uri = self._get_url("screens")
        json_payload = {"name": screen_name}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)

        return response.json()

    def create_screen_tab(self, screen_id: str, tab_name: str) -> SingleJson:
        """Create a new screen tab.

        Args:
            screen_id: Screen that tab belongs to
            tab_name: Name for the new tab

        Returns:
            A screen tab json object
        """
        _uri = self._get_url(f"screens/{screen_id}/tabs")
        json_payload = {"name": tab_name}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)

        return response.json()

    def screens_tabs(self, screen_id: str) -> list[SingleJson]:
        """Get screen tabs for a specific screen.

        Args:
            screen_id: Screen ID

        Returns:
            A list of screen tab json objects
        """

        _uri = self._get_url(f"screens/{screen_id}/tabs")
        response = self._session.get(_uri)
        self._raise_for_status(response)
        return response.json()

    def screen_tab_fields(self, screen_id: str, screen_tab_id: str) -> list[SingleJson]:
        """Get screen tab fields for a specific screen and screen tab.

        Args:
            screen_id: Screen ID
            screen_tab_id: Screen tab ID

        Returns:
            A list of screen tab field json objects
        """
        _uri = self._get_url(f"screens/{screen_id}/tabs/{screen_tab_id}/fields")
        response = self._session.get(_uri)
        self._raise_for_status(response)
        return response.json()

    def add_field_to_screen_tab(
        self, screen_id: str, screen_tab_id: str, field_id: str
    ) -> None:
        """Add a field to a screen tab.

        Args:
            screen_id: Screen ID
            screen_tab_id: Screen tab ID
            field_id: Field ID
        """

        _uri = self._get_url(f"screens/{screen_id}/tabs/{screen_tab_id}/fields")
        json_payload = {"fieldId": field_id}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)

    def screen_schemes(self, query: str) -> list[SingleJson]:
        """Get screen schemes filtered by given query.

        Args:
            query: queryString to be used when searching for screen schemes

        Returns:
            List of screen scheme json objects
        """
        _uri = self._get_url("screenscheme")
        response = self._session.get(_uri, params={"queryString": query})
        self._raise_for_status(response)
        return response.json()["values"]

    def create_screen_scheme(self, name: str, screens: SingleJson) -> SingleJson:
        """Create screen scheme.

        Args:
            name: Screen Scheme name
            screens: Screens mapping ->
                {
                    "default": 10017, (Required)
                    "edit": 10019, (Optional)
                    "view": 10020, (Optional)
                    "create": 100017 (Optional)
                }
        Returns:
            Screen Scheme json object
        """
        _uri = self._get_url("screenscheme")
        json_payload = {"name": name, "screens": screens}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)
        return response.json()

    def issue_type_screen_scheme_search(self, query: str) -> list[SingleJson]:
        """Issue type screen schemes filtered by given queryString

        Args:
            query: queryString to be used for search

        Returns:
            List of issue type screen schemes
        """

        _uri = self._get_url("issuetypescreenscheme")
        response = self._session.get(_uri, params={"queryString": query})
        self._raise_for_status(response)
        return response.json()["values"]

    def create_issue_type_screen_scheme(
        self, name: str, issue_type_mappings: list[SingleJson]
    ) -> SingleJson:
        """Create issue type screen scheme with given mapping,

        Args:
            name: Issue type screen scheme name
            issue_type_mappings: List of mapping issue type <-> screen scheme

        Returns:
            Issue type screen scheme JSON object
        """
        _uri = self._get_url("issuetypescreenscheme")
        json_payload = {"issueTypeMappings": issue_type_mappings, "name": name}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)
        return response.json()

    def assign_issue_type_screen_scheme_to_project(
        self, issue_type_screen_scheme_id: str, project_id: str
    ) -> None:
        """Assigns an issue type screen scheme to project.

        Args:
            issue_type_screen_scheme_id: Issue type screen scheme id
            project_id: Project id
        """
        _uri = self._get_url("issuetypescreenscheme/project")
        json_payload = {
            "issueTypeScreenSchemeId": issue_type_screen_scheme_id,
            "projectId": project_id,
        }

        response = self._session.put(_uri, json=json_payload)
        self._raise_for_status(response)

    def issue_type_screen_scheme_mapping(
        self, issue_type_screen_scheme_id: str
    ) -> list[SingleJson]:
        """Issue type screen scheme mapping filtered by issue_type_screen_scheme_id.

        Args:
            issue_type_screen_scheme_id: Issue type screen scheme ID

        Returns:
            List of mapping json objects
        """
        _uri = self._get_url("issuetypescreenscheme/mapping")
        response = self._session.get(
            _uri, params={"issueTypeScreenSchemeId": issue_type_screen_scheme_id}
        )
        self._raise_for_status(response)
        return response.json()["values"]

    def append_mapping_to_issue_type_screen_scheme(
        self,
        issue_type_screen_scheme_id: str,
        issue_type_id: str,
        screen_scheme_id: str,
    ) -> None:
        """Append mapping of issue type to screen scheme ID.

        Args:
            issue_type_screen_scheme_id: Issue type screen scheme ID
            issue_type_id: Issue type ID
            screen_scheme_id: Screen scheme ID
        """
        _uri = self._get_url(
            f"issuetypescreenscheme/{issue_type_screen_scheme_id}/mapping"
        )
        json_payload = {
            "issueTypeMappings": [
                {"issueTypeId": issue_type_id, "screenSchemeId": screen_scheme_id}
            ]
        }

        response = self._session.put(_uri, json=json_payload)
        self._raise_for_status(response)

    def create_project_extended(
        self,
        assignee_type: str,
        key: str,
        description: str,
        name: str,
        lead_account_id: str,
        project_type_key: str,
        workflow_scheme: int,
    ) -> SingleJson:
        """Create a new project with given parameters.

        Args:
            assignee_type: Project assignee type (PROJECT_LEAD, UNASSIGNED)
            description: Project description
            key: UNIQUE project identifier
            name: Project display name
            lead_account_id: Lead account
            project_type_key: MUST be specified if projectTemplateKey is not provided
                (software, service_desk, business)
            workflow_scheme: Workflow scheme ID

        Returns:
            Project JSON object
        """
        _uri = self._get_url("project")
        json_payload = {
            "assigneeType": assignee_type,
            "description": description,
            "leadAccountId": lead_account_id,
            "key": key,
            "name": name,
            "projectTypeKey": project_type_key,
            "workflowScheme": workflow_scheme,
        }

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)
        return response.json()

    def statuses_search(self, query: str) -> list[SingleJson]:
        """Search status by provided query string.

        Args:
            query: Query string to use in search

        Returns:
            List of status dictionaries
        """
        _uri = self._get_url("statuses/search")

        response = self._session.get(_uri, params={"searchString": query})
        self._raise_for_status(response)
        return response.json()["values"]

    def bulk_create_workflows(
        self, scope: SingleJson, statuses: list[SingleJson], workflows: list[SingleJson]
    ) -> SingleJson:
        """Create a new workflow via bulk API.

        Args:
            scope: Workflow scope (GLOBAL or PROJECT).
            statuses: List of statuses associated with the workflows.
            workflows: List of workflows to be populated.

        Returns:
            Workflow JSON objects along with created statuses
        """

        for status_data in statuses:
            status_name_lower = status_data["name"].casefold()
            existing_statuses = self.statuses_search(query=status_name_lower)
            status_match = next(
                filter(
                    lambda existing_status: (
                        existing_status["name"].casefold() == status_name_lower
                        and existing_status["scope"]["type"] == scope["type"]
                    ),
                    existing_statuses,
                ),
                None,
            )
            status_data["id"] = status_match["id"] if status_match else None

        _uri = self._get_url("workflows/create")
        json_payload = {"scope": scope, "statuses": statuses, "workflows": workflows}

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)
        return response.json()

    def workflowscheme(self) -> list[SingleJson]:
        """Get the workflow schemes."""
        url = self._get_url("workflowscheme")

        response = self._session.get(url)
        self._raise_for_status(response)

        return response.json()["values"]

    def create_workflow_scheme(
        self,
        name: str,
        default_workflow: str,
        issue_type_mappings: SingleJson | None = None,
        description: str | None = None,
    ) -> SingleJson:
        """Create a new workflow scheme.

        Args:
            name: Workflow scheme name
            default_workflow: Default workflow to be used to all not defined types
            issue_type_mappings: Specific issue type <-> workflow mappings
            description: Description of the workflow scheme

        Returns:
            Workflow Scheme JSON object
        """
        _uri = self._get_url("workflowscheme")
        json_payload = {
            "name": name,
            "defaultWorkflow": default_workflow,
            "issueTypeMappings": issue_type_mappings,
            "description": description,
        }

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)
        return response.json()

    def issue_type_schemes_search(self, query: str) -> list[SingleJson]:
        """Search issue type schemes by queryString.

        Args:
            query: queryString to search issue type schemes
        """
        _uri = self._get_url("issuetypescheme")

        response = self._session.get(_uri, params={"queryString": query})
        self._raise_for_status(response)
        return response.json()["values"]

    def create_issue_type_scheme(
        self, name: str, default_issue_type_id: str, issue_type_ids: list[str]
    ) -> SingleJson:
        """Creates an issue type scheme.

        Args:
            name: name of the issue type scheme
            default_issue_type_id: Default issue type to use
            issue_type_ids: Issue types included in this scheme

        Returns:
            Issue type scheme JSON object
        """
        _uri = self._get_url("issuetypescheme")
        json_payload = {
            "defaultIssueTypeId": default_issue_type_id,
            "issueTypeIds": issue_type_ids,
            "name": name,
        }

        response = self._session.post(_uri, json=json_payload)
        self._raise_for_status(response)
        return response.json()

    def assign_issue_type_scheme_to_project(
        self, issue_type_scheme_id: str, project_id: str
    ) -> None:
        """Assigns an issue type scheme to project.

        Args:
            issue_type_scheme_id: Issue type scheme id
            project_id: Project id
        """
        _uri = self._get_url("issuetypescheme/project")
        json_payload = {
            "issueTypeSchemeId": issue_type_scheme_id,
            "projectId": project_id,
        }

        response = self._session.put(_uri, json=json_payload)
        self._raise_for_status(response)

    def create_field_metadata_for_project_and_issue_type(
        self, project_id: str, issue_type_id: str
    ) -> list[SingleJson]:
        """Get create field metadata for given project and issue type.

        Args:
            project_id: Project ID
            issue_type_id: Issue type ID
        """
        _uri = self._get_url(
            f"issue/createmeta/{project_id}/issuetypes/{issue_type_id}"
        )

        response = self._session.get(_uri)
        self._raise_for_status(response)
        return response.json()["fields"]

    def enhanced_search_issues(
        self,
        jql_str: str,
        max_results: int = 50,
        next_page_token: str | None = None,
        fields: str | None = None,
    ) -> SingleJson:
        """Performs an enhanced JQL search for issues using token-based pagination.

        This method uses the '/rest/api/3/search/jql' endpoint, which is suitable
        for searches that may return a large number of results and require
        stable pagination.

        Args:
            jql_str (str): The JQL query string.
            max_results (int): The maximum number of issues to return per page.
            next_page_token (str | None): Token for fetching the next page of results.
            fields (str | None): A comma-separated string of fields to return for
                each issue.

        Returns:
            SingleJson: The JSON response from the API containing the search results.
        """
        _uri: str = self._options["server"].rstrip("/") + "/rest/api/3/search/jql"
        params: dict[str, str | int] = {
            "jql": jql_str,
            "maxResults": max_results,
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token
        if fields:
            params["fields"] = fields

        response: requests.Response = self._session.get(_uri, params=params)
        self._raise_for_status(response)
        return response.json()
