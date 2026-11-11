from __future__ import annotations

import uuid
from typing import Mapping, TypeVar

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from scc_enterprise.core import JiraCustomFields

from TIPCommon.types import JSON, SingleJson


_T = TypeVar("_T")


class BaseModel:
    """Base model for inheritance"""

    def __init__(self, raw_data: JSON) -> None:
        self.raw_data = raw_data

    def as_json(self) -> JSON:
        return self.raw_data


class BaseJiraModel(BaseModel):
    """
    Base jira model for all objects that use id, name fields.
    """

    def __init__(self, raw_data: JSON, id_: str, name: str) -> None:
        super().__init__(raw_data)
        self.id = id_
        self.name = name

    def to_json(self) -> dict[str, str]:
        return {"name": self.name}


class Issue(BaseModel):
    """Jira Issue data model"""

    class Attachment(BaseModel):

        def __init__(
            self,
            raw_data,
            filename: str | None = None,
            author_account_id: str | None = None,
            created: str | None = None,
            size: str | None = None,
            content_link: str | None = None,
        ) -> None:
            super(Issue.Attachment, self).__init__(raw_data)
            self.author_account_id = author_account_id
            self.filename = filename
            self.created = created
            self.size = size
            self.content_link = content_link

    class Comment(BaseModel):

        def __init__(
            self,
            raw_data,
            created: str | None = None,
            updated: str | None = None,
            body: str | None = None,
            id_: str | None = None,
        ) -> None:
            super().__init__(raw_data)
            self.raw_data = raw_data
            self.created = created
            self.updated = updated
            self.body = body
            self.id = id_

            try:
                self.updated_ms = convert_string_to_unix_time(self.updated)
            except Exception:
                self.updated_ms = 1

    def __init__(
        self,
        raw_data,
        id_: str | None = None,
        expand: str | None = None,
        raw_fields: SingleJson | None = None,
        key: str | None = None,
        project_id: str | None = None,
        project_key: str | None = None,
        project_name: str | None = None,
        project_type_key: str | None = None,
        priority: str | None = None,
        attachments: list[Attachment] | None = None,
        created: str | None = None,
        updated: str | None = None,
        comments: list[Comment] | None = None,
        status: str | None = None,
    ) -> None:
        super().__init__(raw_data)
        self.id = id_
        self.expand = expand
        self.raw_fields = raw_fields
        self.key = key

        self.project_id = project_id
        self.project_key = project_key
        self.project_name = project_name
        self.project_type_key = project_type_key

        self.priority = priority
        self.created = created
        self.updated = updated
        self.status = status

        self.attachments = attachments or []
        self.comments = comments or []

        try:
            self.created_ms = convert_string_to_unix_time(self.created)
        except Exception:
            self.created_ms = 1

        try:
            self.updated_ms = convert_string_to_unix_time(self.updated)
        except Exception:
            self.updated_ms = 1

        self.case_uri = ""


class Project(BaseJiraModel):

    def __init__(
        self,
        raw_data: dict,
        id_: str,
        key: str,
        name: str,
        style: str,
        issue_types: list[IssueType],
    ) -> None:
        super().__init__(raw_data, id_, name)
        self.key = key
        self.style = style
        self.issue_types = issue_types

    @property
    def is_classic(self) -> bool:
        return self.style == "classic"


class CreateProject:

    def __init__(
        self,
        key: str,
        description: str,
        name: str,
        lead_account_id: str,
        project_type_key: str = "software",
        assignee_type: str = "UNASSIGNED",
    ) -> None:
        self.key = key
        self.description = description
        self.name = name
        self.lead_account_id = lead_account_id
        self.project_type_key = project_type_key
        self.assignee_type = assignee_type


class WorkflowStatus(BaseJiraModel):

    def __init__(
        self,
        name: str,
        status_category: JiraCustomFields.JiraStatusCategory,
        status_reference: str,
        id_: str | None = None,
        raw_data: SingleJson | None = None,
    ) -> None:
        super().__init__(raw_data, id_, name)
        self.status_category = status_category
        self.status_reference = status_reference

    def to_json(self) -> SingleJson:
        return {
            "name": self.name,
            "statusCategory": self.status_category.value,
            "statusReference": self.status_reference,
        }

    def to_workflow_status(self) -> SingleJson:
        return {"properties": {}, "statusReference": self.status_reference}


class WorkFlowTransition(BaseJiraModel):

    def __init__(
        self,
        id_: str,
        name: str,
        to: WorkflowStatus,
        type_: str,
        links: list[SingleJson] | None = None,
        raw_data: SingleJson | None = None,
    ) -> None:
        super().__init__(raw_data, id_, name)
        self.to = to
        self.links = links
        self.type = type_

    def to_json(self) -> SingleJson:
        """
        Serialize data model into JSON object.

        Field info:
            id: Unique transition ID
            name: Transition display name
            to: Status reference of "to transition"
            type: Type of transition (INITIAL, GLOBAL, DIRECTED)

        Returns:
            Transition JSON object
        """
        return {
            "id": self.id,
            "name": self.name,
            "links": self.links or [],
            "toStatusReference": self.to.status_reference,
            "type": self.type,
        }


class Workflow(BaseJiraModel):

    def __init__(
        self,
        name: str,
        statuses: list[WorkflowStatus] | None = None,
        transitions: list[WorkFlowTransition] | None = None,
        raw_data: JSON | None = None,
        id_: str | None = None,
    ) -> None:
        super().__init__(raw_data, id_, name)
        self.statuses = statuses
        self.transitions = transitions

    def to_json(self) -> SingleJson:
        return {
            "name": self.name,
            "statuses": [status.to_workflow_status() for status in self.statuses],
            "transitions": [transition.to_json() for transition in self.transitions],
        }


class BulkCreateWorkflows:

    def __init__(
        self, statuses: list[WorkflowStatus], workflows: list[Workflow]
    ) -> None:
        self.statuses = statuses
        self.workflows = workflows

    def to_json(self) -> SingleJson:
        return {
            "scope": {"type": "GLOBAL"},
            "statuses": [status.to_json() for status in self.statuses],
            "workflows": [workflow.to_json() for workflow in self.workflows],
        }

    @classmethod
    def from_status_mapping(
        cls, name: str, status_mapping: dict[str : JiraCustomFields.JiraStatusCategory]
    ) -> BulkCreateWorkflows:
        """Create a BulkCreateWorkflows object from status mapping.

        Args:
            name: Workflow name
            status_mapping: Desired status mapping for the workflow

        Returns:
            BulkCreateWorkflows object
        """
        statuses = [
            WorkflowStatus(
                name=status,
                status_category=status_category,
                status_reference=str(uuid.uuid4()),
            )
            for status, status_category in status_mapping.items()
        ]

        workflow_transitions = [
            WorkFlowTransition(
                id_=str(index + 1), to=status, name=status.name, type_="GLOBAL"
            )
            for index, status in enumerate(statuses)
        ]
        workflow_transitions.append(
            WorkFlowTransition(
                id_=str(len(statuses) + 1),
                to=statuses[0],
                name="Created",
                type_="INITIAL",
            )
        )

        return BulkCreateWorkflows(
            statuses=statuses,
            workflows=[
                Workflow(name=name, statuses=statuses, transitions=workflow_transitions)
            ],
        )


class IssueType(BaseJiraModel):

    def __init__(
        self,
        name: str,
        description: str,
        hierarchy_level: int = 0,
        id_: str | None = None,
        raw_data: JSON | None = None,
    ) -> None:
        super().__init__(raw_data, id_, name)
        self.description = description
        self.hierarchy_level = hierarchy_level


class IssueTypeScheme(BaseJiraModel):

    def __init__(
        self,
        raw_data: dict,
        id_: str,
        name: str,
        project_ids: list[str] | None = None,
        issue_type_ids: list[str] | None = None,
        default_issue_type: str | None = None,
    ) -> None:
        super().__init__(raw_data, id_, name)
        self.default_issue_type = default_issue_type
        self.issue_type_ids = issue_type_ids
        self.project_ids = project_ids or []


class CustomField(BaseJiraModel):

    def __init__(
        self,
        name: str,
        description: str | None = None,
        type_: str | None = None,
        searcher_key: str | None = None,
        id_: str | None = None,
        options: list[str] | None = None,
        raw_data: SingleJson | None = None,
    ) -> None:
        super().__init__(raw_data, id_, name)
        self.description = description
        self.type = type_ and JiraCustomFields.FIELDS_TYPE_MAPPING[type_]
        self.searcher_key = searcher_key
        self.options = (
            [CustomFieldOption(value=op) for op in options]
            if options is not None
            else None
        )

    def to_json(self) -> SingleJson:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "searcherKey": self.searcher_key,
        }


class CustomFieldContext(BaseJiraModel):
    pass


class CustomFieldOption(BaseModel):

    def __init__(
        self,
        value: str,
        disabled: bool = False,
        id_: str | None = None,
        raw_data: SingleJson | None = None,
    ) -> None:
        super().__init__(raw_data)
        self.value = value
        self.disabled = disabled
        self.id = id_

    def to_json(self) -> SingleJson:
        return {"value": self.value, "disabled": self.disabled}


class CreateFieldMetadata(BaseModel):

    def __init__(
        self,
        raw_data: dict,
        name: str,
        key: str,
        required: bool,
        has_default_value: bool,
        allowed_values: list[SingleJson] | None = None,
    ) -> None:
        super().__init__(raw_data)
        self.name = name
        self.key = key
        self.required = required
        self.has_default_value = has_default_value
        self.allowed_values = allowed_values or []


class CreateIssue:
    __fields_metadata: list[CreateFieldMetadata] | None = None
    __forward_fields_mapping: dict = {}
    __backwards_fields_mapping: dict = {}

    __issue_attributes: dict[str, str] = {}

    def __getitem__(self, item: str) -> str:
        return self.__issue_attributes[item]

    def get(self, key: str, default: _T | None = None) -> str | _T:
        return self.__issue_attributes.get(key, default)

    def __init__(self, fields_dict) -> None:
        self.raise_if_not_configured()

        for key, value in fields_dict.items():
            self.__issue_attributes[key] = value

    @classmethod
    def is_configured(cls) -> bool:
        return cls.__fields_metadata is not None

    @classmethod
    def raise_if_not_configured(cls) -> None:
        if cls.is_configured():
            return

        raise ValueError(
            "fields_metadata is required to be set before issue creation, "
            "please run CreateIssue.set_fields_metadata() before issue creation"
        )

    @classmethod
    def set_fields_metadata(cls, fields_metadata: list[CreateFieldMetadata]) -> None:
        cls.__fields_metadata = fields_metadata

        for field in cls.__fields_metadata:
            cls.__forward_fields_mapping[field.name] = field.key
            cls.__backwards_fields_mapping[field.key] = field.name

    @classmethod
    def get_field_id_by_name(cls, field_name: str) -> str:
        """Get field ID by its name."""
        cls.raise_if_not_configured()

        if field_name not in cls.__forward_fields_mapping:
            raise KeyError(
                f"The field {field_name} is not defined for this issue " "type."
            )

        return cls.__forward_fields_mapping[field_name]

    @classmethod
    def build_from_field_names(cls, fields_dict: dict) -> CreateIssue:
        cls.raise_if_not_configured()

        existing_keys = set(cls.__forward_fields_mapping.keys())
        field_names = set(fields_dict.keys())

        if not field_names.issubset(existing_keys):
            raise KeyError(
                f"The fields {field_names.difference(existing_keys)} "
                "are not defined for this issue type."
            )

        return cls(fields_dict)

    @classmethod
    def build_from_api_response(cls, issue_data: SingleJson) -> CreateIssue:
        cls.raise_if_not_configured()
        _fields_dict = {}

        for field_key, field_value in issue_data.pop("fields").items():
            field_name = cls.__backwards_fields_mapping.get(field_key) or field_key
            _fields_dict[field_name] = field_value

        _fields_dict.update(issue_data)
        return cls(_fields_dict)

    def update_issue(self, fields_dict: Mapping) -> None:
        self.raise_if_not_configured()

        for field_name, field_value in fields_dict.items():
            if field_name not in self.__forward_fields_mapping:
                raise KeyError(
                    f"The field {field_name} is not defined for this issue " "type."
                )
            self.__issue_attributes[field_name] = field_value

    def create_json(self, logger) -> SingleJson:
        self.raise_if_not_configured()
        json_payload = {}

        for field in self.__fields_metadata:
            field_value = self.get(field.name)

            if field_value is None:
                if field.required and not field.has_default_value:
                    logger.warn(f"Field {field.name} cannot be empty")
                continue

            if field.allowed_values:
                for allowed_value in field.allowed_values:
                    if field_value == allowed_value.get("value"):
                        field_value = {"value": field_value}
                        break

                    elif field_value == allowed_value.get("id"):
                        field_value = {"id": field_value}
                        break

                    elif isinstance(field_value, dict) and (
                        field_value.get("value") == allowed_value.get("value")
                        or field_value.get("id") == allowed_value.get("id")
                    ):
                        break

                else:
                    logger.warn(
                        f"Field {field.name} can take only values from "
                        f"{field.allowed_values}"
                    )

            json_payload[field.key] = field_value

        return json_payload

    def display_json(self) -> dict[str, str]:
        return self.__issue_attributes
