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
INTEGRATION_NAME = "ThreatConnect"

FAILURE_STATUS = "failure"

# Available Indicator Types - apiBranch
ADDRESS = "addresses"
FILE = "files"
HOST = "hosts"
URL = "urls"

# Indicator fields list
FIELDS_LIST = {
    "tags",
    "attributes",
    "securityLabels",
    "groups",
    "indicators",
    "victimAssets",
    "owners",
    "observations",
    "observationCount",
    "victims",
}

# 'name': 'apiBranch'
GROUPS_TYPES_MAP = {
    "Adversary": "adversaries",
    "Campaign": "campaigns",
    "Incident": "incidents",
    "Event": "events",
    "Signature": "signatures",
    "Threat": "threats",
    "Email": "emails",
    "Document": "documents",
    "Report": "reports",
}

# Query format
INDICATOR_REQUEST_URI = "/v2/indicators/{indicatorType}/{indicator}"
INDICATOR_OWNERS_REQUEST_URI = "/v2/indicators/{indicatorType}/{indicator}/owners"
GROUP_REQUEST_URI = "/v2/groups/{groupType}/{groupId}"
GROUPS = "/v2/groups"
