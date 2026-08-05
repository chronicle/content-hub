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

# Security Events Connector
from __future__ import annotations
SECURITY_EVENTS_CONNECTOR_NAME = "Cisco AMP - Security Events Connector"

MAX_EVENTS_PAGE_LIMIT = 500
DEFAULT_EVENTS_PAGE = 100
MAX_EVENTS = 1000
DEFAULT_TIME_FRAME = 1
DEFAULT_MAX_LIMIT = 100
SEVERITIES = ["Low", "Medium", "High", "Critical"]
DEVICE_VENDOR = "Cisco"
DEVICE_PRODUCT = "Cisco AMP"
STORED_IDS_LIMIT = 3000
EVENT_ID_FIELD = "id"

SEVERITY_TO_SIEM = {"Info": -1, "Low": 40, "Medium": 60, "High": 80, "Critical": 100}

SEVERITIES_MAP = {
    "Low": ("Low", "Medium", "High", "Critical"),
    "Medium": ("Medium", "High", "Critical"),
    "High": ("High", "Critical"),
    "Critical": ("Critical",),
}

# Manager
LIMIT = 500
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip",
}
