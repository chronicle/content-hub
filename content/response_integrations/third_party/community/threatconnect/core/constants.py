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

"""ThreatConnect V3 integration constants."""

from __future__ import annotations

INTEGRATION_NAME: str = "ThreatConnect"
PING_SCRIPT_NAME: str = "ThreatConnect - Ping"
EXECUTE_HTTP_REQUEST_SCRIPT_NAME: str = "ThreatConnect - Execute HTTP Request"
SECURITY_LABELS_URI: str = "/api/v3/securityLabels"
INDICATORS_URI: str = "/api/v3/indicators"

ENDPOINTS: dict[str, str] = {
    "ping": INDICATORS_URI,
    "security_labels": SECURITY_LABELS_URI,
    "indicators": INDICATORS_URI,
    "indicator_details": f"{INDICATORS_URI}/{{encoded_value}}",
}

MAX_INT_SENTINEL: int = 9223372036854775807

EXCLUDE_FIELDS_SET: set[str] = {
    "tags",
    "attributes",
    "associatedGroups",
    "groups",
    "associatedIndicators",
    "indicators",
    "securityLabels",
    "observations",
    "lastObserved",
    "legacyLink",
}

PLURAL_MAPPING: dict[str, str] = {
    "Adversary": "adversaries",
    "Attack Pattern": "attackPatterns",
    "Campaign": "campaigns",
    "Course of Action": "coursesOfAction",
    "Document": "documents",
    "Email": "emails",
    "Event": "events",
    "Incident": "incidents",
    "Intrusion Set": "intrusionSets",
    "Malware": "malware",
    "Report": "reports",
    "Signature": "signatures",
    "Tactic": "tactics",
    "Task": "tasks",
    "Threat": "threats",
    "Tool": "tools",
    "Vulnerability": "vulnerabilities",
}
