from __future__ import annotations

from typing import Iterable

from TIPCommon.types import SingleJson
from scc_enterprise.core import JiraDatamodels
from scc_enterprise.core.JiraDatamodels import Issue
from scc_enterprise.core.JiraUtils import extract_text_from_adf


def build_issue_obj(raw_data: SingleJson) -> JiraDatamodels.Issue:
    return JiraDatamodels.Issue(
        raw_data=raw_data,
        id_=raw_data.get("id"),
        expand=raw_data.get("expand"),
        raw_fields=raw_data.get("fields"),
        key=raw_data.get("key"),
        project_id=raw_data.get("fields", {}).get("project", {}).get("id"),
        project_key=raw_data.get("fields", {}).get("project", {}).get("key"),
        project_name=raw_data.get("fields", {}).get("project", {}).get("name"),
        created=raw_data.get("fields", {}).get("created"),
        updated=raw_data.get("fields", {}).get("updated"),
        priority=raw_data.get("fields", {}).get("priority", {}).get("name"),
        status=raw_data.get("fields", {}).get("status", {}).get("name"),
        project_type_key=(
            raw_data.get("fields", {}).get("project", {}).get("projectTypeKey")
        ),
        attachments=build_issue_attachment_list_obj(
            raw_data.get("fields", {}).get("attachment", [])
        ),
        comments=build_issue_comment_obj_list(
            raw_data.get("fields", {}).get("comment", {}).get("comments", [])
        ),
    )


def build_issue_attachment_obj(raw_data: SingleJson) -> JiraDatamodels.Issue.Attachment:
    return JiraDatamodels.Issue.Attachment(
        raw_data=raw_data,
        filename=raw_data.get("filename"),
        author_account_id=raw_data.get("author", {}).get("accountId"),
        created=raw_data.get("created"),
        size=raw_data.get("size"),
        content_link=raw_data.get("content"),
    )


def build_issue_attachment_list_obj(
    raw_data: Iterable[SingleJson],
) -> list[Issue.Attachment]:
    return [build_issue_attachment_obj(raw_attachment) for raw_attachment in raw_data]


def build_issue_obj_list(raw_data: Iterable[SingleJson]) -> list[Issue]:
    return [build_issue_obj(raw_issue) for raw_issue in raw_data]


def build_issue_comment_obj_list(raw_data: Iterable[SingleJson]) -> list[Issue.Comment]:
    return [build_issue_comment_obj(raw_comment) for raw_comment in raw_data]


def build_issue_comment_obj(raw_comment: SingleJson) -> JiraDatamodels.Issue.Comment:
    body: str | None = raw_comment.get("body")
    if isinstance(body, dict):
        body = extract_text_from_adf(body).strip()

    return JiraDatamodels.Issue.Comment(
        raw_data=raw_comment,
        created=raw_comment.get("created"),
        updated=raw_comment.get("updated"),
        body=body,
        id_=raw_comment.get("id"),
    )


def build_issue_type_obj(raw_data: SingleJson) -> JiraDatamodels.IssueType:
    return JiraDatamodels.IssueType(
        raw_data=raw_data,
        id_=raw_data.get("id"),
        name=raw_data.get("name"),
        hierarchy_level=raw_data.get("hierarchyLevel"),
        description=raw_data.get("description"),
    )


def build_issue_type_obj_list(
    raw_data: list[SingleJson],
) -> list[JiraDatamodels.IssueType]:
    return [build_issue_type_obj(issue_type_data) for issue_type_data in raw_data]


def build_project_obj(raw_data: SingleJson) -> JiraDatamodels.Project:
    return JiraDatamodels.Project(
        raw_data=raw_data,
        id_=raw_data.get("id"),
        key=raw_data.get("key"),
        name=raw_data.get("name"),
        style=raw_data.get("style"),
        issue_types=build_issue_type_obj_list(raw_data.get("issueTypes")),
    )


def build_issue_type_scheme_obj(raw_data: SingleJson) -> JiraDatamodels.IssueTypeScheme:
    return JiraDatamodels.IssueTypeScheme(
        raw_data=raw_data,
        id_=(raw_data.get("id") or raw_data.get("issueTypeSchemeId")),
        name=raw_data.get("name"),
        default_issue_type=raw_data.get("defaultIssueTypeId"),
        issue_type_ids=(
            list(
                map(
                    lambda it: it["id"],
                    raw_data.get("issueTypes", {}).get("values", []),
                )
            )
        ),
    )


def build_custom_field_obj(raw_data: SingleJson) -> JiraDatamodels.CustomField:
    return JiraDatamodels.CustomField(
        raw_data=raw_data,
        id_=raw_data.get("id"),
        name=raw_data.get("name"),
        description=raw_data.get("description"),
    )


def build_custom_field_context_obj(
    raw_data: SingleJson,
) -> JiraDatamodels.CustomFieldContext:
    return JiraDatamodels.CustomFieldContext(
        raw_data=raw_data, id_=raw_data.get("id"), name=raw_data.get("name")
    )


def build_workflow_obj(raw_data: SingleJson) -> JiraDatamodels.Workflow:
    return JiraDatamodels.Workflow(
        raw_data=raw_data, id_=raw_data.get("id"), name=raw_data.get("name")
    )


def build_create_field_metadatas(
    raw_data: list[SingleJson],
) -> list[JiraDatamodels.CreateFieldMetadata]:
    return [
        JiraDatamodels.CreateFieldMetadata(
            raw_data=create_field_data,
            name=create_field_data.get("name"),
            key=create_field_data.get("key"),
            required=create_field_data.get("required"),
            has_default_value=create_field_data.get("hasDefaultValue"),
            allowed_values=[
                allowed_value
                for allowed_value in create_field_data.get("allowedValues", [])
            ],
        )
        for create_field_data in raw_data
    ]
