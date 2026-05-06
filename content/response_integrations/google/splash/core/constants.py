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

INTEGRATION_NAME = "Splash"
INTEGRATION_DISPLAY_NAME = "Splash"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_ACTION = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"

ENDPOINTS = {"ping": "/_ping", "get_data": "/render.json"}

CA_CERTIFICATE_FILE_PATH = "cacert.pem"
HTTP_SCHEMA = "http://"
HTTPS_SCHEMA = "https://"
