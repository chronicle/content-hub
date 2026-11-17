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
from .SCCEnterpriseConsts import INTEGRATION_NAME as SCCE_NAME

INTEGRATION_NAME = "Jira"

JIRA_TICKET_URI = "{ui_root}/browse/{ticket_id}"
JIRA_SYNC_TICKET_TYPE = "Task"

MAX_RESULTS = 100
UNAUTHORIZED = 401

CUSTOM_ISSUE_TYPE_NAME = f"{SCCE_NAME} Cloud Posture Ticket"
CUSTOM_ISSUE_TYPE_DESCRIPTION = (
    "This ticket type is used by SOAR to sync your SCC findings, SOAR cases"
    " and Jira issues."
)
CUSTOM_ISSUE_TYPE_SCREEN_NAME = f"{CUSTOM_ISSUE_TYPE_NAME} Screen"
CUSTOM_ISSUE_TYPE_SCREEN_SCHEME_NAME = f"{CUSTOM_ISSUE_TYPE_SCREEN_NAME} Scheme"

SCCE_PROJECT_KEY = "SCCE"
SCCE_PROJECT_NAME = f"{SCCE_NAME} Project"
SCCE_PROJECT_DESCRIPTION = (
    "This is a project to track and resolve posture finding cases."
)
SCCE_WORKFLOW_NAME = f"{SCCE_PROJECT_NAME} - Workflow"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
