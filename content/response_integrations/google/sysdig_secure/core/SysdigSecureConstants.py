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
INTEGRATION_IDENTIFIER = "SysdigSecure"
INTEGRATION_DISPLAY_NAME = "Sysdig Secure"
INTEGRATION_PREFIX = "SysdigSecure_"

PING_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Ping"

ENDPOINTS = {
    "ping": "secure/events/v1/events",
    "get_events": "secure/events/v1/events",
}

ONE_HOUR_NS = 3600 * 1_000_000_000

# Events Connector
EVENTS_CONNECTOR = "Sysdig Secure - Events Connector"
MAX_LIMIT = 200
DEFAULT_LIMIT = 100
SEVERITIES = ["Informational", "Low", "Medium", "High"]
STORED_IDS_LIMIT = 1_000
DEFAULT_DEVICE_VENDOR = "Sysdig Secure"
DEFAULT_DEVICE_PRODUCT = "Sysdig Secure"
SEVERITY_TO_SOAR_SEVERITY_MAPPING = {
    0: 80,
    1: 80,
    2: 80,
    3: 80,
    4: 60,
    5: 60,
    6: 40,
    7: -1
}
SEVERITY_PARAMETER_MAPPING = {
    "informational": [7],
    "low": [6],
    "medium": [4, 5],
    "high": [0, 1, 2, 3]
}
TIME_DELTA_MS = 6 * 3_600_000
