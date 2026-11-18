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

"""Constants for the SAP ERP integration."""

from __future__ import annotations

# Integration identifiers
INTEGRATION_IDENTIFIER: str = "SapErp"
INTEGRATION_DISPLAY_NAME: str = "SAP ERP"

# Script names
PING_SCRIPT_NAME: str = "Ping"
LOCK_SAP_USER_SCRIPT_NAME: str = "Lock SAP User"
DELETE_USER_SESSION_SCRIPT_NAME: str = "Delete User Session"
ACTIVATE_AUDIT_LOG_SCRIPT_NAME: str = "Activate Audit Log"

# Integration configuration parameter names
CLOUD_RUN_URL_PARAM: str = "Cloud Run Service URL"
SERVICE_ACCOUNT_JSON_PARAM: str = "Service Account JSON"
WORKLOAD_IDENTITY_EMAIL_PARAM: str = "Workload Identity Email"
VERIFY_SSL_PARAM: str = "Verify SSL"

# Action parameter names
SAP_INSTANCE_NAME_PARAM: str = "SAP Instance Name"
SAP_CLIENT_NUMBER_PARAM: str = "SAP Client Number"
SAP_USERNAME_PARAM: str = "SAP Username"

# Gateway RFC function IDs
USER_LOCK_FUNCTION_ID: str = "USER_LOCK"
DELETE_USER_SESSION_FUNCTION_ID: str = "DELETE_USER_SESSION"
ACTIVATE_AUDIT_LOG_FUNCTION_ID: str = "ACTIVATE_AUDIT_LOG"

# OAuth scope for Workload Identity impersonation
CLOUD_PLATFORM_SCOPE: str = "https://www.googleapis.com/auth/cloud-platform"

# Timeouts and validation constants
DEFAULT_TIMEOUT_SECONDS: int = 60
PING_TIMEOUT_SECONDS: int = 30
SAP_CLIENT_LENGTH: int = 3

# HTTP statuses for Ping connectivity check
IAM_DENIED_STATUSES: frozenset[int] = frozenset({401, 403})
# GatewayHttpHandler only accepts POST, so a healthy gateway answers GET with
# HTTP 405 {"error": "Only POST requests are supported."}.
HEALTHY_STATUSES: frozenset[int] = frozenset({200, 405})
