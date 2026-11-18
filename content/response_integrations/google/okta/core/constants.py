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
INTEGRATION_IDENTIFIER: str = "Okta"
ENDPOINTS: dict[str, str] = {"send_itp_signal": "/security/api/v1/security-events"}
SEND_ITP_SIGNAL_SCRIPT_NAME: str = "Okta - Send ITP Signal To Okta"
CLEAR_OKTA_USER_SESSION_SCRIPT_NAME: str = "Clear Okta User Session"
SEND_ITP_SIGNAL_ERROR_MESSAGE: str = (
    f"Error executing action {SEND_ITP_SIGNAL_SCRIPT_NAME}."
)
SEVERITY_TYPE: list[str] = ["Low", "Medium", "High"]
NOT_FOUND_STATUS_CODE: list[int] = [400, 404]
OAUTH2_AUTH_METHOD: str = "oauth2"
API_TOKEN_AUTH_METHOD: str = "api_token"
BEGIN_MARKER: str = "-----BEGIN"
END_MARKER: str = "-----END"
BEGIN_PRIVATE_KEY: str = "-----BEGIN PRIVATE KEY-----"
END_PRIVATE_KEY: str = "-----END PRIVATE KEY-----"
