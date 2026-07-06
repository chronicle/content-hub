from __future__ import annotations
from typing import MutableMapping

import dataclasses
from TIPCommon.types import SingleJson
from Integrations.MicrosoftGraphMailDelegated.Managers.datamodels import (
    MicrosoftGraphEmail,
    MicrosoftGraphFolder,
    MicrosoftGraphAttachment,
    MicrosoftGraphFileAttachment,
    UserOOFSettings,
)

from Tests.mocks.product import MockProduct


@dataclasses.dataclass
class MicrosoftGraphMailDelegated(MockProduct):

    def __init__(self):
        self._emails: MutableMapping[str, MicrosoftGraphEmail] = {}
        self._folders: MutableMapping[str, MicrosoftGraphEmail] = {}
        self._user: SingleJson = None
        self._attachments: MutableMapping[str, MicrosoftGraphAttachment] = {}
        self._file_attachments: MutableMapping[str, MicrosoftGraphFileAttachment] = {}
        self._user_oof_settings: str = None
        self._replies: MutableMapping[str, MicrosoftGraphEmail] = {}

    def get_email(self, email_id: str) -> MicrosoftGraphEmail:
        return self._emails[email_id]

    def get_emails(self) -> list[MicrosoftGraphEmail]:
        return list(self._emails.values())

    def get_user(self) -> SingleJson:
        return self._user

    def get_folder(self, folder_id: str) -> MicrosoftGraphFolder:
        return self._folders[folder_id]

    def get_folders(self) -> list[MicrosoftGraphFolder]:
        return list(self._folders.values())

    def get_attachment(self, attachment_id: str) -> MicrosoftGraphAttachment:
        return self._attachments[attachment_id]

    def get_attachments(self) -> list(MicrosoftGraphAttachment):
        return list(self._attachments.values())

    def get_file_attachment(self, attachment_id: str) -> MicrosoftGraphFileAttachment:
        return self._file_attachments[attachment_id]

    def get_user_oof_settings(self) -> UserOOFSettings:
        return self._user_oof_settings

    def add_email(self, email: MicrosoftGraphEmail) -> None:
        self._emails[email.id] = email

    def add_folder(self, folder: MicrosoftGraphFolder) -> None:
        self._folders[folder.id] = folder

    def add_attachment(self, attachment: MicrosoftGraphAttachment) -> None:
        self._attachments[attachment.id] = attachment

    def add_file_attachment(self, attachment: MicrosoftGraphFileAttachment) -> None:
        self._file_attachments[attachment.id] = attachment

    def add_user_oof_settings(self, user_oof_settings: UserOOFSettings) -> None:
        self._user_oof_settings: UserOOFSettings = user_oof_settings

    def add_user(self, user: SingleJson) -> None:
        self._user: SingleJson = user

    def delete_email(self, email_id: str) -> None:
        del self._emails[email_id]

    def mark_email_as_junk(self, email_id: str) -> MicrosoftGraphEmail:
        email: MicrosoftGraphEmail = self._emails[email_id]
        email.moveToJunk = True
        return email

    def mark_email_as_not_junk(self, email_id: str) -> MicrosoftGraphEmail:
        email: MicrosoftGraphEmail = self._emails[email_id]
        email.moveToInbox = True
        return email
