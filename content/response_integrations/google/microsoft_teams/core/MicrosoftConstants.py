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
