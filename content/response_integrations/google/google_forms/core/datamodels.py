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

import collections
from copy import deepcopy
import dataclasses
from enum import Enum
from typing import Any

from EnvironmentCommon import EnvironmentHandle
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson
from . import constants


IntegrationParameters = collections.namedtuple(
    "IntegrationParameters", ["siemplify_logger"]
)


class GoogleFormPriorityEnum(Enum):
    CRITICAL: str = "Critical"
    HIGH: str = "High"
    MED: str = "Medium"
    LOW: str = "Low"
    INFORMATIONAL: str = "Informational"


class SiemplifyPriorityEnum(Enum):
    CRITICAL: int = 100
    HIGH: int = 80
    MED: int = 60
    LOW: int = 40
    INFORMATIONAL: int = 20


PRIORITIES_MAP = {
    GoogleFormPriorityEnum.CRITICAL: SiemplifyPriorityEnum.CRITICAL,
    GoogleFormPriorityEnum.HIGH: SiemplifyPriorityEnum.HIGH,
    GoogleFormPriorityEnum.MED: SiemplifyPriorityEnum.MED,
    GoogleFormPriorityEnum.LOW: SiemplifyPriorityEnum.LOW,
    GoogleFormPriorityEnum.INFORMATIONAL: SiemplifyPriorityEnum.INFORMATIONAL,
}


def calculate_priority(severity) -> int:
    """Calculate the Siemplify alarm priority based on the severity value.

    Args:
        severity (str): The severity value .

    Returns:
        int: The calculated Siemplify alarm priority
    """
    for priority, siemplify_priority in PRIORITIES_MAP.items():
        if severity == priority.value:
            return siemplify_priority.value

    return SiemplifyPriorityEnum.INFORMATIONAL.value


@dataclasses.dataclass(frozen=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return dataclasses.asdict(self)

    def to_flat(self) -> dict[str, Any]:
        return dict_to_flat(self.to_json()["raw_data"])


@dataclasses.dataclass(frozen=True)
class AlertResponse(BaseModel):
    """Class to create data model for Alert Response"""

    form_id: str
    alert_id: str
    form_json: SingleJson
    create_time: str
    events: list = dataclasses.field(default_factory=list)

    @classmethod
    def from_json(
        cls,
        alert_json: SingleJson,
        form_json: FormResponse,
    ) -> AlertResponse:
        """Creates an AlertResponse object from a JSON representation.

        This method takes the JSON representation of an alert and associated form
        response data to construct an `AlertResponse` object.

        Args:
            alert_json (SingleJson): The JSON representation of the alert.
            form_json (FormResponse): The form response data associated with the alert.

        Returns:
            AlertResponse: The constructed `AlertResponse` object.
        """
        alert_json["form_Id"] = form_json.form_id
        alert_json["title"] = form_json.title
        alert_json["description"] = form_json.description
        return cls(
            form_id=form_json.form_id,
            raw_data=alert_json,
            form_json=form_json,
            alert_id=alert_json["responseId"],
            create_time=convert_string_to_unix_time(alert_json["createTime"]),
        )

    def build_events(
        self,
        alert_json: SingleJson,
    ) -> list[dict]:
        """Builds a list of event dictionaries from an alert JSON object.

        This method processes the input alert JSON to generate a list of event
        dictionaries, where each event corresponds to a question and its
        associated answer.

        Args:
            alert_json (SingleJson): The JSON representation of the alert,
                containing details about questions and answers.

        Returns:
            list[dict]: A list of event dictionaries, each representing a question
            and its corresponding answer data.
        """
        events = []
        create_time = convert_string_to_unix_time(alert_json["createTime"])

        base_event = {
            "responseId": alert_json["responseId"],
            "createTime": create_time,
            "lastSubmittedTime": alert_json["lastSubmittedTime"],
            "event_type": "Question",
        }
        answers = alert_json.get("answers", {})

        for question_id, answer_data in answers.items():
            event = base_event.copy()
            event["questionId"] = question_id
            event.update(answer_data)
            events.append(event)

        return events

    def get_alert_info(
        self,
        alert_info: AlertInfo,
        environment_common: EnvironmentHandle,
        severity: str,
    ) -> AlertInfo:
        """Populates and returns updated alert information.

        This method updates the provided `AlertInfo` object with details extracted
        from the raw data of the alert, such as metadata, timestamps, and events.

        Args:
            alert_info (AlertInfo): The `AlertInfo` object to be updated with
                alert details.
            environment_common (EnvironmentHandle): The environment handle used
                to fetch environment-specific details.
            severity (str): The severity level of the alert.

        Returns:
            AlertInfo: The updated `AlertInfo` object with populated fields.
        """
        alert_id = self.raw_data["responseId"]
        form_id = self.raw_data["form_Id"]
        title = self.raw_data["title"]
        create_time = convert_string_to_unix_time(self.raw_data["createTime"])
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = alert_id
        alert_info.display_id = f"GForms_{alert_id}"
        alert_info.name = f'Form "{title}" Response'
        alert_info.reason = "N/A"
        alert_info.description = self.raw_data["description"]
        alert_info.device_vendor = constants.DEVICE_VENDOR
        alert_info.device_product = constants.DEVICE_PRODUCT
        alert_info.priority = calculate_priority(severity)
        alert_info.rule_generator = f'Form "{title}" Response'
        alert_info.source_grouping_identifier = form_id
        alert_info.start_time = create_time
        alert_info.end_time = create_time
        alert_info.events = self.to_events(alert_json=self.raw_data)

        return alert_info

    def set_events(self) -> None:
        """Set alert events

        Returns: (): None
        """
        self.events.append(deepcopy(self.build_events(alert_json=self.raw_data)))

    def to_events(self, alert_json: SingleJson) -> list[SingleJson]:
        """Convert alert events to siemplify events.

        Args:
            alert_json (SingleJson): alert data in JSON format

        Returns:
           list[SingleJson]: list of flat events
        """
        events = deepcopy(self.build_events(alert_json=alert_json))
        return [dict_to_flat(event) for event in events]


@dataclasses.dataclass(frozen=True)
class FormResponse(BaseModel):
    """Class for form details api response."""

    raw_data: SingleJson
    form_id: str
    title: str
    description: str

    @classmethod
    def from_json(cls, form_json: SingleJson) -> FormResponse:
        """Create a form object from a JSON representation.

        Args:
            from_json (SingleJson): The JSON representation of the asset.

        Returns:
            FormResponse: The created form object.
        """
        form_info: SingleJson = form_json.get("info", {})

        return cls(
            raw_data=form_json,
            title=form_info.get("title") or form_json.get("formId"),
            description=form_info.get("description", ""),
            form_id=form_json.get("formId"),
        )
