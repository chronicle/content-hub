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
import json
from integration_testing.common import get_def_file_content

import datetime
import pathlib
from collections.abc import Collection

from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser
from crowd_strike_falcon.core.datamodels import (
    AlertDetails,
    Detection,
    DetectionDetail,
    IncidentDetails,
)
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.types import Entity, SingleJson

from integration_testing.common import create_entity, get_def_file_content


class IdNotFoundError(Exception):
    """Generic error for when an ID cannot be found"""

class AlreadyExistsError(Exception):
    """Generic error for when an ID already exists"""


def create_alert(alert_id: str) -> AlertDetails:
    return CrowdStrikeParser().build_siemplify_alert_details(
        raw_data={
            "id": alert_id,
            "composite_id": f"composite_{alert_id}",
            "display_name": f"Alert for {alert_id}",
            "description": f"Description for alert {alert_id}",
            "product": "Default Product",
            "severity": 10,
            "type": "Default Type",
            "start_time": None,
            "end_time": None,
            "created_timestamp": "Tue, 28 Mar 2017 21:34:39 +0700",
            "updated_timestamp": "Tue, 28 Mar 2017 21:34:39 +0700",
        },
    )

def create_detection(detection_id: str) -> DetectionDetail:
    return CrowdStrikeParser().build_siemplify_detection_detail(
        detection_details_json={
            "detection_id": detection_id,
            "first_behavior": "2024-11-04T15:36:01Z",
            "last_behavior": "2024-11-04T15:36:01Z",
            "max_severity": 50,
            "behaviors": [],
            "max_severity_displayname": "Medium",
        },
    )

def create_incident(incident_id: str) -> IncidentDetails:
    return CrowdStrikeParser().build_siemplify_incident_details(
        raw_data={
            "incident_type": 1,
            "incident_id": incident_id,
            "hosts": [
                {
                    "device_id": "fee8a6ef0cb3412e9a781dcae0287c85",
                    "hostname": "DESKTOP-VTGTQP6",
                },
            ],
            "fine_score": 21,
            "tactics": [
                "Defense Evasion",
                "Privilege Escalation",
                "Credential Access",
            ],
            "start": "2023-01-09T11:23:27Z",
            "end": "2023-01-09T12:52:01Z",
        },
    )

def create_stream_detection(detection_id: str) -> Detection:
    return CrowdStrikeParser().build_siemplify_detection_obj(
        detection_data={
            "metadata": {
                "offset": 26334507,
                "eventType": "AuthActivityAuditEvent",
                "eventCreationTime": datetime.datetime.now().timestamp() * 1000,
            },
            "event": {
                "OperationName": "logged",
                "id": detection_id,
                "ServiceName": "api_request",
                "AuditKeyValues": [
                    {
                        "Key": "received_time",
                        "ValueString": "2024-11-06T11:08:39.478253943Z",
                    },
                ],
            },
        },
    )

def check_for_invalid_elements(json_data, keys=("composite_ids", "ids")):
    """Checks JSON data for invalid elements and returns an error response if found.

    Args:
        json_data (dict): The JSON payload to validate.
        keys (tuple): Keys to check in the JSON payload.

    Returns:
        dict: An error response if invalid elements are found; otherwise, None.

    """
    if (
        isinstance(json_data, dict) and
        any(json_data.get(key, [])[0:1] == ["no_ids"] for key in keys)
    ):
        return {
            "errors": [
                {
                    "code": 400,
                    "message": "invalid element in the request",
                },
            ],
        }
    return None


HOSTNAME_ENTITY_ID: str = "npatni-sysops"
HOSTNAME_ENTITY: Entity = create_entity(HOSTNAME_ENTITY_ID, EntityTypesEnum.HOST_NAME)
SCRIPT_DEADLINE_TIME: datetime.datetime = (
        datetime.datetime.now() + datetime.timedelta(minutes=10)
)
TIMEOUT: SingleJson = {
    "execution_deadline_unix_time_ms": int(
        SCRIPT_DEADLINE_TIME.timestamp() * 1000,
    ),
}
VALID_JSON_SUFFIXES: Collection[str] = (
    ".json",
    ".yaml",
    ".def",
    ".yaml",
    ".yaml",
)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
SUBMIT_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent / "dummy.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
