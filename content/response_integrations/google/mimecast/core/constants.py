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
INTEGRATION_NAME = "Mimecast"
INTEGRATION_DISPLAY_NAME = "Mimecast"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
REJECT_MESSAGE_ACTION = f"{INTEGRATION_NAME} - Reject Message"
RELEASE_MESSAGE_ACTION = f"{INTEGRATION_NAME} - Release Message"
REPORT_MESSAGE_ACTION = f"{INTEGRATION_NAME} - Report Message"
PERMIT_SENDER_ACTION = f"{INTEGRATION_NAME} - Permit Sender"
BLOCK_SENDER_ACTION = f"{INTEGRATION_NAME} - Block Sender"
ADVANCED_ARCHIVE_SEARCH_ACTION = f"{INTEGRATION_NAME} - Advanced Archive Search"
SIMPLE_ARCHIVE_SEARCH_ACTION = f"{INTEGRATION_NAME} - Simple Archive Search"
CREATE_BLOCK_SENDER_POLICY_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Create Block Sender Policy"
)

ENDPOINTS = {
    "ping": "/api/account/get-account",
    "email_search": "/api/message-finder/search",
    "get_email_details": "/api/message-finder/get-message-info",
    "release_message": "/api/message-finder/release-held-email-to-sandbox",
    "release_message_sandbox": "/api/message-finder/release-held-email-to-sandbox",
    "report_message": "/api/message-finder/report-message",
    "reject_message": "/api/message-finder/reject-held-email",
    "manage_sender": "/api/managedsender/permit-or-block-sender",
    "execute_query": "/api/archive/search",
    "get_token": "/oauth/token",
    "hold_release": "/api/gateway/hold-release",
    "hold_reject": "/api/gateway/hold-reject",
    "hold_message_list": "/api/gateway/get-hold-message-list",
    "create_block_sender_policy": "/api/policy/blockedsenders/create-policy",
    "get_message_details": "/api/gateway/message/get-message-detail",
    "get_file": "/api/gateway/message/get-file",
    "download_attachment": "/api/archive/get-message-part"
}

REPORT_TYPES = {"Malware": "malware", "Spam": "spam", "Phishing": "phishing"}

SELECT_ONE_REASON = "select_one"

REJECTION_REASONS = {
    "Inappropriate Communication": "inappropriate_communication",
    "Confidential Information": "confidential_information",
    "Restricted Content": "disapproves_of_content",
    "Against Email Policy": "against_email_policies",
    "Select One": "select_one",
}

HEADERS = {
    "Authorization": None,
    "x-mc-app-id": None,
    "x-mc-date": None,
    "x-mc-req-id": None,
    "Content-Type": "application/json",
}

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Message Tracking Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "Mimecast"
DEVICE_PRODUCT = "Mimecast"
DEFAULT_RULE_GEN = "Mimecast Email"

FILTER_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SEVERITY_MAP = {"negligible": -1, "low": 40, "medium": 60, "high": 80}

SEVERITIES = ["negligible", "low", "medium", "high"]
POSSIBLE_STATUSES = [
    "delivery",
    "held",
    "accepted",
    "bounced",
    "deferred",
    "rejected",
    "archived",
]
POSSIBLE_ROUTES = ["internal", "outbound", "inbound"]

DEFAULT_LIMIT = 50

TIMEFRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 24 Hours": {"hours": 24},
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Custom": "custom",
}
ALERT_ID_KEY = "message_id"
ADVANCE_TRACKING_FIELDS = ["to", "from"]

RESPONSE: list[str] = ["No Action", "Block Sender"]
EXTRACTED_DATA: list[str] = ["Both", "From Envelope", "From Headers"]
SENDER_RECIPIENT_TYPE: list[str] = [
    "Everyone",
    "Email Address",
    "Email Domain",
    "Header Display Name",
    "Internal Addresses",
    "External Addresses",
]
EMAIL_DOMAIN: str = "Email Domain"
EMAIL_ADDRESS: str = "Email Address"
HEADER_DISPLAY_NAME: str = "Header Display Name"
VALID_SENDER_RECIPIENT_TYPES: list[str] = [
    EMAIL_DOMAIN,
    EMAIL_ADDRESS,
    HEADER_DISPLAY_NAME
]
SENDER_REQUIRED_ERROR: str = (
    "Sender is required when Sender Type is Email Domain, "
    "Email Address, or Header Display Name."
)
RECIPIENT_REQUIRED_ERROR: str = (
    "Recipient is required when Recipient Type is Email Domain, "
    "Email Address, or Header Display Name."
)
