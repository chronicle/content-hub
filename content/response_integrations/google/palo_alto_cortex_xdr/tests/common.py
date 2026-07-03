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
import pathlib

from TIPCommon.data_models import AlertCard, CaseDetails
from TIPCommon.types import SingleJson
from ..core.datamodels import (
    Alert,
    Incident,
    IncidentExtraData,
    IncidentInfo,
    XQLSearch,
    XQLSearchResult,
)
from integration_testing.common import get_def_file_content


INTEGRATION_PATH = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
GET_INCIDENT_DETAILS: SingleJson = MOCK_DATA["get_incident_details"]
GET_INCIDENTS: SingleJson = MOCK_DATA["get_incidents"]
GET_INCIDENT_EXTRA_DATA: SingleJson = MOCK_DATA["get_incident_extra_data"]
EXECUTE_XQL_SEARCH: SingleJson = MOCK_DATA["execute_xql_search"]
ENDPOINT_DATA: SingleJson = MOCK_DATA["endpoint_data"]
EXECUTE_XQL_SEARCH_RESULT: SingleJson = MOCK_DATA["execute_xql_search_result"]
INVALID_TOKEN: SingleJson = MOCK_DATA["invalid_token"]
INVALID_INCIDENT: SingleJson = MOCK_DATA["invalid_incident"]
INVALID_INCIDENT_ID: int = -1
CONNECTOR_INCIDENT_ID: int = 1111
INVALID_API_KEY_ID: int = -1
CASE_ID: str = "54321"
ALERT_ID: str = "98765"
MOCK_CASE_IDENTIFIER: str = "54321"

JOB_MOCK_INCIDENT: SingleJson = MOCK_DATA["job_mock_incident"]
JOB_MOCK_INCIDENT_EXTRA_DATA: SingleJson = MOCK_DATA["job_mock_incident_extra_data"]
JOB_MOCK_CASE_DETAILS_DATA: SingleJson = MOCK_DATA["job_mock_case_details_data"]

LIST_ALERTS_URL: str = "/1.0/alerts/"


class IncidentIdNotFoundError(Exception):
    """Accessed Incident ID cannot be found"""


INCIDENT: Incident = Incident.from_json(GET_INCIDENT_DETAILS["reply"])
EXECUTE_XQL_SEARCH: XQLSearch = XQLSearch.from_json(EXECUTE_XQL_SEARCH)
EXECUTE_XQL_SEARCH_RESULT: XQLSearchResult = XQLSearchResult.from_json(
    EXECUTE_XQL_SEARCH_RESULT["reply"]
)

INCIDENTS_INFO: list[IncidentInfo] = [
    IncidentInfo.from_json(incident) for incident in GET_INCIDENTS["reply"]["incidents"]
]
INCIDENT_EXTRA_DATA_INFO: IncidentExtraData = IncidentExtraData.from_json(
    GET_INCIDENT_EXTRA_DATA["reply"]
)


def get_mock_incident() -> IncidentInfo:
    """Helper to create a mock IncidentInfo object from mock_data.json.

    Returns:
        IncidentInfo: The mocked IncidentInfo object.
    """
    return IncidentInfo.from_json(JOB_MOCK_INCIDENT)


def get_mock_incident_extra_data(incident: IncidentInfo) -> IncidentExtraData:
    """Helper to create a mock IncidentExtraData object with alerts from mock_data.json.

    Args:
        incident (IncidentInfo): The base incident to associate with the extra data.

    Returns:
        IncidentExtraData: The mocked IncidentExtraData object.
    """
    alert_raw_data: SingleJson = JOB_MOCK_INCIDENT_EXTRA_DATA["alerts"][0]
    mock_alert: Alert = Alert(
        alert_id=alert_raw_data["alert_id"],
        severity=alert_raw_data["severity"],
        raw_data=alert_raw_data,
    )

    return IncidentExtraData(
        incident=incident,
        alerts=[mock_alert],
        file_artifacts=JOB_MOCK_INCIDENT_EXTRA_DATA["file_artifacts"],
        network_artifacts=JOB_MOCK_INCIDENT_EXTRA_DATA["network_artifacts"],
        raw_data={},
    )


def get_mock_case_details() -> CaseDetails:
    """Helper to create a mock CaseDetails object from mock_data.json.

    Returns:
        CaseDetails: The mocked CaseDetails object.
    """
    alert_card_data: SingleJson = JOB_MOCK_CASE_DETAILS_DATA["alert_card"]
    mock_alerts: list[AlertCard] = [AlertCard(**alert_card_data)]

    case_details_data: SingleJson = JOB_MOCK_CASE_DETAILS_DATA["case_details"].copy()
    case_details_data["alerts"] = mock_alerts
    case_details_data["wall_data"] = []
    case_details_data["entity_cards"] = []
    case_details_data["entities"] = []
    case_details_data["score"] = 0
    case_details_data["involved_suspicious_entity"] = False
    case_details_data["workflow_status"] = ""
    case_details_data["source"] = "Siemplify"
    case_details_data["products"] = []
    case_details_data["tasks"] = []
    case_details_data["last_modifying_user_id"] = ""
    case_details_data["related_alerts"] = []
    case_details_data["alert_count"] = len(mock_alerts)
    return CaseDetails(**case_details_data)
