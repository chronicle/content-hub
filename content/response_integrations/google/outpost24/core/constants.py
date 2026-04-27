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

INTEGRATION_NAME = "Outpost24"
INTEGRATION_DISPLAY_NAME = "Outpost24"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"

GET_TOKEN_URL = "{}/opi/rest/auth/login"
PING_URL = "{}/opi/rest/outscan/findings?limit=1"
GET_DEVICES_URL = "{}/opi/rest/outscan/targets"
GET_FINDINGS_URL = "{}/opi/rest/outscan/findings"

SUPORTED_RISK_LEVELS = [
    "low",
    "medium",
    "high",
    "critical",
    "initial",
    "recommendation",
]
ENRICHMENT_PREFIX = "Outpost24"
DEFAULT_API_LIMIT = 1000

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Outscan Findings Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 100
DEVICE_VENDOR = "Outpost24"
DEVICE_PRODUCT = "Outpost24"

POSSIBLE_TYPES = ["Information", "Vulnerability", "Port"]

SEVERITY_MAP = {
    "Initial": -1,
    "Recommendation": -1,
    "Low": 40,
    "Medium": 60,
    "High": 80,
    "Critical": 100,
}

SEVERITIES = ["initial", "recommendation", "low", "medium", "high", "critical"]

FINDING_TYPES = {
    "All": "Vulnerability, Information",
    "Vulnerability": "Vulnerability",
    "Information": "Information",
}

RISK_COLOR_MAP = {
    "LOW": "#ffff00",
    "MEDIUM": "#ff9900",
    "HIGH": "#ff0000",
    "CRITICAL": "#ff0000",
}

INSIGHT_HTML_TEMPLATE = """
<table>
<tbody>
<tr>
<td>
<h2 style="text-align: left;"><strong>Business Criticality: <span style="color: {risk_color};">{criticality}</span></strong></h2>
</td>
</tr>
</tbody>
</table>
<p><strong>Hostname: </strong>{hostname}<strong><br />IP: </strong>{ip}<strong><br />Exposed: </strong>{exposed}<strong><br /></strong><strong>Source: </strong>{source}</p>
"""

INSIGHT_HTML_TEMPLATE_FINDINGS = """

<h3><strong>Findings Stats</strong></h3>
<h4>Type</h4>
<p><strong>Vulnerability</strong>: {count_vulnerability_findings}<br /><strong>Information:&nbsp;</strong>{count_information_findings}</p>
<p><strong>Risk Level</strong></p>
<p><strong>Initial:</strong>&nbsp;{count_initial_findings}<strong><br /></strong><strong>Recommendation:&nbsp;</strong>{count_recommendation_findings}<strong><br />Low:&nbsp;</strong>{count_low_findings}<strong><br />Medium:&nbsp;</strong>{count_medium_findings}<strong><br />High:</strong>&nbsp;{count_high_findings}<strong><br />Critical:&nbsp;</strong>{count_critical_findings}</p>
"""
