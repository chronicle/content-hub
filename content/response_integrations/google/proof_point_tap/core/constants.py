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
from collections.abc import Mapping, Sequence


INTEGRATION_NAME: str = "ProofPointTAP"
INTEGRATION_DISPLAY_NAME: str = "ProofPoint TAP"

PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
GET_CAMPAIGN_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Campaign"
DECODE_URL_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Decode URL"
SEARCH_EVENTS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Search Events"
LIST_CAMPAIGNS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - List Campaigns"
GET_THREAT_FORENSICS: str = f"{INTEGRATION_NAME} - Get Threat Forensics"

HEADERS: Mapping[str, str] = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}
ENDPOINTS: Mapping[str, str] = {
    "ping": "/v2/campaign/{campaign_id}",
    "get_campaign": "/v2/campaign/{campaign_id}",
    "get_forensics": "/v2/forensics",
    "decode_urls": "/v2/url/decode",
    "search_events": (
        "/v2/siem/{event_type}?interval={start_time}/{end_time}&format=json"
    ),
    "list_campaigns": "/v2/campaign/ids?interval={start_time}/{end_time}&format=json",
    "get_threat": (
        "/v2/forensics?threatId={threat_id}"
        "&includeCampaignForensics={includeCampaignForensics}"
    ),
}
LIMIT_DEFAULT: int = 50
MAX_LIMIT: int = 1000

CAMPAIGNS_TABLE_NAME: str = "Campaign Details"
CAMPAIGN_EVIDENCE_TABLE_NAME: str = "Campaign {id} Evidence"

API_EVENT_TYPE_MAPPING: Mapping[str, str] = {
    "All": "all",
    "Clicks Blocked": "clicks/blocked",
    "Clicks Permitted": "clicks/permitted",
    "Messages Delivered": "messages/delivered",
    "Messages Blocked": "messages/blocked",
    "Issues": "issues",
}

THREAT_STATUS_MAPPING: Mapping[str, str] = {
    "Active": "active",
    "Cleared": "cleared",
    "False Positive": "falsePositive",
}

TIMEFRAME_TO_HOURS: Mapping[str, int] = {
    "Last Hour": 1,
    "Last 6 Hours": 6,
    "Last 24 Hours": 24,
    "Last Week": 167,
}
POSSIBLE_EVENT_TYPE_VALUES: Sequence[str] = [
    "All",
    "Clicks Blocked",
    "Clicks Permitted",
    "Messages Delivered",
    "Messages Blocked",
    "Issues",
]
POSSIBLE_THREAT_STATUS_VALUES: Sequence[str] = [
    "Select One",
    "Active",
    "Cleared",
    "False Positive",
]
POSSIBLE_TIMEFRAME_TO_HOURS_VALUES: Sequence[str] = [
    "Last Hour",
    "Last 6 Hours",
    "Last 24 Hours",
    "Last Week",
    "Custom",
]

EVENT_TYPE_MAPPING: Mapping[str, str] = {
    "All": ["clicksPermitted", "clicksBlocked", "messagesDelivered", "messagesBlocked"],
    "Clicks Blocked": ["clicksBlocked"],
    "Clicks Permitted": ["clicksPermitted"],
    "Messages Delivered": ["messagesDelivered"],
    "Messages Blocked": ["messagesBlocked"],
    "Issues": ["clicksPermitted", "messagesDelivered"],
}
