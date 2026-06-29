# Copyright 2026 Google LLC
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
import pathlib
import abc


from typing import MutableMapping, TypedDict

from TIPCommon.base.action import CaseComment, EntityTypesEnum
from TIPCommon.data_models import AlertCard, CaseDetails, DatabaseContextType
from TIPCommon.types import Entity, SingleJson

from integration_testing.common import create_entity
from integration_testing.platform.external_context import ExternalContextRowKey
from google_sec_ops_ai_agents.tests.mocks.siemplify.common import GeminiCaseSummary


class GoogleSecOpsSoar(abc.ABC):

    def __init__(self) -> None:
        self._cases: MutableMapping[int, CaseData] = {}
        self._alerts: MutableMapping[str, AlertData] = {}
        self._entities: MutableMapping[str, Entity] = {}
        self._case_scope_context: MutableMapping[str, ExternalContextRowKey] = {}
        self._custom_field_values: MutableMapping[str, SingleJson] = {}
        self._custom_fields: MutableMapping[str, SingleJson] = {}
        self._case_summary: MutableMapping[int, GeminiCaseSummary] = {}

    def set_custom_fields(self, custom_fields: list[SingleJson]) -> None:
        """Set custom field values."""
        self._custom_fields = {cf["id"]: cf for cf in custom_fields}

    def list_custom_fields(
            self,
            custom_field_name: str | None = None
    ) -> list[SingleJson]:
        """List custom field values."""
        custom_fields = self._custom_fields.values()
        if custom_field_name:
            custom_fields = filter(
                lambda cf: cf["displayName"] == custom_field_name,
                custom_fields
            )

        return list(custom_fields)

    def set_custom_field_values(self, custom_field_values: list[SingleJson]) -> None:
        """Set custom field values."""
        self._custom_field_values = {
            cfv["customFieldId"]: cfv for cfv in custom_field_values
        }

    def list_custom_field_values(self) -> list[SingleJson]:
        """List custom field values."""
        return list(self._custom_field_values.values())

    def set_case_scope_context(self, key: str, value: str) -> None:
        """Sets a scope context value for a case."""
        context_data: ExternalContextRowKey = ExternalContextRowKey(
            context_type=DatabaseContextType, identifier=key, property_key=value
        )
        self._case_scope_context[key] = context_data

    def get_case_scope_context(self, key: str | int) -> ExternalContextRowKey:
        """Gets a scope context value for a case."""
        return self._case_scope_context.get(key)

    @property
    def cases(self) -> list[CaseDetails]:
        return [case["case_details"] for case in self._cases.values()]

    @property
    def number_of_cases(self) -> int:
        return len(self._cases)

    def get_case(self, case_id: int | str) -> CaseDetails:
        """Get a case by ID"""
        case_id: int = _cast_id(case_id)
        if case_id not in self._cases:
            raise ValueError("Case not found")

        return self._cases[case_id]["case_details"]

    def get_alert(self, alert_name: int | str) -> AlertCard:
        """Get a case by ID"""
        if alert_name not in self._alerts:
            raise ValueError("alert not found")

        return self._alerts[alert_name]["alert_details"]

    def get_alerts(self) -> list[AlertCard]:
        """Get all alerts"""
        return [_alert["alert_details"] for _alert in self._alerts.values()]

    def add_alert(self, alert: AlertCard) -> None:
        """Add an alert"""
        self._alerts[alert.identifier] = {"alert_details": alert}

    def add_entity(
        self,
        identifier: str,
        category: EntityTypesEnum,
    ) -> None:
        """Adds an entity to the internal entity collection."""
        entity: Entity = create_entity(
            identifier=identifier,
            type_=category,
        )
        self._entities[identifier] = entity

    def get_entity(self, identifier) -> Entity:
        """Get an entity by identifier"""
        return self._entities.get(identifier)

    def get_entities(self) -> list[Entity]:
        """Get all entities as a list"""
        return list(self._entities.values())

    def add_case(
        self,
        case: CaseDetails,
        case_comments: list[CaseComment] | None = None,
    ) -> None:
        """Add a case"""
        if case_comments is None:
            case_comments = []

        self._cases[case.id_] = {
            "case_details": case,
            "comments": {c.comment_id: c for c in case_comments},
        }

    def update_case(self, case: CaseDetails) -> None:
        """Update a case"""
        if case.id_ not in self._cases:
            raise ValueError

        existing_case: CaseDetails = self._cases[case.id_]["case_details"]
        vars(existing_case).update(vars(case))

    def get_case_comment(
        self,
        case_id: str | int,
        comment_id: str | int,
    ) -> CaseComment:
        """Get a case comment by case ID and comment ID"""
        case_id: int = _cast_id(case_id)
        comment_id: int = _cast_id(comment_id)
        if case_id not in self._cases:
            raise ValueError(f"Case {case_id} not found")

        comments: MutableMapping[int, CaseComment] = self._cases[case_id]["comments"]
        if comment_id not in comments:
            raise ValueError(f"Comment {comment_id} not found")

        return comments[comment_id]

    def get_all_case_comment(self, case_id: str | int) -> list[CaseComment]:
        """Get all case comments by case ID"""
        case_id: int = _cast_id(case_id)
        if case_id not in self._cases:
            raise ValueError(f"Case {case_id} not found")

        return list(self._cases[case_id]["comments"].values())

    def add_case_comment(self, case_id: int | str, comment: CaseComment) -> None:
        """Add a case comment to a case"""
        case_id: int = _cast_id(case_id)
        if case_id not in self._cases:
            raise ValueError("Case not found")

        self._cases[case_id]["comments"][comment.comment_id] = comment

    def case_number_of_comments(self, case_id: str | int) -> int:
        """Get the number of comments for a case"""
        case_id: int = _cast_id(case_id)
        if case_id not in self._cases:
            raise ValueError("Case not found")

        return len(self._cases[case_id]["comments"])

    def add_case_summary(self, case_id: int, case_summary: GeminiCaseSummary) -> None:
        """Add a case summary for a case"""
        self._case_summary[case_id] = case_summary

    def get_case_summary(self, case_id: int) -> GeminiCaseSummary:
        """Get the case summary for a case"""
        if case_id not in self._case_summary:
            raise ValueError("Case summary not found")

        return self._case_summary[case_id]


class CaseData(TypedDict):
    case_details: CaseDetails
    comments: MutableMapping[int, CaseComment]


class AlertData(TypedDict):
    alert_details: AlertCard


def _cast_id(id_: str | int):
    if isinstance(id_, str):
        if not id_.isdigit():
            raise TypeError("Case ID must be an integer or a digit string")
        return int(id_)

    if isinstance(id_, int):
        return id_

    raise TypeError("Case ID must be int or str")
