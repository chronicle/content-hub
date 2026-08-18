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
from collections.abc import Mapping, MutableMapping, Sequence


INTEGRATION_NAME: str = "Extrahop"

PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
UPDATE_DETECTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Update Detection"

CONNECTOR_NAME = f"{INTEGRATION_NAME} - Detections Connector"
ENDPOINTS: MutableMapping[str, str] = {
    "token": "/oauth2/token",
    "ping": "/api/v1/devices?search_type=ip address&limit=1",
    "get_detections": "/api/v1/detections/search",
    "get_device_details": "/api/v1/devices/{device_id}",
    "get_and_update_detection": "/api/v1/detections/{detection_id}",
}
DEFAULT_TIME_FRAME: int = 1
DEFAULT_LIMIT: int = 100
DEVICE_VENDOR: str = "Extrahop"
DEVICE_PRODUCT: str = "Extrahop"
DEVICE_OBJECT_TYPE: str = "device"
ALERT_ID_KEY: str = "id"
STATUS_MAPPING: Mapping[str, str] = {
    "In Progress": "in_progress",
    "Closed": "closed",
    "Acknowledged": "acknowledged",
}
RESOLUTION_MAPPING: Mapping[str, str] = {
    "Action Taken": "action_taken",
    "No Action Taken": "no_action_taken",
}
DEFAULT_PARAM_VALUE: str = "Select One"
CLOSED_STATUS: str = "Closed"
POSSIBLE_STATUS_VALUES: Sequence[str] = [
    DEFAULT_PARAM_VALUE,
    "Closed",
    "In Progress",
    "Acknowledged",
]
POSSIBLE_RESOLUTION_VALUES: Sequence[str] = [
    DEFAULT_PARAM_VALUE,
    "Action Taken",
    "No Action Taken",
]
INVALID_CREDS: str = "invalid_client"
