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

"""Constants for CrowdStrikeFalcon Integration Unit Tests."""
import json
import os
from typing import Any, Union

JSON = Union[dict[str, Any], list]


def get_json_data(file_path: str) -> JSON:
  return json.load(
      open(
          os.path.join(
              os.path.dirname(__file__),
              file_path,
          ),
      ),
  )

DEFAULT_TIME_STR: str = "2024-12-13T08:40:27Z"
IDS_DB_KEY: str = "ids"
COMMENT: str = "Comment"
NO_IDS: str = "no_ids"
AUTH_ROUTE: str = "/oauth2/token"

LIST_UPLOADED_IOCs_DATA = get_json_data(
    "mock_data/ListUploadedIOCs_data.json",
)

LIST_HOST_VULNERABILITIES_DATA = get_json_data(
    "mock_data/ListHostVulnerabilities_data.json",
)

GET_EVENT_OFFSET_DATA = get_json_data(
    "mock_data/GetEventOffset_data.json",
)

UPDATE_ID_PROTECTION_DETECTION = get_json_data(
    "mock_data/UpdateIdentityProtectionDetection_data.json",
)

UPDATE_DETECTION = get_json_data(
    "mock_data/UpdateDetection_data.json",
)

ADD_COMMENT_TO_DETECTION = get_json_data(
    "mock_data/AddCommentToDetection_data.json",
)

GET_HOST_INFORMATION = get_json_data(
    "mock_data/GetHostInformation_data.json",
)

INCIDENTS_CONNECTOR_RESPONSE_DATA = get_json_data(
    "mock_data/IncidentsConnector_data.json",
)

ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_RESPONSE_DATA = get_json_data(
    "mock_data/AddIdentityProtectionDetectionComment_data.json",
)

SEARCH_INCIDENT_RESPONSE_DATA = get_json_data(
    "mock_data/SearchIncident_data.json",
)

ADD_INCIDENT_COMMENT_RESPONSE_DATA = get_json_data(
    "mock_data/AddIncidentComment_data.json",
)

UPDATE_INCIDENT_RESPONSE_DATA = get_json_data(
    "mock_data/UpdateIncident_data.json",
)

IOC_IDs = LIST_UPLOADED_IOCs_DATA.get("ioc_ids")

GET_IOCs_JSON = LIST_UPLOADED_IOCs_DATA.get("get_iocs")

SEARCH_DEVICES_IDS_LIST = LIST_HOST_VULNERABILITIES_DATA.get(
    "search_devices_ids",
)

GET_VULNERABILITY_IDS_JSON = LIST_HOST_VULNERABILITIES_DATA.get(
    "get_vulnerability_ids",
)

VULNERABILITY_DETAILS_JSON = LIST_HOST_VULNERABILITIES_DATA.get(
    "get_vulnerabilities_detailed_information",
)

REMIDIATION_DEAILS_JSON = LIST_HOST_VULNERABILITIES_DATA.get(
    "get_remediation_details",
)

GET_STREAM_DETECTIONS_JSON = GET_EVENT_OFFSET_DATA.get(
    "get_stream_detections",
)

GET_ALERT_DETAILS = UPDATE_ID_PROTECTION_DETECTION.get(
    "get_alert_details",
)

UPDATE_DETECTION_JSON = UPDATE_DETECTION.get(
    "update_detection_json",
)

ADD_COMMENT_TO_DETECTION_JSON = ADD_COMMENT_TO_DETECTION.get(
    "add_comment_to_detection",
)

GET_DEVICE_LOGIN_HISTORIES_JSON = GET_HOST_INFORMATION.get(
    "get_device_login_histories",
)

GET_DEVICE_LOGIN_HISTORIES_OUT_JSON = GET_HOST_INFORMATION.get(
    "get_device_login_histories_output",
)

GET_INCIDENT_DETAILS_JSON = INCIDENTS_CONNECTOR_RESPONSE_DATA.get(
    "get_incident_details",
)

GET_INCIDENTS_JSON = INCIDENTS_CONNECTOR_RESPONSE_DATA.get(
    "get_incidents",
)

GET_INCIDENT_BEHAVIORS_JSON = INCIDENTS_CONNECTOR_RESPONSE_DATA.get(
    "get_incident_behaviors",
)

GET_INCIDENT_BEHAVIORS_DETAILS_JSON = INCIDENTS_CONNECTOR_RESPONSE_DATA.get(
    "get_incident_behaviors_details",
)

SEARCH_DETECTION_JSON = ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_RESPONSE_DATA.get(
    "search_detection",
)

ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_JSON = ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_RESPONSE_DATA.get(
    "add_comment",
)

SEARCH_INCIDENT_JSON = SEARCH_INCIDENT_RESPONSE_DATA.get(
    "search_incident_success",
)

ADD_INCIDENT_COMMENT_INCIDENT_JSON = ADD_INCIDENT_COMMENT_RESPONSE_DATA.get(
    "add_incident_comment",
)

GET_UUID_SUCCESS_JSON = UPDATE_INCIDENT_RESPONSE_DATA.get(
    "get_uuid_success",
)

MOCK_DATA = get_json_data("mock_data/mock_data.json")

DETECTION_ID = "xxx_test_data:ind:xxxx_test:xxx_62804241178466-10305-75828240"

INCIDENT_IDS = [
    "inc:xxx_test_data:xxx999",
    "inc:xxx-test-data77f8xca5879xc82fc:xxxa1f784d6x4bec91e97dxcbf123",
]

INCIDENT_ID = INCIDENT_IDS[0]

BEHAVIOR_IDS = [
    "ind:xxxa1c5ef609ac479ba77f8ca5879c82fc:771xx9930685184-10x307-565x008",
    "ind:xxx2a1c5ef609ac479ba77f8ca5879c82fc:77xxx19929095705-103x06-564496x",
]

TEST_COMMENT = "Test11"

INCIDENT_ID_STATUS = "New"
INCIDENT_ID_ASSIGN_TO = "Yuriy Landovskyy"

SUCCESS_STATUS_CODE = 200
NOT_FOUND_STATUS_CODE = 404
BAD_REQUEST_STATUS_CODE = 400

TEST_SEVERITY_VALUE = 1
TEST_UNIXTIMESTAMP = 1695297950000
TEST_LIMIT_VALUE = 100
MILLISECONDS_IN_SECOND = 1000

TEST_ZERO_VALUE = 0

INVALID_IDS = ["invalid_id1", "invalid_id2"]
INVALID_ID = INVALID_IDS[0]
