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
INTEGRATION_NAME = "QualysEDR"
INTEGRATION_DISPLAY_NAME = "Qualys EDR"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"


HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

ENDPOINTS = {"auth": "auth", "events": "ioc/events"}

PARAMETERS_DEFAULT_DELIMITER = ","

# Connector
CONNECTOR_NAME = "Qualys EDR - Events Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_MAX_LIMIT = 100
MAX_LIMIT = 1000
MIN_SCORE = 0
MAX_SCORE = 10
DEVICE_VENDOR = "Qualys"
DEVICE_PRODUCT = "Qualys EDR"
POSSIBLE_TYPES = ["file", "mutex", "process", "network", "registry"]

SEVERITY_MAP = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}
