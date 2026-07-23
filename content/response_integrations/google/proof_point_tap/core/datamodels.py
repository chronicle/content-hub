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
import dataclasses
from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict
from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    username: str
    password: str
    verify_ssl: bool


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Campaign(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        description=None,
        startDate=None,
        families=None,
        malware=None,
        techniques=None,
        brands=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.start_date = startDate
        self.families = families
        self.malwares = malware
        self.techniques = techniques
        self.brands = brands

    @classmethod
    def from_json(cls, data: SingleJson):
        return cls(
            raw_data=data,
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            startDate=data.get("startDate"),
            families=data.get("families"),
            malware=data.get("malware"),
            techniques=data.get("techniques"),
            brands=data.get("brands"),
        )

    def to_json(self) -> SingleJson:
        return self.raw_data

    def to_table(self):
        return {
            "Name": self.name,
            "Description": self.description,
            "Start Date": self.start_date,
            "Related Families": (
                ", ".join([fam.get("name", "") for fam in self.families])
                if self.families
                else ""
            ),
            "Related Malware": (
                ", ".join([m.get("name", "") for m in self.malwares])
                if self.malwares
                else ""
            ),
            "Related Techniques": (
                ", ".join([t.get("name", "") for t in self.techniques])
                if self.techniques
                else ""
            ),
            "Related Actors": (
                ", ".join([brand.get("name", "") for brand in self.brands])
                if self.brands
                else ""
            ),
        }

    def to_insight(self):
        html_content = ""

        html_content += f"<h2><strong>{self.name}</strong></h2>"
        html_content += f"<p><strong>Start Date: {self.start_date}</strong><br />"
        html_content += (
            f"<p><strong>Related Families: "
            f"{', '.join([fam.get('name', '') for fam in self.families]) if self.families else 'N/A'}"
            "</strong><br />"
        )
        html_content += (
            f"<strong>Related Malware: "
            f"{', '.join([m.get('name', '') for m in self.malwares]) if self.malwares else 'N/A'}"
            "</strong><br />"
        )
        html_content += (
            f"<strong>Related Techniques: "
            f"{', '.join([t.get('name', '') for t in self.techniques]) if self.techniques else 'N/A'}"
            "</strong><br />"
        )
        html_content += (
            f"<strong>Related Actors: "
            f"{', '.join([brand.get('name', '') for brand in self.brands]) if self.brands else 'N/A'}"
            "</strong><br /></p>"
        )
        description = self.description.replace("\r\n", "<br>").replace("\n", "<br>")
        html_content += f"<p><strong>{description}</strong></p>"

        return html_content


class ForensicObj(BaseModel):
    def __init__(self, raw_data, forensics):
        super().__init__(raw_data)
        self.forensics = forensics


class Forensic(BaseModel):
    def __init__(
        self,
        raw_data,
        type=None,
        display=None,
        malicious=None,
        what=None,
        platforms=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.type = type
        self.display = display
        self.malicious = malicious
        self.what = what
        self.platforms = platforms

    def to_table(self):
        return {
            "Type": self.type,
            "Description": self.display,
            "Malicious": self.malicious,
            "URL": self.what.get("url", ""),
            "Path": self.what.get("path", ""),
            "SHA256": self.what.get("sha256", ""),
            "IP Address": self.what.get("ip", ""),
            "Platforms": (
                ", ".join([p.get("name", "") for p in self.platforms])
                if self.platforms
                else ""
            ),
        }


class DecodedURL(BaseModel):
    def __init__(
        self,
        raw_data,
        encodedUrl=None,
        decodedUrl=None,
        error=None,
        success=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.encoded_url = encodedUrl
        self.decoded_url = decodedUrl
        self.error = error
        self.success = success


@dataclasses.dataclass(slots=True)
class Event:
    raw_data: SingleJson
    event_type: str
    spam_score: int
    phis_score: int
    subject: str

    @classmethod
    def from_json(cls, event_data: SingleJson, event_type: str):
        return cls(
            raw_data=event_data,
            event_type=event_type,
            spam_score=event_data.get("spamScore"),
            phis_score=event_data.get("phisScore"),
            subject=event_data.get("subject"),
        )

    def to_json(self):
        self.raw_data["eventType"] = self.event_type
        return self.raw_data


@dataclasses.dataclass(slots=True)
class ThreatForensic:
    raw_data: SingleJson
    threat_type: str
    display: str
    engine: str
    malicious: bool
    note: str
    time: int
    platforms: list[SingleJson]

    @classmethod
    def from_json(cls, data: SingleJson):
        return cls(
            raw_data=data,
            threat_type=data.get("type"),
            display=data.get("display"),
            engine=data.get("engine"),
            malicious=data.get("malicious"),
            note=data.get("note"),
            time=data.get("time", 0),
            platforms=data.get("platforms", []),
        )

    def to_json(self) -> SingleJson:
        return self.raw_data


@dataclasses.dataclass(slots=True)
class ThreatReport:
    raw_data: SingleJson
    threat_id: str
    name: str
    threat_status: str
    scope: str

    @classmethod
    def from_json(cls, data: SingleJson):
        return cls(
            raw_data=data,
            threat_id=data.get("id"),
            name=data.get("name"),
            threat_status=data.get("threatStatus"),
            scope=data.get("scope"),
        )

    def to_json(self) -> SingleJson:
        return self.raw_data
