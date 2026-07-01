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

HEADERS: dict[str, str] = {"Content-Type": "application/json"}
FORM_URL_ENCODED_HEADERS: dict[str, str] = {
    "Content-Type": "application/x-www-form-urlencoded"
}


EXCEEDED_RATE_LIMIT_STATUS_CODE: int = 429
UNAUTHORIZED_STATUS_CODE: int = 401
BAD_REQUEST_STATUS_CODE: int = 400
FORBIDDEN_STATUS_CODE: int = 403
BATCH_SIZE: int = 100

BASE_URL: str = "{0}/api/v1"

ADD_WHITE_LIST_KEY: str = "Add"
REMOVE_WHITE_LIST_KEY: str = "Remove"

OAUTH_TOKEN_ENDPOINT: str = "{0}/oauth2/v1/token"
OAUTH_AUDIENCE: str = "https://api.zscaler.com"

INVALID_CREDENTIALS_ERROR: str = (
    "Unable to establish a connection. Please verify that your API Root "
    "URL is correct and the server is reachable."
)
OAUTH_AUTH_FAILED_ERROR: str = (
    "Please verify that your Client ID, Client Secret and Login API Root are correct."
)
LEGACY_AUTH_FAILED_ERROR: str = (
    "Please verify that your Login ID, Password, and API Key are correct."
)
GENERIC_AUTH_FAILED_ERROR: str = "Please verify your configured credentials."
MISSING_CREDENTIALS_ERROR: str = (
    "Authentication failed: Provide either full OAuth 2.0 credentials "
    "(Client ID, Client Secret, Login API Root) OR full Legacy credentials "
    "(Login ID, Api Key, Password)."
)
PROVIDER_NAME: str = "Zscaler"

ADD_TO_BLACKLIST_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Add To Blacklist"
REMOVE_FROM_BLACKLIST_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Remove from blacklist"
ADD_TO_WHITELIST_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Add to whitelist"
REMOVE_FROM_WHITELIST_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Remove from whitelist"
LOOKUP_URL_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Lookup URL"
GET_BLACKLIST_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Get Blacklist"
GET_WHITELIST_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Get Whitelist"
GET_SANDBOX_REPORT_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Get Sandbox Report"
GET_URL_CATEGORIES_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Get URL Categories"
PING_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Ping"
