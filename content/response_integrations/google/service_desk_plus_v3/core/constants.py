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
INTEGRATION_NAME = "ServiceDeskPlusV3"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
ADD_NOTE_ACTION = f"{INTEGRATION_NAME} - Add Note"
ADD_NOTE_AND_WAIT_ACTION = f"{INTEGRATION_NAME} - Add Note And Wait For Reply"
CLOSE_REQUEST_ACTION = f"{INTEGRATION_NAME} - Close Request"
CREATE_REQUEST_ALERT_ACTION = f"{INTEGRATION_NAME} - Create Alert Request"
CREATE_REQUEST_ACTION = f"{INTEGRATION_NAME} - Create Request"
CREATE_REQUEST_DROPDOWN_ACTION = f"{INTEGRATION_NAME} - Create Request - Dropdown Lists"
UPDATE_REQUEST_ACTION = f"{INTEGRATION_NAME} - Update Request"
GET_REQUEST_ACTION = f"{INTEGRATION_NAME} - Get Request"
WAIT_FOR_STATUS_UPDATE_ACTION = f"{INTEGRATION_NAME} - Wait For Status Update"
WAIT_FOR_FIELD_UPDATE_ACTION = f"{INTEGRATION_NAME} - Wait For Field Update"

UPDATE_REQUEST_TYPE = "UPDATE"
CREATE_REQUEST_TYPE = "CREATE"


# Requests
REQUESTS_URL = "requests"
SPECIFIC_REQUEST_URL = "requests/{}"
ADD_NOTE_URL = "requests/{}/notes"
CLOSE_REQUEST_URL = "requests/{}/close"
GET_NOTE_URL = "requests/{}/notes/{}"

# Jobs
SYNC_CLOSURE_SCRIPT_NAME = f"{INTEGRATION_NAME} - SyncClosure"
SERVICE_DESK_PLUS_TAG = "ServiceDeskPlus"
REQUESTS_TAG = "ServiceDeskPlus Requests:"
TAG_SEPARATOR = ":"
CANCELLED_STATUS = "Cancelled"
CLOSED_STATUS = "Closed"
RESOLVED_STATUS = "Resolved"
REASON = "Maintenance"
ROOT_CAUSE = "None"
COMMENT = "{status} in ServiceDeskPlus"
CASE_STATUS_CLOSED = 2
CASE_STATUS_OPEN = 1
DEFAULT_HOURS_BACKWARDS = 24
MIN_HOURS_BACKWARDS = 1
