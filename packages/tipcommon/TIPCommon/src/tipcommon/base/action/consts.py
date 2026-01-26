# Copyright 2025 Google LLC
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

from .data_models import ExecutionState

EXECUTION_STATE = {
    ExecutionState.COMPLETED: "Completed",
    ExecutionState.IN_PROGRESS: "In Progress",
    ExecutionState.FAILED: "Failed",
    ExecutionState.TIMED_OUT: "Timed Out",
}

PARAMETER_EXTRACTION_ERR_MSG = (
    "Failed to get the definition files for all the actions that are "
    "configured in the current environment!\n"
    "HTTPError stacktrace: {error}\n"
)
CONFIG_PARAMETER_EXTRACTION_ERR_MSG = (
    "Failed to get the full-details file of the integration!\nHTTPError stacktrace: {error}\n"
)
DEF_FILE_PARSE_ERROR_MSG = (
    'Failed to parse the "get env action-def" response Json\nJSONDecoder stacktrace: {error}\n'
)
CONFIG_DEF_FILE_PARSE_ERROR_MSG = (
    'Failed to parse the "get full-details" response Json\nJSONDecoder stacktrace: {error}\n'
)
ENTITY_OG_ID_ATTR = "original_identifier"
ACTION_DEF_NAME_KEY = "name"
ADD_TO_CASE_RESULT_MSG = "Adding {action_type} to case result\n"
ADD_TO_CASE_RESULT_ERR_MSG = "Failed to send {action_type} to case result, Error: {error0}\n"
SDK_WRAPPER_ERR_MSG = "Failed to execute an SDK wrapper method, Error: {error}\n"
