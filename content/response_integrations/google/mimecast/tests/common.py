from __future__ import annotations
import json
from integration_testing.common import get_def_file_content
import pathlib

from TIPCommon.types import SingleJson

from mimecast.core.datamodels import (
    Attachment,
    HoldMessage,
    Message,
    MessageDetails,
)
from mimecast.core.MimecastParser import MimecastParser
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
