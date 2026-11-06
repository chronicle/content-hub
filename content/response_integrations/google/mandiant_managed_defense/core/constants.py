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
PROVIDER_NAME = "Mandiant MD"
INTEGRATION_NAME = "MandiantManagedDefense"
INTEGRATION_PREFIX = "Mandiant_MD_"

# Action names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"


ENDPOINTS = {
    "generate_token": "/token",
    "test_connectivity": "/investigations",
    "get_investigations": "/investigations",
    "get_investigation_details": "/investigations/{external_id}",
}

# investigations connector
INVESTIGATIONS_CONNECTOR = "Mandiant Managed Defense - Investigations Connector"
MAX_LIMIT = 100
ALERT_STATUSES = ["open", "resolved", "disputed", "false-positive"]
STORED_IDS_LIMIT = 10_000
DEFAULT_DEVICE_VENDOR = "Mandiant Managed Defense"
DEFAULT_DEVICE_PRODUCT = "Investigations"
SEVERITY_MAPPING = {
    "under review": -1,
    "informational": -1,
    "low": 40,
    "medium": 60,
    "high": 80,
}
MAIN_ALERT_EVENT_TYPE = "Main Alert"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
BAD_TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
FETCH_INTERVAL = 12
SOURCE_NAME = "FaaS Portal"
SKIPPED_OBJECTS = ["x-fireeye-com-investigation"]
OBJECT_TYPE_NOTE = "x-fireeye-com-note"
NOTE_TYPE_COMMENT = "comment"
COMPROMISE_TARGET_TYPE = "x-fireeye-com-compromise-target"
COM_ALERT_TYPE = "x-fireeye-com-alert"
MIN_PADDING_LIMIT = 1
MAX_PADDING_LIMIT = 12
