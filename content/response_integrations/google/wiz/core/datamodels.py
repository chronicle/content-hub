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

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    siemplify_logger: ScriptLogger
    auth_url: str | None = None


@dataclasses.dataclass(slots=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        """Convert the model to a JSON serializable format.

        Returns:
            The raw JSON data.

        """
        return self.raw_data


class WizIncidentComment:
    def __init__(self, raw_comment: SingleJson) -> None:
        self.raw_comment = raw_comment

    @property
    def message(self) -> str:
        """The text comment message.

        Returns:
            str: The comment text.

        """
        return self.raw_comment.get("text", "")


@dataclasses.dataclass(slots=True)
class WizServiceTicket(BaseModel):
    id_: str
    external_id: str | None = None
    name: str | None = None
    url: str | None = None

    @classmethod
    def from_json(cls, json_data: SingleJson) -> WizServiceTicket:
        """Create a WizServiceTicket instance from JSON data.

        Returns:
            WizServiceTicket: The parsed WizServiceTicket object.

        """
        return cls(
            raw_data=json_data,
            id_=json_data["id"],
            external_id=json_data.get("externalId"),
            name=json_data.get("name"),
            url=json_data.get("url"),
        )


@dataclasses.dataclass(slots=True)
class Issue(BaseModel):
    issue_id: str
    status: str | None = None
    severity: str | None = None
    updated_at: str | None = None
    comments: list[WizIncidentComment] = dataclasses.field(default_factory=list)
    service_tickets: list[WizServiceTicket] = dataclasses.field(default_factory=list)

    @classmethod
    def from_json(cls, json_data: SingleJson) -> Issue:
        """Create an Issue instance from JSON data.

        Returns:
            An Issue instance.

        """
        notes = json_data.get("notes") or []
        comments = [WizIncidentComment(note) for note in notes]
        tickets_json = json_data.get("serviceTickets") or []
        service_tickets = [WizServiceTicket.from_json(ticket) for ticket in tickets_json]
        return cls(
            raw_data=json_data,
            issue_id=json_data["id"],
            status=json_data.get("status"),
            severity=json_data.get("severity"),
            updated_at=json_data.get("updatedAt"),
            comments=comments,
            service_tickets=service_tickets,
        )


@dataclasses.dataclass(slots=True)
class IssueComment(BaseModel):
    comment_id: str

    @classmethod
    def from_json(cls, json_data: SingleJson) -> IssueComment:
        """Create an IssueComment instance from JSON data.

        Returns:
            An IssueComment instance.

        """
        return cls(raw_data=json_data, comment_id=json_data["id"])


@dataclasses.dataclass(slots=True)
class VulnerabilityFinding(BaseModel):
    finding_id: str
    name: str
    severity: str

    @classmethod
    def from_json(cls, json_data: SingleJson) -> VulnerabilityFinding:
        """Create a VulnerabilityFinding instance from JSON data.

        Returns:
            A VulnerabilityFinding instance.

        """
        return cls(
            raw_data=json_data,
            finding_id=json_data["id"],
            name=json_data.get("name", ""),
            severity=json_data.get("severity", ""),
        )


@dataclasses.dataclass(slots=True)
class ThreatAIAnalysis(BaseModel):
    analysis_id: str | None
    status: str | None
    verdict: str | None
    analyzed_at: str | None
    severity: str | None
    confidence_level: str | None
    conclusion: str | None

    @classmethod
    def from_json(
        cls,
        raw_data: SingleJson,
        json_data: SingleJson | None
    ) -> ThreatAIAnalysis | None:
        """Create a ThreatAIAnalysis instance from JSON data.

        Returns:
            A ThreatAIAnalysis instance, or None if json_data is empty.

        """
        if not json_data:
            return None

        return cls(
            raw_data=raw_data,
            analysis_id=json_data.get("id"),
            status=json_data.get("status"),
            verdict=json_data.get("verdict"),
            analyzed_at=json_data.get("analyzedAt"),
            severity=json_data.get("severity"),
            confidence_level=json_data.get("confidenceLevel"),
            conclusion=json_data.get("conclusion"),
        )
