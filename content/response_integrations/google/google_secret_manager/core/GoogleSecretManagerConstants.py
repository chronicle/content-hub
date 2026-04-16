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

"""Constants for the Google Secret Manager integration."""

# Integration identifier
INTEGRATION_NAME = "Google Secret Manager"

# Script names
PING_SCRIPT_NAME = "Ping"
SYNC_CREDENTIAL_JOB_SCRIPT_NAME = (
    "Sync Integration Credential Job"
)

# Integration configuration parameter names
SERVICE_ACCOUNT_JSON_PARAM = "Service Account JSON"
PROJECT_ID_PARAM = "Project ID"
WORKLOAD_IDENTITY_EMAIL_PARAM = "Workload Identity Email"

# Secret Manager API defaults
DEFAULT_SECRET_VERSION = "latest"

# Job parameter names
ENVIRONMENT_NAME_PARAM = "Environment Name"
CREDENTIAL_MAPPING_PARAM = "Credential Mapping"

# Credential mapping JSON keys
INTEGRATION_INSTANCES_KEY = "integration_instances"
CONNECTORS_KEY = "connectors"
JOBS_KEY = "jobs"

# API Filter Values
ANY_INTEGRATION_FILTER_VALUE: str = "-"
