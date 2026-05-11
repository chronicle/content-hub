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
INTEGRATION_NAME = "ArcSightLogger"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
SEND_QUERY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Send Query"

PAGE_LIMIT = 100

ENDPOINTS = {
    "login": "/core-service/rest/LoginService/login",
    "logout": "/core-service/rest/LoginService/logout",
    "search": "/server/search",
    "status": "/server/search/status",
    "events": "/server/search/events",
}

LOGIN_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}
REQUEST_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

LOGIN_DATA = "login={}&password={}"
LOGOUT_DATA = "authToken={}"

QUERY_STATUS_COMPLETED = "complete"
QUERY_STATUS_RUNNING = "running"
QUERY_STATUS_STARTING = "starting"
QUERY_STATUS_ERROR = "error"

DEFAULT_TIME_FRAME = "1h"
TIME_UNIT_MAPPER = {
    "w": "weeks",
    "d": "days",
    "h": "hours",
    "m": "minutes",
    "s": "seconds",
}
