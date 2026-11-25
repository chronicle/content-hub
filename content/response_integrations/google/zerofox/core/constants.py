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
INTEGRATION_NAME: str = "Zerofox"
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
ADD_NOTE_TO_ALERT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add Note To Alert"
ADD_EVIDENCE_TO_ALERT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add Evidence To Alert"
CLOSE_ALERT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Close Alert"
REQUEST_TAKEDOWN_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Request Takedown"

ENDPOINTS: dict[str, str] = {
    "get_alert": "/1.0/alerts/?limit=1",
    "add_note": "/1.0/alerts/{alert_id}/append_notes/",
    "close_alert": "/1.0/alerts/{alert_id}/close/",
    "request_takedown": "/1.0/alerts/{alert_id}/request_takedown/",
    "add_evidence_to_alert": "/1.0/alerts/{alert_id}/attachments/"
}
INVALID_TOKEN_ERROR: str = "invalid token."
FAILED_TO_TAKE_REQUEST_DOWN_ERR: str = "failed to take action `request_takedown`"
INVALID_ATTACHMENT_ERR: str = "invalid extension for attachment"
