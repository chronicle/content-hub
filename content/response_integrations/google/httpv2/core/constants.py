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
PROVIDER_NAME = "HTTP V2"
INTEGRATION_NAME = "HTTPV2"

# Action names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
EXECUTE_HTTP_REQUEST_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute HTTP Request"


API_REQUEST_METHODS_MAPPING = {
    "GET": "GET",
    "POST": "POST",
    "PUT": "PUT",
    "PATCH": "PATCH",
    "DELETE": "DELETE",
    "HEAD": "HEAD",
    "OPTIONS": "OPTIONS",
}

AUTH_METHOD = {
    "BASIC": "basic",
    "API_KEY": "api_key",
    "ACCESS_TOKEN": "access_token",
    "NO_AUTH": None,
}

DEFAULT_REQUEST_TIMEOUT = 120

FIELDS_TO_RETURN_POSSIBLE_VALUES = [
    "response_data",
    "redirects",
    "response_code",
    "response_cookies",
    "response_headers",
    "apparent_encoding",
]

JSON_DATA_TYPE = "application/json"
ACCESS_TOKEN_PLACEHOLDER = "{{integration.token}}"
CA_CERTIFICATE_FILE_NAME = "cacert.pem"
FILE_NAME = "attachment"
ZIP_FILE_EXTENSION = ".zip"
ZIP_FILE_PASSWORD = b"infected"
