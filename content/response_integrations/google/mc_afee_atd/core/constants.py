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
INTEGRATION_NAME = "McAfeeATD"
INTEGRATION_DISPLAY_NAME = "McAfee ATD"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
CHECK_HASH_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Check Hash"
GET_ANALYZER_PROFILES_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Get Analyzer Profiles"
)
GET_REPORT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Report"
SUBMIT_FILE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit File"
SUBMIT_URL_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit URL"
