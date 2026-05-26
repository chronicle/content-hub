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
PRIORITIES = ["LOW", "MEDIUM", "HIGH"]
DEVICE_VENDOR = "Symantec"
DEVICE_PRODUCT = "Symantec ATP"
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
INCIDENTS_CONNECTOR_NAME = "Symantec ATP Incidents Connector"
SYMANTEC_TO_SIEM_PRIORITY = {1: 40, 2: 60, 3: 80}
SIEM_TO_SYMANTEC_PRIORITY = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
ATP_QUERIES_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
MIN_INCIDENTS_TO_FETCH = 100
MAX_INCIDENTS_TO_FETCH = 1000
LATEST_EVENTS_FOR_INCIDENT = 100
LIMIT_IDS_IN_IDS_FILE = 3000
IDS_HOURS_LIMIT = 72
ALERT_ID_FIELD = "uuid"
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
