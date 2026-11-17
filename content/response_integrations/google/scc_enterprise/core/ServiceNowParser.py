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

from typing import Any, TypeVar

from TIPCommon.types import SingleJson

from .SCCEnterpriseConsts import NOT_AVAILABLE
from . import ServiceNowDatamodels


_T = TypeVar("_T")


def parse_sn_entry(class_: type[_T], raw_data: SingleJson) -> _T:
    return class_(raw_data=raw_data, **raw_data)


def get_value(raw_data: SingleJson, key: str) -> str:
    field: str | SingleJson = raw_data.get(key, "")
    return field if isinstance(field, str) else field.get("value", "")


def build_incident_instance(raw_data: SingleJson) -> ServiceNowDatamodels.Incident:
    assignee = raw_data.get("u_assigned_to", NOT_AVAILABLE)
    if isinstance(assignee, dict):
        # In case of detailed response is set to true
        assignee = assignee.get("display_value", NOT_AVAILABLE)

    return ServiceNowDatamodels.Incident(
        raw_data=raw_data,
        sys_id=raw_data.get("sys_id", ""),
        status=raw_data.get("u_status", ""),
        overview=raw_data.get("u_overview", NOT_AVAILABLE),
        severity=raw_data.get("u_severity", NOT_AVAILABLE),
        priority=raw_data.get("u_priority", NOT_AVAILABLE),
        assignee=assignee or NOT_AVAILABLE,  # assignee can exist but be ""
        case_uri=raw_data.get("u_source_link") or "",
        sys_created_on=raw_data.get("sys_created_on"),
        sys_created_by=raw_data.get("sys_created_by"),
    )


def build_ticket(item_json: SingleJson) -> ServiceNowDatamodels.Ticket:
    return ServiceNowDatamodels.Ticket(
        raw_data=item_json,
        state=item_json.get("u_status", ""),
        sys_id=item_json.get("sys_id", ""),
        number=item_json.get("number", ""),
    )


def build_comment(item_json: SingleJson) -> ServiceNowDatamodels.Comment:
    return ServiceNowDatamodels.Comment(
        raw_data=item_json,
        value=item_json.get("value"),
        sys_created_on=item_json.get("sys_created_on"),
        element_id=item_json.get("element_id"),
    )


def build_incident(item_json: SingleJson) -> ServiceNowDatamodels.Incident:
    return build_incident_instance(item_json)


def build_incidents(raw_data: SingleJson) -> list[ServiceNowDatamodels.Incident]:
    return [
        build_incident_instance(raw_data=incident)
        for incident in raw_data.get("result", [])
    ]


def build_result(raw_json: SingleJson, fn_name: str) -> Any:
    file_fns = globals()
    func = file_fns[fn_name]
    return func(raw_json.get("result", {}))


def build_results(raw_json: SingleJson, fn_name: str) -> list[Any]:
    file_fns = globals()
    func = file_fns[fn_name]
    return [func(item_json) for item_json in raw_json.get("result", [])]
