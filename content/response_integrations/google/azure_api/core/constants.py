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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

INTEGRATION_IDENTIFIER: str = "AzureApi"
INTEGRATION_DISPLAY_NAME: str = "Azure API"

# Scripts names
PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"
GET_AUTHORIZATION_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Get Authorization"
GENERATE_TOKEN_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Generate Token"
EXECUTE_HTTP_REQUEST_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Execute HTTP Request"
TOKEN_RENEWAL_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Refresh Token Renewal Job"

# Default values
GRAPH_API_VERSION: str = "v1.0"
DEFAULT_LOGIN_API_ROOT: str = "https://login.microsoftonline.com"
DEFAULT_GRAPH_API_ROOT: str = "https://graph.microsoft.com"
DEFAULT_SCOPE: str = "https://graph.microsoft.com/.default"
DEFAULT_VERIFY_SSL: bool = True
DEFAULT_REQUEST_TIMEOUT: int = 120
ERROR_STATUS_CODE_THRESHOLD: int = 400

FIELDS_TO_RETURN_POSSIBLE_VALUES: list[str] = [
    "response_data",
    "redirects",
    "response_code",
    "response_cookies",
    "response_headers",
    "apparent_encoding",
]

FILE_NAME: str = "attachment"
ZIP_FILE_EXTENSION: str = ".zip"
ZIP_FILE_PASSWORD: bytes = b"infected"

# Endpoints
ENDPOINTS: Mapping[str, str] = {
    "bearer_token_url": "{tenant_id}/oauth2/v2.0/token",
    "authorize_url": "{tenant_id}/oauth2/v2.0/authorize",
}

# Magic strings
PARAM_LOGIN_API_ROOT: str = "Microsoft Login API Root"
PARAM_GRAPH_API_ROOT: str = "Microsoft Graph API Root"
PARAM_TENANT_ID: str = "Tenant ID"
PARAM_CLIENT_ID: str = "Client ID"
PARAM_CLIENT_SECRET: str = "Client Secret"
PARAM_VERIFY_SSL: str = "Verify SSL"
PARAM_SCOPE: str = "Scopes"
PARAM_REFRESH_TOKEN: str = "Refresh Token"
PARAM_REDIRECT_URL: str = "Redirect URL"
PARAM_AUTHORIZATION_URL: str = "Authorization URL"
PARAM_OAUTH_SCOPES: str = "Oauth Scopes"
PARAM_RELATIVE_URL: str = "Relative URL"
PARAM_METHOD: str = "Method"
PARAM_BODY: str = "Body"

OAUTH_SCOPE: list[str] = [
    "mail.read",
    "mail.send",
    "mail.readwrite",
    "mailboxsettings.read",
    "mailboxsettings.readwrite",
    "user.read",
    "directory.read.all",
    "presence.read.all",
    "offline_access",
]
RESPONSE_TYPE_CODE: str = "code"
RESPONSE_MODE_QUERY: str = "query"
GRANT_TYPE_AUTH_CODE: str = "authorization_code"
GRANT_TYPE_REFRESH_TOKEN: str = "refresh_token"
GRANT_TYPE_CLIENT_CREDENTIALS: str = "client_credentials"
TOKEN_PAYLOAD_FROM_SECRET: Mapping[str, str] = {
    "client_id": "",
    "client_secret": "",
    "refresh_token": "",
    "grant_type": GRANT_TYPE_REFRESH_TOKEN,
    "scope": "",
}

BROWSE_AUTH_LINK_MESSAGE: str = "Browse to this authorization link"
AUTH_URL_GENERATED_MESSAGE: str = "Authorization URL generated successfully."
INVALID_AUTH_URL_MESSAGE: str = (
    "Failed to generate a token because the authorization URL that you provided is "
    "incorrect. The 'code' parameter is missing."
)
UNABLE_TO_GENERATE_TOKEN_MESSAGE: str = "Unable to generate the refresh token with the provided authorization URL."
TOKEN_GENERATED_MESSAGE: str = "Successfully fetched the refresh token: \n{}\n"
REQUEST_EXECUTED_MESSAGE: str = "Request executed successfully."
REQUEST_FAILED_MESSAGE: str = "Failed to execute request. Error: {}"
PING_SUCCESS_MESSAGE: str = "Successfully connected to the Azure API."
FILE_NAME: str = "attachment"
ZIP_FILE_EXTENSION: str = ".zip"
ZIP_FILE_PASSWORD: str = "infected"
