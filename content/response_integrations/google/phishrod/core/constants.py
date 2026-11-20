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
INTEGRATION_NAME = "Phishrod"
INTEGRATION_DISPLAY_NAME = "Phishrod"

DEFAULT_DEVICE_VENDOR = "PhishRod"
DEFAULT_DEVICE_PRODUCT = "PhishRod"
DEFAULT_RULE_GENERATOR = "PhishRod"
DEFAULT_SOURCE_GROUPING_IDENTIFIER = "PhishRod"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
UPDATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Incident"
MARK_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Mark Incident"

# Connector Names
INCIDENTS_CONNECTOR_NAME = f"{INTEGRATION_NAME} - Incidents Connector"

# Connector Constant
TIMEOUT_THRESHOLD = 0.9
STORED_IDS_LIMIT = 2000

ENDPOINTS = {
    "ping": "/api/jsonws/phishrod.psc_secondary_analysis_tracking/get-secondary-analysis-tracking?apiKey={api_key}&clientId={client_id}",
    "get_incidents": "/api/jsonws/phishrod.psc_primary_analysis_tracking/get-primary-analysis-tracking?apiKey={api_key}&clientId={client_id}",
    "update_incident": "/api/jsonws/phishrod.psc_secondary_analysis_tracking/update-incident-status?apiKey={api_key}&clientId={client_id}&incidentNumber={incidentNumber}&incidentStatus={incidentStatus}",
    "mark_incident": "/api/jsonws/phishrod.psc_primary_analysis_tracking/initiate-primary-analysis?apiKey={api_key}&clientId={client_id}&incidentNumber={incidentNumber}&action={incident_status}&comment={comment}",
}

SEVERITIES = {"INFORMATIONAL": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}

FORBIDDEN_STATUS = 403

# Mark Incident Constants
MARK_INCIDENT_STATUS_TYPE = {
    "Mark For Secondary Analysis": "suspicious",
    "Mark As Safe": "safe",
    "Mark As Spam": "spam",
}

RESPONSE_ALREADY_UPDATED = "Incident status has already been updated before"

# Update Incident Constants
UPDATE_INCIDENT_STATUS_DEFAULT_VALUE = "Delete"
UPDATE_INCIDENT_ALREADY_MARKED_MESSAGE = "Incident status is already marked."
