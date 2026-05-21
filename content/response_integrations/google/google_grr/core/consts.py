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
INTEGRATION_NAME = "GoogleGRR"
INTEGRATION_DISPLAY_NAME = "Google GRR"

# Error Codes:
API_UNAUTHORIZED_ERROR = 401
API_NOT_FOUND_ERROR = 404
API_BAD_REQUEST = 400

# Error Messages
INVALID_HUNT_ID = "invalid literal for int() with base 16"

WEEK_IN_SECONDS = 604800


UTC = "UTC"

HUNT_URL_PART = "/#/hunts/"

# Actions Names:
PING = "Ping"
LIST_CLIENTS = "List Clients"
GET_CLIENT_DETAILS = "Get Client Details"
LIST_LAUNCHED_FLOWS = "List Launched Flows"
GET_HUNT_DETAILS = "Get Hunt Details"
LIST_HUNTS = "List Hunts"
STOP_A_HUNT = "Stop a Hunt"
START_A_HUNT = "Start a Hunt"

STOP_STATE = "STOPPED"
START_STATE = "STARTED"
PAUSE_STATE = "PAUSED"
