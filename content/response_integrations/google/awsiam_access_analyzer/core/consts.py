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
INTEGRATION_NAME = "AWS IAM Access Analyzer"
VENDOR = "AWS"
PRODUCT = "IAM Access Analyzer"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ASC = "ASC"
DESC = "DESC"
DEFAULT_MAX_RESULTS = 100
PAGE_SIZE = 50

DEFAULT_HOURS_BACKWARDS = 1
DEFAULT_TIMEOUT_IN_SECONDS = 180
DEFAULT_ALERT_SEVERITY = "Medium"
DEFAULT_MAX_FINDINGS_TO_FETCH = 50

NOT_AVAILABLE = "N/A"

MAX_RETRIES = 10

ARCHIVED_STATUS = "ARCHIVED"

CONNECTOR_DISPLAY_NAME = "AWS IAM Access Analyzer - Findings Connector"

SEVERITIES = {"INFORMATIONAL": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}

RULE_GENERATOR_NAME = "AWS IAM Access Analyzer"
