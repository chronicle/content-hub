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
from datetime import timedelta

INTEGRATION_IDENTIFIER = "CloudLogging"
INTEGRATION_DISPLAY_NAME = "Cloud Logging"

PING_SCRIPT_NAME = "Ping"
EXECUTE_QUERY_SCRIPT_NAME = "Execute Query"
SCOPES = ["https://www.googleapis.com/auth/logging.read"]

API_URL = "https://logging.googleapis.com"
ENDPOINTS = {
    "ping": "v2/monitoredResourceDescriptors",
    "execute_query": "v2/entries:list",
}

CUSTOM_TIME = "Custom"
TIME_INTERVALS = {
    "Last Hour": timedelta(hours=1),
    "Last 6 Hours": timedelta(hours=6),
    "Last 24 Hours": timedelta(hours=24),
    "Last Week": timedelta(weeks=1),
    "Last Month": timedelta(weeks=4),
}
