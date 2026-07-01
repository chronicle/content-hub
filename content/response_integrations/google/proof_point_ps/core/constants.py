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

PROVIDER = "ProofPointPS"

# Headers used for session requests
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0"
    ),
}

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Action Names
PING_ACTION_NAME = "ProofPointPS - Ping"
ENRICH_ACTION_NAME = "ProofPoint - Enriched Entities"
SEARCH_ACTION_NAME = "ProofPointPS - Search Quarantined Emails"
RELEASE_ACTION_NAME = "ProofPointPS - Release Quarantined Email"
RESUBMIT_ACTION_NAME = "ProofPointPS - Resubmit Quarantined Email"
FORWARD_ACTION_NAME = "ProofPointPS - Forward Quarantined Email"
MOVE_ACTION_NAME = "ProofPointPS - Move Quarantined Email"
DELETE_ACTION_NAME = "ProofPointPS - Delete Quarantined Email"
DOWNLOAD_ACTION_NAME = "ProofPointPS - Download Quarantined Email"

# Endpoints
QUARANTINE_ENDPOINT = "/rest/v1/quarantine"
