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
INTEGRATION_NAME = "McAfeeMvisionEPOV2"
INTEGRATION_DISPLAY_NAME = "McAfee Mvision ePO V2"
DEFAULT_SCOPES = "epo.device.r epo.device.w epo.evt.r epo.taggroup.r epo.taggroup.w epo.tags.r epo.tags.w mi.user.investigate soc.inv.ade"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ADD_TAG_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Tag To Device"
REMOVE_TAG_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Tag From Device"
ENRICH_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Endpoint"
ENRICHMENT_PREFIX = "MMV_EPO_V2"
LIST_TAGS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Tags"
LIST_DEVICES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Devices"
PER_PAGE_LIMIT = 100
DEFAULT_LIMIT_TAGS = 100
DEFAULT_LIMIT_DEVICES = 100
DEFAULT_VENDOR = "McAfee"
DEFAULT_PRODUCT = "McAfeeMVisionEPO"
