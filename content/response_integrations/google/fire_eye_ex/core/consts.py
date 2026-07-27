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
ALERTS_CONNECTOR_NAME = "FireEye EX - Alerts Connector"
TIMEOUT_THRESHOLD = 0.9
HOURS_LIMIT_IN_IDS_FILE = 72
TEST_OFFSET_HOURS = 24
DURATION = "48_hours"
MAP_FILE = "map.json"
IDS_FILE = "ids.json"
DEVICE_VENDOR = "FireEye"
DEVICE_PRODUCT = "FireEye EX"
ALERT_NAME = "Malicious Email"
PRINT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
