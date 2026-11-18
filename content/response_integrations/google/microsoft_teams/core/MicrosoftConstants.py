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
INTEGRATION_NAME = "MicrosoftTeams"
INTEGRATION_DISPLAY_NAME = "Microsoft Teams"
WAIT_REPLY_SCRIPT = f"{INTEGRATION_NAME} - Wait For Reply"
SEND_MESSAGE_ACTION = f"{INTEGRATION_NAME} - Send Message"
WAIT_FOR_REPLY_ACTION = f"{INTEGRATION_NAME} - Wait For Reply"
LIST_USERS_ACTION = f"{INTEGRATION_NAME} - List Users"
LIST_TEAMS_ACTION = f"{INTEGRATION_NAME} - List Teams"
LIST_CHANNELS_ACTION = f"{INTEGRATION_NAME} - List Channels"
GET_USER_DETAILS_ACTION = f"{INTEGRATION_NAME} - Get User Details"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
GET_TEAM_DETAILS_ACTION = f"{INTEGRATION_NAME} - Get Team Details"
GENERATE_TOKEN_ACTION = f"{INTEGRATION_NAME} - Generate Token"
GET_AUTHORIZATION_ACTION = f"{INTEGRATION_NAME} - Get Authorization"
SEND_CHAT_MESSAGE_ACTION = f"{INTEGRATION_NAME} - Send Chat Message"
SEND_USER_MESSAGE_ACTION = f"{INTEGRATION_NAME} - Send User Message"
LIST_CHATS_ACTION = f"{INTEGRATION_NAME} - List Chats"
CREATE_CHANNEL_ACTION = f"{INTEGRATION_NAME} - Create Channel"
DELETE_CHANNEL_ACTION = f"{INTEGRATION_NAME} - Delete Channel"
ADD_USERS_TO_CHANNEL_ACTION = f"{INTEGRATION_NAME} - Add Users To Channel"
REMOVE_USERS_FROM_CHANNEL_ACTION = f"{INTEGRATION_NAME} - Remove Users From Channel"
CREATE_CHAT_ACTION = f"{INTEGRATION_NAME} - Create Chat"
SEND_MESSAGE_REPLY_ACTION = f"{INTEGRATION_NAME} - Send Message Reply"
SEND_CARD_MESSAGE_ACTION = f"{INTEGRATION_NAME} - Send Card Message"
UPDATE_CARD_ACTION = f"{INTEGRATION_NAME} - Update Card"
SEND_CASE_CARD_ACTION = f"{INTEGRATION_NAME} - Send Case Card"
UPDATE_CASE_CARD_ACTION = f"{INTEGRATION_NAME} - Update Case Card"
TOKEN_RENEWAL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Refresh Token Renewal Job"

CHECK_FIRST_REPLY = "Check First Reply"
WAIT_TILL_TIMEOUT = "Wait Till Timeout"
TIMEOUT_BUFFER_IN_SECONDS = 45
DEFAULT_TIMEOUT = 300
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

CHAT_TYPES = {
    "All": None,
    "Group Chat": "group",
    "Meeting Chat": "meeting",
    "One on One Chat": "oneOnOne",
}

EQUAL_FILTER = "Equal"
CONTAINS_FILTER = "Contains"
NOT_SPECIFIED_FILTER = "Not Specified"

FILTER_KEY_TOPIC = "Topic"
FILTER_KEY_MEMBER_EMAIL = "Member Email"
FILTER_KEY_MEMBER_DISPLAY_NAME = "Member Display Name"
FILTER_KEY_SELECT_ONE_FILTER = "Select One"
PRIVATE_MEMBERSHIP_TYPE = "private"

ASYNC_MESSAGE = "Waiting for reply..."
REPLIES_EXP_REPLY_MESSAGE = (
    "Message with ID {message_id} in channel '{channel_name}' of "
    "team '{team_name}' has expected reply '{expected_reply}'!"
)
REPLIES_WO_EXP_REPLY_MESSAGE = (
    "Successfully retrieved replies related to the message with "
    "ID {message_id} in channel '{channel_name}' of team {team_name}."
)
TIMEOUT_MESSAGE = (
    "Expected reply '{expected_reply}' was not seen to message with "
    "ID '{message_id}' in channel '{channel_name}' of team '{team_name}'"
)

TIMEOUT_MESSAGE_NO_REPLY = (
    "No reply was received to a message with ID '{message_id}' in "
    "channel '{channel_name}' of team '{team_name}'. Please try again."
)

DEFAULT_CONTENT_TYPE = "text"
DEFAULT_API_ROOT = "https://graph.microsoft.com"
DEFAULT_LOGIN_API_ROOT = "https://login.microsoftonline.com"

DESTINATION_CHANNEL = "Channel"
DESTINATION_CHAT = "Chat"

ADAPTIVE_CARD_CONTENT_TYPE = "application/vnd.microsoft.card.adaptive"
ADAPTIVE_CARD_TYPE = "AdaptiveCard"
ADAPTIVE_CARD_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
ADAPTIVE_CARD_DEFAULT_VERSION = "1.5"
ADAPTIVE_CARD_MAX_VERSION = (1, 5)
BOT_FRAMEWORK_MESSAGE_TYPE = "message"
CARD_SOFT_SIZE_LIMIT_BYTES = 28 * 1024

ACTION_TYPE_PREFIX = "Action."
ACTION_OPEN_URL = "Action.OpenUrl"
ACTION_SUBMIT = "Action.Submit"
ACTION_EXECUTE = "Action.Execute"
ACTION_SHOW_CARD = "Action.ShowCard"
REJECTED_CARD_ACTIONS = {
    ACTION_SUBMIT: "requires a bot to handle the callback",
    ACTION_EXECUTE: "requires a bot to handle the callback",
    ACTION_SHOW_CARD: "is not supported by the Microsoft Graph API",
}
INPUT_TYPE_PREFIX = "Input."
UNSAFE_URL_SCHEMES = ("javascript:", "data:", "file:", "vbscript:")

CASE_CARD_MAX_ALERTS = 3
CASE_CARD_MAX_ACTIVITIES = 4
CASE_CARD_MAX_TEXT_LENGTH = 150
CASE_CARD_MAX_ACTIVITY_LENGTH = 120
CASE_CARD_MAX_TAGS = 10
CASE_PRIORITY_LABELS = {
    -1: "Informational",
    40: "Low",
    60: "Medium",
    80: "High",
    100: "Critical",
}
CASE_PRIORITY_STYLES = {
    "Informational": ("accent", "Accent"),
    "Low": ("good", "Good"),
    "Medium": ("warning", "Warning"),
    "High": ("attention", "Attention"),
    "Critical": ("attention", "Attention"),
}
CASE_STATUS_LABELS = {0: "New", 1: "Open", 2: "Closed", 4: "Merged"}
