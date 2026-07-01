from __future__ import annotations

from base64 import b64encode

from collections.abc import MutableSequence, Sequence

from soar_sdk.SiemplifyDataModel import Attachment
from TIPCommon.types import SingleJson
from .constants import ATTACHMENT_EXTENSION, EML_ATTACHMENT_DESCRIPTION
from .datamodels import (
    MicrosoftGraphAttachment,
    MicrosoftGraphEmail,
    MicrosoftGraphFileAttachment,
    MicrosoftGraphFolder,
    SearchResultData,
    UserOOFSettings,
)


def build_mg_emails(
    alerts_data: Sequence[SingleJson],
    mailbox_name: str,
    folder_name: str,
) -> MutableSequence[MicrosoftGraphEmail]:
    """Get list of MicrosoftGraphEmail object.

    Args:
        alerts_data (Sequence[SingleJson]): json data from api response.
        mailbox_name (str): mailbox name for the mails.
        folder_name (str): folder name for the mails.

    Returns:
        MutableSequence[MicrosoftGraphEmail]: list of MicrosoftGraphEmail object.
    """
    return [
        MicrosoftGraphEmail(
            raw_data=alert_data,
            mailbox_name=mailbox_name,
            folder_name=folder_name,
            mail_id=alert_data.get("id"),
            **alert_data,
        )
        for alert_data in alerts_data
    ]


def build_mg_file_attachments(
    attachments_data: Sequence[SingleJson],
) -> MutableSequence[MicrosoftGraphFileAttachment]:
    """List of MicrosoftGraphFileAttachment attachment objects.

    Args:
        attachments_data (Sequence[SingleJson]): json data for attachment
        api response

    Returns:
        MutableSequence[MicrosoftGraphFileAttachment]: list of
        MicrosoftGraphFileAttachment objects.
    """
    return [
        MicrosoftGraphFileAttachment(
            raw_data=attachment_data,
            attachment_id=attachment_data.get("id"),
            **attachment_data,
        )
        for attachment_data in attachments_data
    ]


def build_mg_folder(
    folder_data: SingleJson,
    mailbox_name: str | None = None,
) -> MicrosoftGraphFolder:
    """Get MicrosoftGraphFolder object.

    Args:
        folder_data (SingleJson): json data for the folder from api
        response.
        mailbox_name (str): Mailbox name.

    Returns:
        MicrosoftGraphFolder: MicrosoftGraphFolder object.
    """
    return MicrosoftGraphFolder(
        raw_data=folder_data,
        folder_id=folder_data.get("id"),
        display_name=folder_data.get("displayName"),
        mailbox_name=mailbox_name,
    )


def build_mg_attachment(
    raw_data: SingleJson,
    mailbox_name: str,
    folder_name: str,
    folder_id: str,
    email_id: str,
) -> MutableSequence[MicrosoftGraphAttachment]:
    """Get the list of MicrosoftGraphAttachment objects.

    Args:
        raw_data (SingleJson): Json response data.
        mailbox_name (str): Mailbox address.
        folder_name (str): Folder name.
        email_id (str): Message id to get the attachment data.

    Returns:
        MutableSequence[MicrosoftGraphAttachment]:: list of
        datamodels.MicrosoftGraphAttachment objects.
    """

    return [
        MicrosoftGraphAttachment.from_json(
            attachment_json=attachment_data,
            mailbox_name=mailbox_name,
            folder_name=folder_name,
            folder_id=folder_id,
            email_id=email_id,
        )
        for attachment_data in raw_data.get("value", [])
    ]


def create_eml_object(
    original_email_content: bytes,
    attachment_name: str,
) -> Attachment:
    """Create eml object with the original email

    Args:
        original_email_content (bytes): content of email as bytes.
        attachment_name (str): Name of the attachment.

    Return: {Attachment} of attachment object
    """

    base64_blob = b64encode(original_email_content).decode()

    attachment_object = Attachment(
        case_identifier=None,
        alert_identifier=None,
        base64_blob=base64_blob,
        attachment_type=ATTACHMENT_EXTENSION,
        name=attachment_name,
        description=EML_ATTACHMENT_DESCRIPTION,
        is_favorite=False,
        orig_size=len(original_email_content),
        size=len(base64_blob),
    )

    return attachment_object


def build_mg_oof_settings_object(raw_data: SingleJson) -> UserOOFSettings:
    """Get UserOOFSettings object.

    Args:
        raw_data (SingleJson): json data for the OOFSettings data from api response.

    Returns:
        UserOOFSettings: UserOOFSettings object.
    """
    return UserOOFSettings(raw_data=raw_data)


def build_search_results(
    response_json: Sequence[SingleJson],
) -> MutableSequence[SearchResultData]:
    """Builds a list of `SearchResultData` objects from API response data.

    Args:
        response_json (Sequence[SingleJson]): The JSON response from the API containing
        search results.

    Returns:
        MutableSequence[SearchResultData]: A list of `SearchResultData` objects
        constructed from the search hits in the API response.
    """
    return [
        SearchResultData.from_json(response_json=response)
        for response in response_json
    ]
