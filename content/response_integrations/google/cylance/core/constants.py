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
PROVIDER_NAME = "Cylance"

# Actions
GET_THREAT_DOWNLOAD_LINK = f"{PROVIDER_NAME} - Get Threat Download Link"

ENDPOINTS = {"get_threat_download_link": "/threats/v2/download/{hash}"}
PARAMETERS_DEFAULT_DELIMITER = ","
ENRICH_PREFIX = "Cylance"
