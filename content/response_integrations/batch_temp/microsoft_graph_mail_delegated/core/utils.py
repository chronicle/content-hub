from __future__ import annotations

from typing import Any

from base64 import b64encode, b64decode
import binascii
from collections.abc import (
    Container,
    Iterable,
    Mapping,
    MutableSequence,
    Sequence,
)
from email.parser import BytesParser
from email.policy import default
from email import message

import collections
import mimetypes
import os
import time

from soar_sdk.SiemplifyDataModel import Attachment
from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.smp_time import (
    convert_string_to_timestamp,
    is_approaching_action_timeout,
)
from TIPCommon.soar_ops import get_file, save_file
from TIPCommon.types import ChronicleSOAR, SingleJson
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from . import constants

from .datamodels import (
    IntegrationParameters,
    MicrosoftGraphAttachment,
    MicrosoftGraphEmail,
    MicrosoftGraphFolder,
    SmimeAuth,
)
from . import EmailUtils
from . import exceptions
from .MicrosoftGraphMailDelegatedManager import ApiManager


MailboxResult = collections.namedtuple(
    "MailboxResult",
    ["valid_mailboxes", "invalid_mailboxes", "invalid_folder_mailboxes"],
)


def get_integration_parameters(siemplify: ChronicleSOAR) -> IntegrationParameters:
    """
    Get the parameters object for MicrosoftGraphMailDelegated's auth and api manager
    """
    azure_ad_endpoint = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Microsoft Entra ID Endpoint",
        is_mandatory=True,
    )
    microsoft_graph_endpoint = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Microsoft Graph Endpoint",
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Client Secret Value",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Microsoft Entra ID Directory ID",
        is_mandatory=True,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Refresh Token",
        is_mandatory=True,
    )
    user_mailbox = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="User Mailbox",
        is_mandatory=True,
    )
    redirect_url = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Redirect URL",
        print_value=True,
    )
    mail_field_source = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Mail Field Source",
        input_type=bool,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
    )
    private_key_b64 = extract_configuration_param(
        siemplify=siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Base64 Encoded Private Key",
    )
    certificate_b64 = extract_configuration_param(
        siemplify=siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Base64 Encoded Certificate",
    )
    ca_certificate_b64 = extract_configuration_param(
        siemplify=siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Base64 Encoded CA certificate",
    )
    smime_auth = SmimeAuth(
        private_key_b64=private_key_b64,
        certificate_b64=certificate_b64,
        ca_certificate_b64=ca_certificate_b64,
    )
    integration_params = IntegrationParameters(
        azure_ad_endpoint=azure_ad_endpoint,
        microsoft_graph_endpoint=microsoft_graph_endpoint,
        client_id=client_id,
        secret_id=secret_id,
        tenant=tenant,
        user_mailbox=user_mailbox,
        refresh_token=refresh_token,
        redirect_url=redirect_url,
        mail_field_source=mail_field_source,
        verify_ssl=verify_ssl,
        smime_auth=smime_auth,
        siemplify_logger=siemplify.LOGGER,
    )
    validate_configuration_params(siemplify, integration_params)

    return integration_params


def validate_configuration_params(
    soar_action: ChronicleSOAR,
    config_params: IntegrationParameters,
) -> None:
    """Validate configuration parameters for auth params and api params wi and user
        service account attributes.

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object.
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object.
        api_params (api_manager.ApiParameters): api params object.
    """
    validator = ParameterValidator(soar_action)
    if not is_empty_string_or_none(config_params.user_mailbox):
        config_params.user_mailbox = validator.validate_email(
            param_name="User Mailbox",
            email=config_params.user_mailbox,
            print_value=True,
        )

    if (
        config_params.smime_auth.private_key_b64
        and not config_params.smime_auth.certificate_b64
    ) or (
        not config_params.smime_auth.private_key_b64
        and config_params.smime_auth.certificate_b64
    ):
        raise exceptions.InvalidParameterException(
            "Both private key and certificate are required or "
            "neither should be provided."
        )

    validate_b64_certificate(
        param_name="Base64 Encoded Private Key",
        param_value=config_params.smime_auth.private_key_b64,
    )
    validate_b64_certificate(
        param_name="Base64 Encoded Certificate",
        param_value=config_params.smime_auth.certificate_b64,
    )
    validate_b64_certificate(
        param_name="Base64 Encoded CA certificate",
        param_value=config_params.smime_auth.ca_certificate_b64,
    )


def validate_b64_certificate(param_name: str, param_value: str) -> None:
    """Validate if the provided parameter value is a valid base64 encoded string.

    Args:
        param_name (str): The name of the parameter being validated.
        param_value (str): The value of the parameter to validate.

    Raises:
        exceptions.InvalidParameterException: If the provided parameter value is not a
            valid base64 encoded string.
    """
    if param_value:
        try:
            b64decode(param_value)

        except (ValueError, binascii.Error) as e:
            raise exceptions.InvalidParameterException(
                f"Invalid value was provided for parameter {param_name}. Error: {e}"
            )


def transform_dict_keys(
    original_dict: Mapping[str, Any],
    prefix: str,
    keys_to_except: Container[str] | None = None,
) -> SingleJson:
    """Transform dict keys by adding prefix

    Args:
        original_dict (Mapping[str, Any]): The dictionary whose keys are to be
            transformed.
        prefix (str): The prefix to add to the dictionary keys.
        keys_to_except (Container[str] | None): A container of keys that should not
            be prefixed. Defaults to None.

    Returns
        SingleJson: The transformed dict
    """
    if keys_to_except is None:
        keys_to_except = []

    if prefix:
        return {
            f"{prefix}_{key}" if key not in keys_to_except else key: value
            for key, value in original_dict.items()
        }

    return original_dict


def transform_template_string(template: str, event: Mapping[str, str]) -> str:
    """Transform string containing template using event data.

    Args:
        template(str): String containing template.
        event(Mapping[str, str]): Case event data.

    Returns:
        str: Transformed string.
    """
    index = 0

    while (
        constants.PLACEHOLDER_START in template[index:]
        and constants.PLACEHOLDER_END in template[index:]
    ):
        partial_template = template[index:]
        start, end = (
            partial_template.find(constants.PLACEHOLDER_START)
            + len(constants.PLACEHOLDER_START),
            partial_template.find(constants.PLACEHOLDER_END),
        )
        substring = partial_template[start:end]
        value = event.get(substring) if event.get(substring) else ""
        template = template.replace(
            f"{constants.PLACEHOLDER_START}{substring}{constants.PLACEHOLDER_END}",
            value,
            1,
        )
        index = index + start + len(value)

    return template


def create_siemplify_case_wall_attachment_object(
    full_file_name: str,
    file_contents: bytes,
) -> Attachment:
    """Create attachment object with the original email.

    Args:
        full_file_name(str): File name of the attachment.
        file_contents(bytes): Attachment content as bytes.

    Returns:
        Attachment: Siemplify attachment object.
    """
    base64_blob = b64encode(file_contents).decode()

    file_name, file_extension = os.path.splitext(full_file_name)
    attachment_object = Attachment(
        case_identifier=None,
        alert_identifier=None,
        base64_blob=base64_blob,
        attachment_type=file_extension,
        name=file_name,
        description="Original email attachment",
        is_favorite=False,
        orig_size=len(file_contents),
        size=len(base64_blob),
    )
    return attachment_object


def filter_valid_invalid_mailboxes(
    manager: ApiManager,
    mailboxes: MutableSequence[str],
    default_mailbox: str,
) -> tuple[MutableSequence[str], MutableSequence[str]]:
    """Filter valid and invalid mailboxes provided in action param and from
    MicrosoftGraphMailDelegated server.

    This method retrieves the email addresses of searchable mailboxes from
    the manager provided in mailboxes, compare them and returns valid and invalid
    mailboxes.
    Args:
        manager (ApiManager): ApiManager instance.
        mailboxes (MutableSequence[str]): List of mailboxes provided.
        default_mailbox (str): Default mailbox if action parameter has 'Default Mailbox'
        as string in csv values.

    Returns:
        tuple[MutableSequence[str], MutableSequence[str]]: A tuple containing the comma
        separated list of searchable and unsearchable mailboxes.
    """
    valid_mailboxes = []
    invalid_mailboxes = []
    mailbox_list = _get_mailboxes_as_list(mailboxes, default_mailbox)
    for mailbox in mailbox_list:
        try:
            user_mailbox = manager.get_user_mailbox(mail_address=mailbox)
            valid_mailboxes.append(user_mailbox)

        except exceptions.MicrosoftGraphMailManagerError as err:
            if not _error_contains_mailbox_or_permission_error_msg(mailbox, err):
                raise exceptions.MicrosoftGraphMailManagerError(err) from err

            invalid_mailboxes.append(mailbox)

    return valid_mailboxes, invalid_mailboxes


def validate_mailbox(manager: ApiManager, mailbox: str, default_mailbox: str) -> str:
    """Validates if the given mailbox exists.

    Args:
        manager (ApiManager): The API manager instance.
        mailbox (str): The mailbox provided in action parameter.
        default_mailbox (str): The default mailbox.

    Returns:
        str: The validated mailbox that exists.

    Raises:
        MicrosoftGraphMailManagerError: If the provided mailbox is not found.
    """
    mailbox_result = filter_valid_invalid_mailboxes(
        manager=manager,
        mailboxes=[mailbox],
        default_mailbox=default_mailbox,
    )
    if not mailbox_result[0]:
        raise exceptions.MicrosoftGraphMailManagerError(
            f'The provided mailbox "{mailbox}" was not found.'
        )

    return mailbox_result[0][0]


def _error_contains_mailbox_or_permission_error_msg(
    mailbox: str,
    err: exceptions.MicrosoftGraphMailManagerError,
) -> bool:
    err_msg = str(err)
    mailbox_err_msg = constants.MAILBOX_DOES_NOT_EXIST_ERROR.format(
        mail_address=mailbox
    )
    return mailbox_err_msg in err_msg or constants.MAILBOX_NOT_FOUND_ERROR in err_msg


def _get_mailboxes_as_list(
    mailboxes: MutableSequence[str],
    default_mailbox: str,
) -> MutableSequence[str]:
    mailboxes = [
        (
            default_mailbox.lower()
            if mailbox == constants.DEFAULT_MAILBOX
            else mailbox.lower()
        )
        for mailbox in mailboxes
    ]

    return mailboxes


def get_mailbox(mailbox: str, default_mailbox: str) -> str:
    if mailbox == constants.DEFAULT_MAILBOX:
        return default_mailbox

    return mailbox


def has_processed_emails(
    mailboxes_emails: Mapping[str, Sequence[MicrosoftGraphEmail]],
) -> bool:
    """Check if any emails have been processed across all mailboxes.

    Args:
        mailboxes_emails(Mapping[str, Sequence[MicrosoftGraphEmail]]): A dictionary
        mapping mailbox names to sequences of processed emails.

    Returns:
        bool: True if any email has been processed,
    """
    return any(mailboxes_emails.values())


def update_search_filters(
    folders: MutableSequence[MicrosoftGraphFolder],
    subject_filter: str | None = None,
    sender_filter: str | None = None,
    time_filter: str | None = None,
    only_unread: bool = False,
    limit: int | None = None,
    is_all_field: bool = False,
) -> MutableSequence[MicrosoftGraphFolder]:
    """Update search filters for a list of MicrosoftGraphFolders.

    Args:
        folders (MutableSequence[MicrosoftGraphFolder]): List of MicrosoftGraphFolders
        to update.
        subject_filter (str | None): Subject filter to apply.
        sender_filter (str | None): Sender filter to apply.
        time_filter (str | None): Time filter to apply.
        only_unread (bool): Flag to filter only unread emails.
        limit (int | None): Limit the number of results.
        is_all_field(bool): Flag to filter only unread emails.

    Returns:
        MutableSequence[MicrosoftGraphFolder]: Updated list of MicrosoftGraphFolders.
    """
    for folder in folders:
        folder.subject_filter = subject_filter
        folder.sender_filter = sender_filter
        folder.time_filter = time_filter
        folder.only_unread = only_unread
        folder.limit = limit
        folder.is_all_field = is_all_field

    return folders


def get_emails_with_email_ids(
    manager: ApiManager,
    mailboxes: Iterable[str],
    email_ids: Iterable[str],
) -> MutableSequence[MicrosoftGraphEmail]:
    """Retrieve email details for specified message IDs in the given mailboxes.

    Args:
        manager (ApiManager): The ApiManager instance.
        mailboxes (Iterable[str]): A list of mailboxes to retrieve email details from.
        email_ids (Iterable[str]): A list of email IDs for which to retrieve details.

    Returns:
        MutableSequence[MicrosoftGraphEmail]: A list of retrieved MicrosoftGraphEmail
        objects.
    """
    valid_emails: MutableSequence[MicrosoftGraphEmail] = []
    for mailbox in mailboxes:
        for email_id in email_ids:
            try:
                email = manager.get_mail_details(folder=mailbox, email_id=email_id)
                valid_emails.append(email)

            except exceptions.MicrosoftGraphMailManagerError:
                pass

    return valid_emails


def get_mailboxes_result(
    manager: ApiManager,
    mailboxes: Iterable[str],
    folder_name: str,
) -> MailboxResult:
    """Retrieve mailbox information for a given folder.

    Args:
        manager (ApiManager): The ApiManager instance.
        mailboxes (Iterable[str]): A list of mailboxes to retrieve information from.
        folder_name (str): The name of the folder to retrieve information about.

    Returns:
        MailboxResult: A named tuple containing information about valid and invalid
        mailboxes.
    """
    valid_mailboxes: MutableSequence[MicrosoftGraphFolder] = []
    invalid_mailboxes: MutableSequence[str] = []
    invalid_folder_mailboxes: MutableSequence[str] = []

    for mailbox in mailboxes:
        try:
            folder = manager.get_folder_by_name(
                folder_name=folder_name, mail_address=mailbox
            )
            valid_mailboxes.append(folder)

        except exceptions.MicrosoftGraphMailManagerError as error:
            if f"Mail folder \"{folder_name}\"" in str(error):
                invalid_folder_mailboxes.append(mailbox)
            else:
                invalid_mailboxes.append(mailbox)

    return MailboxResult(valid_mailboxes, invalid_mailboxes, invalid_folder_mailboxes)


def get_sent_draft_email(
    manager: ApiManager,
    folder: MicrosoftGraphFolder,
    email: MicrosoftGraphEmail,
    timeout_in_ms: int,
) -> MicrosoftGraphEmail:
    """Get draft email from sent items folder with created draft email.

    Args:
        manager (ApiManager): ApiManager object
        folder (MicrosoftGraphFolder): MicrosoftGraphFolder object
        email (MicrosoftGraphEmail): MicrosoftGraphEmail object
        timeout_in_ms (int): Action execution script timeout.

    Raises:
        TimeoutReachedException: Raised if the timeout is reached while
        searching for the forwarded email.

    Returns:
        MicrosoftGraphEmail: The email which was created as a draft and sent.
    """
    while True:
        time.sleep(constants.TIME_INTERVAL)
        manager.logger.info(
            "Getting sent draft mail details with internetMessageId "
            f'"{email.internet_message_id}"'
        )
        sent_emails = _get_emails_to_forwarded_email(manager, folder, email)
        forwarded_email = _get_latest_forwarded_email(sent_emails)
        if forwarded_email:
            break

        if is_approaching_action_timeout(
            timeout_in_ms,
            timeout_threshold_in_sec=constants.TIMEOUT_SECONDS,
        ):
            raise exceptions.TimeoutReachedException(
                "Unable to get sent draft mail details with internetMessageId "
                f'"{email.internet_message_id}".'
            )
        manager.logger.info("Retrying...")

    manager.logger.info(
        f"Email details found successfully from {constants.DEFAULT_SENT_FOLDER_NAME}."
    )

    return forwarded_email


def _get_emails_to_forwarded_email(
    manager: ApiManager,
    folder: MicrosoftGraphFolder,
    email: MicrosoftGraphEmail,
) -> list[MicrosoftGraphEmail]:
    email.reply_folder_id = folder.id
    return manager.get_all_replies(
        email=email,
        internet_message_id=email.internet_message_id,
    )


def _get_latest_forwarded_email(
    sent_emails: MutableSequence[MicrosoftGraphEmail],
) -> MicrosoftGraphEmail | None:
    """Getting latest email sorted with receivedDateTime from list of emails.

    Args:
        sent_emails (MutableSequence[MicrosoftGraphEmail]): List of emails grouped by
        internet message id for the forwarded email.

    Returns:
        MicrosoftGraphEmail | None: MicrosoftGraphEmail object, otherwise None.
    """
    if not sent_emails:
        return None

    sorted_emails = sorted(
        sent_emails,
        key=lambda email: convert_string_to_timestamp(email.received_date_time),
        reverse=True,
    )

    return sorted_emails[0]


def encode_content_as_base64(item_content: bytes) -> str:
    """
    Encode the provided content as a Base64 string.

    Args:
        content (bytes): The content to be encoded as Base64.

    Returns:
        str: The Base64-encoded representation of the content as a string.
    """
    return b64encode(item_content).decode()


def get_recipient_first_valid_reply(
    sender: str,
    replies: Sequence[MicrosoftGraphEmail],
    body_exclude_pattern: str,
    logger: SiemplifyLogger,
) -> MicrosoftGraphEmail | None:
    """Get the first valid message sent by the recipient.

    Args:
        sender (str): Sender address.
        replies (Sequence[MicrosoftGraphEmail]): List of EmailModel or
        MicrosoftGraphEmail objects
        body_exclude_pattern(str): Regex pattern to exclude replies based on body
        content.
        logger(SiemplifyLogger): Siemplify logger instance.

    Returns:
        MicrosoftGraphEmail | None: The first valid message or None if no valid message
        is found.
    """
    sender_replies = [
        reply for reply in replies if reply.sender.lower() == sender.lower()
    ]
    sender_replies = sorted(sender_replies, key=lambda i: i.received_date_time)

    filtered_replies, excluded_reply = EmailUtils.filter_emails_with_regexes(
        emails=sender_replies,
        exclude_regex_pattern=body_exclude_pattern,
    )

    logger.info(f"Excluded {len(excluded_reply)} replies for sender: {sender}")
    logger.info(f"Filtered {len(filtered_replies)} replies for sender: {sender}")

    return filtered_replies[0] if filtered_replies else None


def fix_filename(file_name: str) -> str:
    """Replaces slashes in filenames with underscores.

    Args:
      file_name(str): The filename to be fixed (str).

    Returns:
      str: The fixed filename with slashes replaced by underscores (str).
    """
    if not file_name:
        return constants.UNKNOWN_FILE_NAME

    if "/" in file_name:
        file_name = file_name.replace("/", "_")
    if "\\" in file_name:
        file_name = file_name.replace("\\", "_")

    return file_name


def validate_file(
    chronicle_soar: ChronicleSOAR,
    file_identifier: str,
    file_location: str,
) -> bool:
    """Check the file identifier exists in GCP Bucket or Local System.

    Args:
        chronicle_soar (ChronicleSOAR): ChronicleSOAR action object.
        file_identifier (str): File identifier to check if it exists.
        file_location (str): Location of file whether on GCP or Local.

    Returns:
        bool: True if file exists, False otherwise.
    """
    if file_location == constants.DEFAULT_FILE_LOCATION:
        return is_gcp_file(chronicle_soar, file_identifier)

    return os.path.isfile(file_identifier)


def is_gcp_file(chronicle_soar: ChronicleSOAR, file_identifier: str) -> bool:
    """Check the file identifier exists in GCP Bucket.

    Args:
        chronicle_soar (ChronicleSOAR): ChronicleSOAR action object.
        file_identifier (str): file identifier to check if it exists in the GCP bucket.

    Returns:
        bool: True if file identifier exists, False otherwise.
    """
    try:
        abcd = get_file(chronicle_soar, file_identifier)
        chronicle_soar.LOGGER.info(abcd)
        return bool(get_file(chronicle_soar, file_identifier))

    except Exception as e:
        chronicle_soar.LOGGER.info(e)
        if constants.GCP_FILE_NOT_FOUND_ERR in str(e).lower():
            return False

        raise


def save_file_to_gcp(
    chronicle_soar: ChronicleSOAR,
    file_path: str,
    file_name: str,
    file_content: bytes,
) -> str:
    """Save file to GCP bucket.

    Args:
        chronicle_soar (ChronicleSOAR): ChronicleSOAR instance.
        file_path (str): file path.
        file_name (str): file name.
        file_content (bytes): file content in bytes.

    Raises:
        exceptions.SaveFileToGCPError: If file is unable to save to GCP bucket.

    Returns:
        str: file_name with file path.
    """
    try:
        file_identifier = save_file(
            chronicle_soar=chronicle_soar,
            path=file_path,
            name=file_name,
            content=file_content,
        )
        chronicle_soar.LOGGER.info(f"File {file_name} saved successfully")

    except Exception as e:
        if constants.GCP_FILE_NOT_FOUND_ERR in str(e).lower():
            raise exceptions.SaveFileToGCPError(
                "Error while saving file to GCP Bucket. GCP Bucket is not supported "
                "in this instance."
            ) from e

        raise

    return file_identifier


def load_attachment(
    chronicle_soar: ChronicleSOAR,
    attachment_path: str,
    attachment_location: str,
) -> SingleJson:
    """Load specified attachment from either local disk or GCP bucket.

    Args:
        chronicle_soar (ChronicleSOAR): SiemplifyAction object.
        attachment_path (str): Attachment path or GCP identifiers.
        attachment_location (str): Location of attachment.

    Returns:
        SingleJson: Dictionaries representing file attachments.
    """
    if attachment_location == constants.DEFAULT_FILE_LOCATION:
        file_content = get_file(chronicle_soar, attachment_path)
        file_size = len(file_content)
    else:
        with open(attachment_path, "rb") as f:
            file_content = f.read()
        file_size = os.path.getsize(attachment_path)

    if file_size > constants.MAX_ATTACHMENT_SIZE:
        raise ValueError(
            "The following attachments exceed the size limit of 20MB: "
            f"{os.path.basename(attachment_path)}"
        )

    if not file_content:
        raise ValueError(
            f"Invalid attachment location or missing content for: {attachment_path}"
        )

    base64_blob = b64encode(file_content).decode()
    file_name = os.path.basename(attachment_path)
    content_type, _ = mimetypes.guess_type(file_name)
    content_type = content_type or "application/octet-stream"

    attachment = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": file_name,
        "contentType": content_type,
        "contentBytes": base64_blob,
    }

    return attachment


def get_attachments(
    manager: ApiManager,
    email: MicrosoftGraphEmail,
) -> list[MicrosoftGraphAttachment]:
    """
    Retrieves attachments from an email.

    This function determines whether an email is S/MIME encrypted and
    retrieves attachments accordingly. For S/MIME emails, it uses
    get_smime_attachments_from_email to extract attachments. For non-S/MIME
    emails, it uses the ApiManager's get_attachments method.

    Args:
        email (MicrosoftGraphEmail): The MicrosoftGraphEmail object.
        manager (ApiManager): The ApiManager instance for interacting with the API.

    Returns:
        list[MicrosoftGraphAttachment]: A list of MicrosoftGraphAttachment objects.
    """
    if email.is_smime_email:
        return get_smime_attachments_from_email(email)

    return manager.get_attachments(email)


def get_emails_with_updated_metadata(
    manager: ApiManager,
    emails: MutableSequence[MicrosoftGraphEmail],
    smime_auth: SmimeAuth,
) -> MutableSequence[MicrosoftGraphEmail]:
    """Updates the metadata of S/MIME encrypted emails.

    This function iterates through a list of MicrosoftGraphEmail objects,
    checks if each email is S/MIME encrypted, and if so, loads the email
    content, parses it, and updates the email object with the parsed data.

    Args:
        manager (ApiManager): The ApiManager instance.
        emails (MutableSequence[MicrosoftGraphEmail]): A list of
            MicrosoftGraphEmail objects to process.

    Returns:
        MutableSequence[MicrosoftGraphEmail]: The updated list of
            MicrosoftGraphEmail objects.
    """
    for email in emails:
        if email.is_smime_email:
            email_content = manager.load_email_content(email)
            email.mime_content = email_content
            email.parsed_email = _parsed_email(
                email_content,
                smime_auth,
                manager.logger,
            )
            email.set_smime_email_body()

    return emails


def _parsed_email(
    mime_content: bytes,
    smime_auth: SmimeAuth,
    logger: SiemplifyLogger,
) -> SingleJson:
    decrypted_mime_content: bytes = EmailUtils.get_decrypted_mime_content(
        mime_content=mime_content,
        smime_auth=smime_auth,
        logger=logger,
    )
    decrypted_email: message.Message = BytesParser(policy=default).parsebytes(
        text=decrypted_mime_content
    )

    email_data: SingleJson = EmailUtils.EmailUtils(logger).convert_eml_to_siemplify_eml(
        msg=decrypted_email
    )
    email_data["attachments"]: list[SingleJson] = get_attachments_from_eml(
        decrypted_email
    )

    return email_data


def get_attachments_from_eml(email: message.Message) -> Iterable[SingleJson]:
    """Extract attachments from an email message.

    Args:
        email (message.Message): The email message to extract attachments from.
            This should be an instance of email.message.Message, typically
            obtained by parsing an email using email.parser.BytesParser.
            The email should contain attachments.

    Returns:
        Iterable[dict[str, str]]: list of attachments data.
    """
    attachments = []
    for part in email.iter_attachments():
        content: bytes = part.get_payload(decode=True) or b""
        content_type: str = part.get_content_type()
        filename: str | None = part.get_filename() or None
        file_ext: str | None = (
            os.path.splitext(filename)[1].lower() if filename else None
        )

        is_eml = content_type == "message/rfc822" or file_ext == ".eml"
        if is_eml:
            part: message.Message = part.get_payload()
            if isinstance(part, list):
                part = part[0]
                content_type = part.get_content_type()
                filename = f"{part.get('subject', 'unnamed')}.eml"
                file_ext = ".eml"
                content = part.as_bytes()

            if isinstance(part, str):
                content = part.encode()

        attachments.append(
            {
                "name": filename,
                "fileExt": file_ext,
                "contentType": content_type,
                "contentBytes": content,
                "isSmime": True,
            }
        )

    return attachments


def get_smime_attachments_from_email(
    email: MicrosoftGraphEmail,
) -> Iterable[MicrosoftGraphAttachment]:
    """
    Extracts and returns attachments from an S/MIME encrypted email.

    This function processes a MicrosoftGraphEmail object that has been
    decrypted and parsed, extracting any attachments found within the
    parsed email content. It then converts these attachments into
    MicrosoftGraphAttachment objects.

    Args:
        email (MicrosoftGraphEmail): The MicrosoftGraphEmail object containing
            the parsed S/MIME email data.

    Returns:
        Iterable[MicrosoftGraphAttachment]: An iterable of
            MicrosoftGraphAttachment objects representing the extracted attachments.
    """
    attachments = []
    for attachment in email.parsed_email["attachments"]:
        attachment["@odata.type"] = "#microsoft.graph.fileAttachment"
        attachments.append(
            MicrosoftGraphAttachment.from_json(
                attachment_json=attachment,
                mailbox_name=email.mailbox_name,
                folder_name=email.folder_name,
                folder_id=email.folder_id,
                email_id=email.id,
            )
        )

    return attachments
