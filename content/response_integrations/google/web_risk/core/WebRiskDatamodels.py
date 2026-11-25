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
from enum import Enum
from dataclasses import dataclass

from TIPCommon.types import SingleJson


@dataclass(frozen=True, slots=True)
class ToJsonMixin:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return self.raw_data


class AbuseType(Enum):
    MALWARE = "Malware"
    SOCIAL_ENGINEERING = "Social Engineering"
    UNWANTED_SOFTWARE = "Unwanted Software"


class ThreatJustification(Enum):
    MANUAL_VERIFICATION = "Manual Verification"
    USER_REPORT = "User Report"
    AUTOMATED_REPORT = "Automated Report"


class ThreatTypeEnum(Enum):
    THREAT_TYPE_UNSPECIFIED = "THREAT_TYPE_UNSPECIFIED"
    MALWARE = "MALWARE"
    SOCIAL_ENGINEERING = "SOCIAL_ENGINEERING"
    UNWANTED_SOFTWARE = "UNWANTED_SOFTWARE"
    SOCIAL_ENGINEERING_EXTENDED_COVERAGE = "SOCIAL_ENGINEERING_EXTENDED_COVERAGE"


@dataclass(frozen=True, slots=True)
class ThreatObject(ToJsonMixin):
    threat_types: list[ThreatTypeEnum]
    expire_time: str
    hash: str | None = None

    @classmethod
    def from_json(cls, raw_data: SingleJson) -> "ThreatObject":
        """Parse JSON to ThreatObject data model."""
        return cls(
            raw_data=raw_data,
            threat_types=[ThreatTypeEnum(tt) for tt in raw_data.get("threatTypes", [])],
            hash=raw_data.get("hash"),
            expire_time=raw_data.get("expireTime"),
        )


@dataclass
class Submission:
    submission_uri: str
    abuse_type: AbuseType | None
    confidence_level: str | None
    justification: ThreatJustification | None
    comment: str | None
    region_codes: list[str] | None
    platform: str | None

    def build_threat_info(self) -> SingleJson:
        """Build threat info sub payload."""
        threat_info = {}
        if self.abuse_type is not None:
            threat_info["abuseType"] = self.abuse_type.name

        if self.confidence_level is not None:
            threat_info["threatConfidence"] = {
                "level": self.confidence_level.upper()
            }

        if self.justification is not None or self.comment is not None:
            threat_justification = {}
            if self.justification is not None:
                threat_justification["labels"] = [
                    self.justification.name
                ]

            if self.comment is not None:
                threat_justification["comments"] = [self.comment, ]

            threat_info["threatJustification"] = threat_justification

        return threat_info

    def build_threat_discovery(self) -> SingleJson:
        """Build threat discovery sub payload."""
        threat_discovery = {}
        if self.platform is not None:
            threat_discovery["platform"] = self.platform.upper()

        if self.region_codes is not None:
            threat_discovery["regionCodes"] = self.region_codes

        return threat_discovery

    def to_payload(self) -> SingleJson:
        """Transform Submission object to JSON payload."""
        return {
            "submission": {
                "uri": self.submission_uri
            },
            "threatInfo": self.build_threat_info(),
            "threatDiscovery": self.build_threat_discovery(),
        }

@dataclass(frozen=True, slots=True)
class Operation(ToJsonMixin):
    name: str
    state: str
    done: bool
    error: SingleJson | None = None

    @property
    def is_running(self) -> bool:
        return self.done is False

    @classmethod
    def from_json(cls, raw_data: SingleJson) -> "Operation":
        """Parse JSON to Operation data model."""
        return cls(
            raw_data=raw_data,
            name=raw_data.get("name"),
            state=raw_data.get("metadata", {}).get("state"),
            done=raw_data.get("done", False),
            error=raw_data.get("error"),
        )
