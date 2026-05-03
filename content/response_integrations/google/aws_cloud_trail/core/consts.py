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
INTEGRATION_NAME = "AWSCloudTrail"
INTEGRATION_DISPLAY_NAME = "AWS Cloud Trail"

PING_SCRIPT_NAME = "Ping"

# Connectors
CONNECTOR_DISPLAY_NAME = "AWS Cloud Trail - Insights Connector"
DEVICE_VENDOR = "AWS"
DEVICE_PRODUCT = "Cloud Trail"
INSIGHT_ID_FIELD = "event_id"

DEFAULT_ALERT_SEVERITY = "Medium"
DEFAULT_TIMEOUT_IN_SECONDS = 180
DEFAULT_MAX_INSIGHTS_TO_FETCH = 50
DEFAULT_MAX_HOURS_BACKWARDS = 1
PAGE_SIZE = 50
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

CRITICAL_RISK = "critical"
HIGH_RISK = "high"
MEDIUM_RISK = "medium"
LOW_RISK = "low"
INFORMATIONAL_RISK = "informational"

INSIGHTS_ALERT_SEVERITIES = [
    INFORMATIONAL_RISK,
    LOW_RISK,
    MEDIUM_RISK,
    HIGH_RISK,
    CRITICAL_RISK,
]

CLOUD_TRAIL_TO_SIEMPLIFY_PRIORITIES = {
    INFORMATIONAL_RISK: -1,
    LOW_RISK: 40,
    MEDIUM_RISK: 60,
    HIGH_RISK: 80,
    CRITICAL_RISK: 100,
}
