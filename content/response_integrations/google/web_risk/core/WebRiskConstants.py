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
INTEGRATION_IDENTIFIER = "WebRisk"

# Actions
PING_SCRIPT_NAME = "Ping"
ENRICH_ENTITIES_SCRIPT_NAME = "EnrichEntities"
SUBMIT_ENTITIES_SCRIPT_NAME = "SubmitEntities"

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
OAUTH_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

CONFIDENCE_LEVELS = {
    "Select One": None,
    "Low": "LOW",
    "Medium": "MEDIUM",
    "High": "HIGH"
}
PLATFORMS = {
    "Select One": None,
    "Android": "ANDROID",
    "iOS": "IOS",
    "MacOS": "MACOS",
    "Windows": "WINDOWS",
}

# Test uri for enrichment taken from official doc page
# https://cloud.google.com/web-risk/docs/lookup-api#example-urissearch
URI_EXAMPLE = "http://testsafebrowsing.appspot.com/s/malware.html"