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

import dataclasses

from graphql_query import Argument, Field, Operation, Query, Variable

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class IssueQueryBuilder:
    issue_id: str
    variable_name: str = "id"
    variable_type: str = "ID!"
    operation_name: str = "GetIssue"
    query_name: str = "issue"

    def build_fields(self) -> list[str]:
        """Build the fields required in the issue query."""
        return [
            "id",
            "createdAt",
            "updatedAt",
            "status",
            "severity",
            "type",
            "description",
            "resolvedAt",
            Field(
                name="entitySnapshot",
                fields=[
                    "cloudPlatform",
                    "id",
                    "name",
                    "region",
                    "subscriptionName",
                    "type",
                ],
            ),
            Field(name="projects", fields=["id", "name"]),
            Field(name="sourceRules", fields=["id", "name", "description"]),
        ]

    def build_query(self) -> SingleJson:
        """Build the GraphQL query and variables payload."""
        variable = Variable(name=self.variable_name, type=self.variable_type)

        query = Query(
            name=self.query_name,
            arguments=[Argument(name=self.variable_name, value=variable)],
            fields=self.build_fields(),
        )

        operation = Operation(
            type="query",
            name=self.operation_name,
            variables=[variable],
            queries=[query],
        )

        return {
            "query": operation.render(),
            "variables": {self.variable_name: self.issue_id},
        }


@dataclasses.dataclass(slots=True)
class AddCommentThreadMutationBuilder:
    issue_id: str
    comment: str
    operation_name: str = "CreateIssueComment"
    mutation_name: str = "createIssueNote"
    input_variable_name: str = "input"
    input_variable_type: str = "CreateIssueNoteInput!"

    def build_mutation(self) -> SingleJson:
        """Builds the GraphQL mutation payload for adding a comment to an issue."""
        variable = Variable(
            name=self.input_variable_name,
            type=self.input_variable_type,
        )
        issue_note_fields = ["createdAt", "id", "text"]
        mutation = Query(
            name=self.mutation_name,
            arguments=[Argument(name=self.input_variable_name, value=variable)],
            fields=[Field(name="issueNote", fields=issue_note_fields)],
        )
        operation = Operation(
            type="mutation",
            name=self.operation_name,
            variables=[variable],
            queries=[mutation],
        )
        input_value = {"issueId": self.issue_id, "text": self.comment}

        return {
            "query": operation.render(),
            "variables": {self.input_variable_name: input_value},
        }


@dataclasses.dataclass(slots=True)
class UpdateIssuePatch:
    status: str | None = None
    resolution_reason: str | None = None
    resolution_note: str | None = None
    note: str | None = None

    def to_dict(self) -> SingleJson:
        """Convert instance to dict, mapping specific fields and excluding None values.

        Returns:
            SingleJson: Dictionary with mapped keys and non-None values.
        """
        field_map = {
            "resolution_reason": "resolutionReason",
            "resolution_note": "resolutionNote",
        }
        return {
            field_map.get(k, k): v for k, v in dataclasses.asdict(self).items() if v is not None
        }


@dataclasses.dataclass(slots=True)
class UpdateIssueMutationBuilder:
    issue_id: str
    patch: UpdateIssuePatch = dataclasses.field(default_factory=UpdateIssuePatch)
    variable_name_issue_id: str = "issueId"
    variable_name_patch: str = "patch"
    variable_name_override: str = "override"
    operation_name: str = "UpdateIssue"
    mutation_name: str = "updateIssue"
    return_note_field: str | None = None

    def build_mutation(self) -> SingleJson:
        """Builds the GraphQL mutation payload for updating an issue."""
        issue_id_var = Variable(name=self.variable_name_issue_id, type="ID!")
        patch_var = Variable(name=self.variable_name_patch, type="UpdateIssuePatch")
        variables = [issue_id_var, patch_var]

        variable_data = {
            self.variable_name_issue_id: self.issue_id,
            self.variable_name_patch: self.patch.to_dict(),
        }

        input_value_fields = [
            Argument(name="id", value=issue_id_var),
            Argument(name="patch", value=patch_var),
        ]
        issue_fields = ["id", "status", "resolutionReason", "note", "dueAt"]

        if self.return_note_field:
            issue_fields.remove("note")
            issue_fields.append("resolutionNote")

        mutation = Query(
            name=self.mutation_name,
            arguments=[Argument(name="input", value=input_value_fields)],
            fields=[
                Field(
                    name="issue",
                    fields=issue_fields,
                )
            ],
        )

        return {
            "query": Operation(
                type="mutation",
                name=self.operation_name,
                variables=variables,
                queries=[mutation],
            ).render(),
            "variables": variable_data,
        }
