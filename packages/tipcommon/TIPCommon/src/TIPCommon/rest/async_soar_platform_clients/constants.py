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


HTTP_CONNECT_TIMEOUT_SECONDS: float = 10.0
HTTP_READ_TIMEOUT_SECONDS: float = 300.0
HTTP_WRITE_TIMEOUT_SECONDS: float = 10.0
HTTP_POOL_TIMEOUT_SECONDS: float = 10.0

HTTP_MAX_KEEP_ALIVE_CONNECTIONS: int = 10
HTTP_MAX_CONNECTIONS: int = 45
DEFAULT_PAGE_SIZE: int = 1000
STATUS_CODE_NO_CONTENT: int = 204
CONNECTOR_INSTANCE_UPDATE_FIELDS: tuple[str, ...] = (
    "name",
    "id",
    "enabled",
    "agent",
    "environment",
    "displayName",
    "description",
    "intervalSeconds",
    "allowList",
    "productFieldName",
    "eventFieldName",
    "timeoutSeconds",
    "integrationVersion",
    "parameters",
    "version",
    "loggingEnabledUntilUnixMs",
)
