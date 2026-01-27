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
import json

from OverflowManager import OverflowAlertDetails
from SiemplifyConnectorsDataModel import AlertInfo, CaseInfo

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import JSON, SingleJson


@dataclasses.dataclass
class ActionOutput:
    output_message: str
    result_value: str | bool
    execution_state: ExecutionState
    json_output: ActionJsonOutput | None
    debug_output: str = ""

    @classmethod
    def from_json(cls, json_: SingleJson) -> ActionOutput:
        result_object_json = json.loads(json_["ResultObjectJson"])
        json_result = result_object_json.get("JsonResult")
        return cls(
            output_message=json_["Message"],
            json_output=(
                ActionJsonOutput.from_json(json_result) if json_result is not None else None
            ),
            result_value=json_["ResultValue"],
            debug_output=json_["DebugOutput"],
            execution_state=ExecutionState(json_["ExecutionState"]),
        )

    def to_json(self) -> SingleJson:
        json_output = None if self.json_output is None else self.json_output.to_json()
        return {
            "Message": self.output_message,
            "ResultValue": self.result_value,
            "ExecutionState": self.execution_state.value,
            "ResultObjectJson": json.dumps({"JsonResult": json_output}),
            "DebugOutput": self.debug_output,
        }


@dataclasses.dataclass
class ActionJsonOutput:
    title: str = "JsonResult"
    content: str = ""
    type: str | None = None
    is_for_entity: bool = False
    json_result: JSON | None = None

    @classmethod
    def from_json(cls, json_: SingleJson) -> ActionJsonOutput:
        return cls(
            title=json_["Title"],
            type=json_["Type"],
            is_for_entity=json_["IsForEntity"],
            content=json_["Content"],
            json_result=json.loads(json_["RawJson"]),
        )

    def to_json(self) -> SingleJson:
        return {
            "Title": self.title,
            "Type": self.type,
            "IsForEntity": self.is_for_entity,
            "Content": self.content,
            "RawJson": json.dumps(self.json_result),
        }


@dataclasses.dataclass
class ConnectorOutput:
    json_output: ConnectorJsonOutput | None
    debug_output: str = ""

    @classmethod
    def from_json(cls, json_: SingleJson) -> ConnectorOutput:
        json_obj = json_["ResultObjectJson"]
        result_json = json.loads(json_obj) if json_obj is not None else None
        return cls(
            json_output=(
                ConnectorJsonOutput.from_json(result_json) if result_json is not None else None
            ),
            debug_output=json_["DebugOutput"],
        )

    def to_json(self) -> SingleJson:
        json_output = None if self.json_output is None else self.json_output.to_json()
        return {"ResultObjectJson": json.dumps(json_output), "DebugOutput": self.debug_output}


@dataclasses.dataclass
class ConnectorJsonOutput:
    alerts: list[AlertInfo | CaseInfo]
    overflow_alerts: list[OverflowAlertDetails] = dataclasses.field(default_factory=list)
    log_items: list = dataclasses.field(default_factory=list)
    log_rows: list[str] = dataclasses.field(default_factory=list)
    variables: dict = dataclasses.field(default_factory=dict)

    @classmethod
    def from_json(cls, json_: SingleJson) -> ConnectorJsonOutput:
        return cls(
            alerts=[alert_info_from_json(o) for o in json_["cases"]],
            overflow_alerts=[OverflowAlertDetails(**o) for o in json_["overflow_cases"]],
            log_items=json_["log_items"],
            log_rows=json_["log_rows"],
            variables=json_["variables"],
        )

    def to_json(self) -> SingleJson:
        return {
            "cases": [vars(o) for o in self.alerts],
            "overflow_cases": [vars(o) for o in self.overflow_alerts],
            "log_items": self.log_items,
            "variables": self.variables,
            "log_rows": self.log_rows,
        }


def alert_info_from_json(json_: SingleJson) -> AlertInfo:
    """Create an AlertInfo object from a json of attributes"""
    alert: AlertInfo = AlertInfo()
    alert.environment = json_["environment"]
    alert.ticket_id = json_["ticket_id"]
    alert.description = json_["description"]
    alert.display_id = json_["display_id"]
    alert.reason = json_["reason"]
    alert.name = json_["name"]
    alert.source_system_url = json_["source_system_url"]
    alert.source_rule_identifier = json_["source_rule_identifier"]
    alert.device_vendor = json_["device_vendor"]
    alert.device_product = json_["device_product"]
    alert.start_time = json_["start_time"]
    alert.end_time = json_["end_time"]
    alert.is_test_case = json_["is_test_case"]
    alert.priority = json_["priority"]
    alert.rule_generator = json_["rule_generator"]
    alert.source_grouping_identifier = json_["source_grouping_identifier"]
    alert.extensions = json_["extensions"]
    alert.events = json_["events"]
    alert.attachments = json_["attachments"]
    alert.siem_alert_id = json_["siem_alert_id"]

    return alert
