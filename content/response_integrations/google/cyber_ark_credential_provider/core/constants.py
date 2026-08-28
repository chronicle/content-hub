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


INTEGRATION_NAME: str = "CyberArkCredentialProvider"

RUN_CLI_APP_PASSWORD_SDK_COMMAND_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Run CLI Application Password SDK Command"
)
GET_APPLICATION_PASSWORD_VALUE_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Get Application Password Value"
)
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"

TEST_COMMAND: str = "-?"

PASSWORD_OUTPUT_FIELD: str = "Password"
