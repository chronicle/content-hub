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
import json
import pathlib

from TIPCommon.types import SingleJson

from ..core.datamodels import (
    Attachment,
    HoldMessage,
    Message,
    MessageDetails,
)
from ..core.MimecastParser import MimecastParser
from integration_testing.common import get_def_file_content


class IdNotFoundError(Exception):
    """Generic error for when an ID cannot be found"""


class AlreadyExistsError(Exception):
    """Generic error for when an ID already exists"""

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

MOCK_MESSAGE_DATA: SingleJson = MOCK_DATA.get("message_data")
MOCK_MESSAGE_DETAILS_DATA: SingleJson = MOCK_DATA.get("message_details_data")
MOCK_HOLD_MESSAGE_DATA: SingleJson = MOCK_DATA.get("hold_message_data")
MOCK_ATTACHMENT_DATA: SingleJson = MOCK_DATA.get("attachment_data")
BLOCK_SENDER_POLICY_ERROR_JSON: SingleJson = MOCK_DATA.get("block_sender_policy_error")
MOCK_INVALID_CLIENT_CREDENTIALS_JSON: SingleJson = MOCK_DATA.get(
    "invalid_client_credentials"
)
MOCK_VALID_OAUTH_TOKEN_JSON: SingleJson = MOCK_DATA.get("valid_oauth_token")
DOWNLOAD_ATTACHMENT_URL: list[SingleJson] = MOCK_DATA.get("download_attachment_url")

MESSAGE: Message = MimecastParser().build_message_object(MOCK_MESSAGE_DATA)

MESSAGE_DETAILS: MessageDetails = MimecastParser().build_message_details_object(
    MOCK_MESSAGE_DETAILS_DATA
)

HOLD_MESSAGE: HoldMessage = MimecastParser().build_hold_message_objects(
    MOCK_HOLD_MESSAGE_DATA
)

ATTACHMENT: Attachment = MimecastParser().build_attachment_object(MOCK_ATTACHMENT_DATA)
