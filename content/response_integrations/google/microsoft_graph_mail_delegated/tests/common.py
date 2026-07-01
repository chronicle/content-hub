from __future__ import annotations

import pathlib
from typing import Collection

from TIPCommon.types import SingleJson
from core.datamodels import (
    MicrosoftGraphAttachment,
    MicrosoftGraphEmail,
    MicrosoftGraphFileAttachment,
    MicrosoftGraphFolder,
    UserOOFSettings,
)
import json
def get_json_file_content(path: pathlib.Path) -> SingleJson:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def set_is_test_run_to(value: bool):
    import TIPCommon.utils
    TIPCommon.utils.is_test_run = lambda: value

class Entity:
    def __init__(self, identifier: str, entity_type):
        self.identifier = identifier
        # Store the enum value if it is an enum, else the raw value
        self.entity_type = getattr(entity_type, 'value', entity_type)
        self.additional_properties = {}
        self.is_enriched = False
    
    def _update_internal_properties(self):
        pass
        
    def to_dict(self):
        return {
            "identifier": self.identifier,
            "entity_type": self.entity_type,
            "additional_properties": self.additional_properties,
            "is_enriched": self.is_enriched
        }

def create_entity(identifier: str, entity_type) -> object:
    return Entity(identifier=identifier, entity_type=entity_type)


VALID_JSON_SUFFIXES: Collection[str] = (
    ".json",
    ".jobdef",
    ".def",
    ".connectordef",
    ".actiondef",
)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_json_file_content(CONFIG_PATH)
MOCK_DATA: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_ERROR_MSG: str = "Failed to authenticate to MicrosoftGraphMailDelegated"

EMAIL_JSON = get_json_file_content(MOCK_DATA).get("get_mail_details")
FOLDER_JSON = get_json_file_content(MOCK_DATA).get("Inbox")["value"][0]
MAILBOX_SETTINGS_JSON = get_json_file_content(MOCK_DATA).get("get_mailbox_settings")
ATTACHMENT_JSON = get_json_file_content(MOCK_DATA).get("get_attachment")
USER_OOF_JSON = get_json_file_content(MOCK_DATA).get("get_ooo_settings")
USER_JSON = get_json_file_content(MOCK_DATA).get("get_user")
FAILED_USER_JSON = get_json_file_content(MOCK_DATA).get("get_user_failed")
OAUTH_TOKEN_JSON = get_json_file_content(MOCK_DATA).get("oauth_token")
USER_FAILED_JSON = get_json_file_content(MOCK_DATA).get("get_user_failed")
FOLDER_FAILED_JSON = get_json_file_content(MOCK_DATA).get("get_folder_failed")
MAIL_FAILED_JSON = get_json_file_content(MOCK_DATA).get("get_mail_failed")
MAILS_FAILED_JSON = get_json_file_content(MOCK_DATA).get("get_mails_failed")
ATTACHMENTS_FAILED_JSON = get_json_file_content(MOCK_DATA).get("get_attachment_failed")
SEARCH_QUERY_DATA = get_json_file_content(MOCK_DATA).get("seach_query_data")


DEFAULT_EMAIL: MicrosoftGraphEmail = MicrosoftGraphEmail(
    raw_data=EMAIL_JSON,
    mailbox_name=CONFIG.get("Default Mailbox"),
    folder_name="Inbox",
    mail_id=EMAIL_JSON.get("id"),
    **EMAIL_JSON,
)
DEFAULT_FOLDER: MicrosoftGraphFolder = MicrosoftGraphFolder(
    raw_data=FOLDER_JSON,
    folder_id=FOLDER_JSON.get("id"),
    display_name="Inbox",
)
DEFAULT_ATTACHMENT: MicrosoftGraphAttachment = MicrosoftGraphAttachment(
    raw_data=ATTACHMENT_JSON, **ATTACHMENT_JSON
)
DEFAULT_FILE_ATTACHMENT: MicrosoftGraphFileAttachment = MicrosoftGraphFileAttachment(
    raw_data=ATTACHMENT_JSON, **ATTACHMENT_JSON
)
DEFAULT_USER_OOF_SETTINGS = UserOOFSettings(raw_data=USER_OOF_JSON)
