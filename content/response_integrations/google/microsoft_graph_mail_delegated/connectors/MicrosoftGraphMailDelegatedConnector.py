from __future__ import annotations

import base64
import os
from pathlib import Path
import re
import sys
import uuid
from collections import defaultdict
from collections.abc import Iterable
from extract_msg.exceptions import InvalidFileFormatError
import requests

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo, CaseInfo
from soar_sdk.SiemplifyDataModel import Attachment

from TIPCommon.base.connector import Connector
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.data_models import BaseAlert
from TIPCommon.exceptions import ParameterExtractionError, SMIMEMailError
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import (
    convert_datetime_to_unix_time,
    get_last_success_time,
    is_approaching_timeout,
    unix_now,
)
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run, is_overflowed

from core.EmailUtils import EmailUtils, get_html_urls
from EnvironmentCommon import GetEnvironmentCommonFactory
from core import AuthenticationManager as auth_manager
from core import MicrosoftGraphMailDelegatedManager as api_manager
from core.MicrosoftGraphMailDelegatedParser import create_eml_object

from core.constants import (
    CASE_NAME_PATTERN,
    EVENT_ATTACHMENT_CONTENT_TYPE_MAP,
    KEYS_TO_EXCEPT_ON_TRANSFORMATION,
    PRIORITY_DEFAULT,
    SMIME_ATTACHMENT_CONTENT_TYPES,
    STORED_IDS_LIMIT,
    EMPTY_EMAIL_SUBJECT,
)
from core.datamodels import MicrosoftGraphEmail, MicrosoftGraphFileAttachment, SmimeAuth
from core import exceptions
from core.utils import (
    create_siemplify_case_wall_attachment_object,
    transform_dict_keys,
    transform_template_string,
    validate_b64_certificate,
)

CONNECTOR_NAME = "Microsoft Graph Mail Delegated Connector"
CONNECTOR_STARTING_TIME = unix_now()


class MicrosoftGraphMailDelegatedConnector(Connector):

    def __init__(self, _is_test: bool) -> None:
        super().__init__(CONNECTOR_NAME, _is_test)
        self.manager: api_manager.ApiManager | None = None
        self.regex_map = self._build_regex_map(self.siemplify.whitelist)
        self.email_utils = EmailUtils(logger=self.logger)

    def validate_params(self):
        """Validate connector parameters."""
        self.params.max_email_per_cycle = self.param_validator.validate_positive(
            param_name="Max Emails Per Cycle",
            value=self.params.max_emails_per_cycle,
        )
        self.params.offset_time_in_hours = self.param_validator.validate_non_negative(
            param_name="Offset Time In Hours",
            value=self.params.offset_time_in_hours,
        )
        validate_b64_certificate(
            param_name="Base64 Encoded Private Key",
            param_value=self.params.base64_encoded_private_key,
        )
        validate_b64_certificate(
            param_name="Base64 Encoded Certificate",
            param_value=self.params.base64_encoded_certificate,
        )
        validate_b64_certificate(
            param_name="Base64 Encoded CA certificate",
            param_value=self.params.base64_encoded_ca_certificate,
        )
        self.params.headers_to_add_to_events = string_to_multi_value(
            self.params.headers_to_add_to_events,
            only_unique=True
        )

    def init_managers(self) -> None:
        """Initializes the API client manager."""
        auth_params = auth_manager.SessionAuthenticationParameters(
            azure_ad_endpoint=self.params.microsoft_entra_id_endpoint,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret_value,
            tenant=self.params.microsoft_entra_id_directory_id,
            refresh_token=self.params.refresh_token,
            verify_ssl=self.params.verify_ssl,
        )
        session = auth_manager.get_authenticated_session(auth_params)
        api_params = api_manager.ApiParameters(
            api_root=self.params.microsoft_graph_endpoint,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret_value,
            tenant=self.params.microsoft_entra_id_directory_id,
            mail_address=self.params.mail_address,
        )
        self.manager = api_manager.ApiManager(
            session=session,
            api_parameters=api_params,
            mail_field_source=self.params.mail_field_source,
            logger=self.logger,
        )
        mail_address = self.manager.get_user_mailbox(self.params.mail_address)
        self.manager.mail_address = mail_address

        return self.manager

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def get_last_success_time(self) -> int:
        return get_last_success_time(
            self.siemplify,
            offset_with_metric={"hours": self.params.offset_time_in_hours},
        )

    def set_last_success_time(
        self, alerts: Iterable[MicrosoftGraphEmail], **kwargs
    ) -> None:
        """Set connector's last success time."""
        super().set_last_success_time(
            alerts=alerts,
            timestamp_key="timestamp",
            **kwargs,
        )

    def get_alerts(self) -> Iterable[MicrosoftGraphEmail]:
        """Gets emails from the API manager."""
        self.logger.info(
            f"Successfully loaded {len(self.context.existing_ids)} existing ids"
        )
        try:
            emails = self.manager.get_emails(
                folder_name=self.params.folder_to_check_for_emails,
                datetime_from=self.get_last_success_time(),
                max_email_per_cycle=self.params.max_email_per_cycle,
                existing_ids=self.context.existing_ids,
                unread_only=self.params.unread_emails_only,
                email_exclude_pattern=self.params.email_exclude_pattern,
                connector_starting_time=CONNECTOR_STARTING_TIME,
                script_timeout=self.params.python_process_timeout,
            )

            return emails[:1] if self.is_test_run else emails
        except (
            exceptions.MicrosoftGraphMailManagerError,
            requests.exceptions.RequestException,
        ) as e:
            self.logger.warn(
                "Failed to fetch emails due to transient upstream API or connection error. "
                f"Skipping this cycle. Details: {e}"
            )
            return []

    def create_alert_info(self, alert: MicrosoftGraphEmail) -> AlertInfo:
        """Convert BaseAlert object to a Siemplify AlertInfo object.

        Args:
            alert: The BaseAlert object.

        Returns:
            AlertInfo: A Siemplify AlertInfo object.
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = alert.identifier
        alert_info.display_id = alert.identifier
        alert_info.rule_generator = alert.rule_generator
        alert_info.start_time = int(alert.start_time)
        alert_info.end_time = int(alert.end_time)

        return alert_info

    def write_context_data(self, all_alerts: Iterable[MicrosoftGraphEmail]) -> None:
        """Write connector's context data."""
        if not all_alerts:
            return

        self.logger.info("Saving existing ids.")
        write_ids(
            self.siemplify,
            self.context.existing_ids,
            stored_ids_limit=STORED_IDS_LIMIT,
        )

    def _disable_overflow_check(self, alerts: Iterable[CaseInfo]) -> bool:
        """Checks if an alert is overflowed and should be skipped based on
            configuration settings.

        Args:
            alerts: Iterable of CaseInfo objects.

        Return: True if the alert is overflowed and should be skipped, otherwise False.
        """
        original_case = alerts[0]
        alert_is_overflowed = not self.params.disable_overflow and is_overflowed(
            self.siemplify,
            original_case,
            is_test_run,
        )
        if alert_is_overflowed:
            self.logger.info(
                f"{original_case.rule_generator}-{original_case.ticket_id}-"
                f"{original_case.environment}-{original_case.device_product}"
                f" found as overflow alert. Skipping."
            )
        return alert_is_overflowed

    def process_alerts(
        self,
        alerts: Iterable[MicrosoftGraphEmail],
    ) -> tuple[Iterable[CaseInfo], Iterable[MicrosoftGraphEmail]]:
        """Processes fetched alerts."""
        processed_alerts = []
        processed_email: Iterable[MicrosoftGraphEmail] = []
        all_alerts = []

        for alert in alerts:
            try:
                microsoft_graph_alert = alert
                all_alerts.append(microsoft_graph_alert)
                self.logger.info(
                    f"Starting to process alert {microsoft_graph_alert.id}"
                )

                if is_approaching_timeout(
                    self.params.python_process_timeout,
                    CONNECTOR_STARTING_TIME,
                    TIMEOUT_THRESHOLD,
                ):
                    self.logger.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                alert.mime_content = self.manager.load_email_content(email=alert)
                alert.parsed_email = self._parse_eml(alert.id, alert.mime_content)
                if alert.parsed_email is None:
                    self.context.existing_ids.append(microsoft_graph_alert.id)
                    continue
                if alert.is_smime_email:
                    self._set_smime_event_type_attachments(alert=alert)

                processed_alert = self.process_alert(alert=microsoft_graph_alert)
                disable_overflow = self._disable_overflow_check(processed_alert)
                if disable_overflow:
                    continue
                if isinstance(processed_alert, (list, tuple)):
                    processed_alerts.extend(processed_alert)
                elif processed_alert:
                    processed_alerts.append(processed_alert)

                if self.is_test_run and processed_alerts:
                    self.logger.info("Maximum alert count (1) for test run reached!")
                    break
                self.context.existing_ids.append(microsoft_graph_alert.id)
                processed_email.append(microsoft_graph_alert)

            except Exception as e: # pylint: disable=broad-except
                if hasattr(alert, "id"):
                    alert_id_to_log = alert.id
                elif hasattr(alert, "alert_id"):
                    alert_id_to_log = alert.alert_id
                else:
                    alert_id_to_log = str(alert)

                self.logger.error(
                    f"Failed to process alert with id {alert_id_to_log}: {e}"
                )
                self.logger.exception(e)
        if self.params.mark_emails_as_read:
            self.manager.mark_emails_as_read(processed_email)

        return processed_alerts, all_alerts

    def _set_smime_event_type_attachments(self, alert: MicrosoftGraphEmail) -> None:
        _, event_type_attachments = self._get_smime_attachments_from_parsed_alert(
            alert.parsed_email["attachments"]
        )
        self._set_smime_event_type_attachment_to_email(
            alert=alert,
            event_attachments=event_type_attachments,
        )

    def _set_smime_event_type_attachment_to_email(
        self,
        alert: MicrosoftGraphEmail,
        event_attachments: list[tuple[str, bytes]],
    ) -> None:
        for attachment_name, attachment_content in event_attachments:
            extension = Path(attachment_name).suffix.lower()
            content_type = EVENT_ATTACHMENT_CONTENT_TYPE_MAP.get(extension)
            if content_type:
                attachment_object = self._get_attachment_object(
                    attachment_name, attachment_content, content_type
                )
                getattr(alert, f"{extension[1:]}_attachments").append(attachment_object)

    def _get_attachment_object(
        self,
        attachment_name: str,
        attachment_content: bytes,
        content_type: str,
    ) -> MicrosoftGraphFileAttachment:
        raw_data = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": attachment_name,
            "contentType": content_type,
        }
        attachment = MicrosoftGraphFileAttachment(raw_data=raw_data, **raw_data)
        attachment.content = attachment_content

        return attachment

    def _map_alerts_to_base_alerts(
        self, emails: Iterable[MicrosoftGraphEmail]
    ) -> Iterable[MicrosoftGraphEmail]:
        """Maps MicrosoftGraphEmail objects to BaseAlert objects."""
        base_alerts = []

        for email in emails:
            base_alert = BaseAlert(
                raw_data=email.to_json(),
                alert_id=email.id,
            )
            base_alerts.append(base_alert)
        return base_alerts

    def _build_regex_map(self, regex_list) -> SingleJson:
        regex_map = {}
        for regex_item in regex_list:
            try:
                if ": " in regex_item:
                    user_regex = regex_item.split(": ", 1)
                    if len(user_regex) >= 2:
                        regex_map.update({user_regex[0]: user_regex[1]})
            except (ValueError, AttributeError, IndexError) as e:
                self.siemplify.logger.error(
                    f"Unable to get parse whitelist item {regex_item}. "
                    f"Ignoring item and continuing."
                )
                self.siemplify.logger.exception(e)
        return regex_map

    def _extract_regex_from_content(self, email_subject, email_body) -> SingleJson:
        """Get urls, subject, from and to addresses from email body

        Args:
            email_subject: {str} email subject.
            email_body: {str} email body.

        Return: {dict} fields after parse.
        """
        result_dictionary = {}
        for key, regex_value in self.regex_map.items():
            if regex_value:
                regex_object = re.compile(regex_value)
                all_results = regex_object.findall(email_body) + regex_object.findall(
                    email_subject
                )

                for index, result in enumerate(all_results, 1):
                    key_name = f"{key}_{index}"
                    result_dictionary[key_name] = result

        return result_dictionary

    def _get_eml_attachments(
        self,
        email: MicrosoftGraphEmail,
    ) -> Iterable[MicrosoftGraphFileAttachment]:
        """Get eml attachments.

        Args:
            email: {MicrosoftGraphEmail} Parse microsoft graph email.

        Return: {list} EML attachments list exported from original message
        """
        attachments = []

        for eml_attachment in email.eml_attachments:
            try:
                self.logger.info(f"Parsing EML: {eml_attachment.name}")
                parsed_eml = self._parse_eml(email.id, eml_attachment.content)
                if not parsed_eml:
                    continue

                parsed_eml["attachments_md5_filehash"] = eml_attachment.md5_hash()

                attachments.append((eml_attachment.name, parsed_eml))

            except (AttributeError, KeyError, TypeError, LookupError) as err:
                self.logger.error("Failed Parsing EML content")
                self.logger.exception(err)

        return attachments

    def _parse_eml(self, alert_id: str, content: bytes) -> SingleJson | None:
        try:
            smime_auth = SmimeAuth(
                private_key_b64=self.params.base64_encoded_private_key,
                certificate_b64=self.params.base64_encoded_certificate,
                ca_certificate_b64=self.params.base64_encoded_ca_certificate,
            )
            return self.email_utils.convert_siemplify_eml_to_connector_eml(
                content,
                headers_to_add=self.params.headers_to_add_to_events,
                smime_auth=smime_auth,
            )

        except (ParameterExtractionError, SMIMEMailError, ValueError) as e:
            self.logger.error(
                f"Failed to process SMIME email with message_id={alert_id}. "
                f"Skipping. Error: {str(e)}"
            )

        return None

    def _get_msg_attachments(
        self, email: MicrosoftGraphEmail
    ) -> Iterable[MicrosoftGraphFileAttachment]:
        """Get msg attachments.

        Args:
            email: {MicrosoftGraphEmail} Parse microsoft graph email.

        Return: {list} MSG attachments list exported from original message.
        """
        parsed_attachments = []
        for msg_attachment in email.msg_attachments:
            self.logger.info(f"Parsing MSG: {msg_attachment.name}")
            parsed_msg = self.email_utils.convert_siemplify_msg_to_connector_msg(
                msg_attachment.content,
                headers_to_add=self.params.headers_to_add_to_events,
            )

            if parsed_msg is None:
                self.logger.info(
                    f"Corrupted MSG attachment detected: {msg_attachment.name}. "
                    f"Treating as regular file attachment."
                )
                email.file_attachments.append(msg_attachment)
                continue

            parsed_msg["attachments_md5_filehash"] = msg_attachment.md5_hash()
            parsed_attachments.append((msg_attachment.name, parsed_msg))

        return parsed_attachments

    def _get_ics_attachments(
        self, email: MicrosoftGraphEmail
    ) -> Iterable[MicrosoftGraphFileAttachment]:
        """Get ics attachments.

        Args:
            email: {MicrosoftGraphEmail} Parse microsoft graph email.

        Return: {email} ICS attachments list exported from original message.
        """
        parsed_attachments_data = []
        for ics_attachment in email.ics_attachments:
            try:
                self.logger.info(f"Parsing ICS: {ics_attachment.name}")
                parsed_ics_list = (
                    self.email_utils.convert_siemplify_ics_to_connector_msg(
                        ics_attachment.content
                    )
                )

                if len(parsed_ics_list) > 1:
                    file_name, file_extension = os.path.splitext(ics_attachment.name)
                    for index, ics in enumerate(parsed_ics_list, 1):
                        new_file_name = f"{file_name}_{index}{file_extension}"
                        parsed_attachments_data.append((new_file_name, ics))
                elif len(parsed_ics_list) == 1:
                    parsed_attachments_data.append(
                        (ics_attachment.name, parsed_ics_list[0])
                    )

            except (
                ValueError,
                TypeError,
                AttributeError,
                KeyError,
                LookupError,
            ) as err:
                self.logger.error("Failed Parsing ICS content")
                self.logger.exception(err)

        return parsed_attachments_data

    def _attach_file_to_case(self, file_name, file_content):
        self.logger.info("Checking EML and MSG attachments to attach to the case")
        try:
            if isinstance(file_content, str):
                file_content = file_content.encode()
            self.logger.info(f"Attached {file_name} file to the case")
            return create_siemplify_case_wall_attachment_object(file_name, file_content)

        except (AttributeError, KeyError, TypeError) as e:
            self.logger.error(f"Failed to attach {file_name} to the case wall")
            self.logger.exception(e)

        return None

    def process_alert(self, alert: MicrosoftGraphEmail) -> CaseInfo:
        """Process the alert and generate cases based on the alert_per_attachment
            setting.

        Args:
            alert (MicrosoftGraphEmail): The email alert object to be processed.

        Returns:
            CaseInfo: A list containing the created case(s)
        """
        alert.content = alert.mime_content

        if (
            not
            self.params.create_a_separate_google_sec_ops_alert_per_attached_mail_file
        ):
            return [
                self._create_case(
                    alert,
                    self.params.attached_mail_file_prefix,
                    self.params.original_received_mail_prefix,
                    self.params.attach_original_eml,
                )
            ]

        return self._create_cases(
            alert,
            self.params.attached_mail_file_prefix,
            self.params.original_received_mail_prefix,
            self.params.attach_original_eml,
        )

    def _get_item_attachments_data(self, email):
        """
        Get attachments from message.
        :param email: {MicrosoftGraphEmail} If True will load only unread emails.
        :return: {list} Item attachments list exported from original message
        """
        eml_attachments = self._get_eml_attachments(email)
        msg_attachments = self._get_msg_attachments(email)
        ics_attachments = self._get_ics_attachments(email)

        self.logger.info(
            f"Found {len(eml_attachments)} EMLs, {len(msg_attachments)} MSGs and "
            f"{len(ics_attachments)} ICSs for mail with ID: {email.id}"
        )

        return eml_attachments + msg_attachments + ics_attachments

    def _get_events_for_attachments(self, alert: MicrosoftGraphEmail, prefix=None):
        """
        Create and return evens from original message attachments only EML/MSG/ICS.
        :param alert: {MicrosoftGraphEmail} Parsed EML content.
        :param prefix: {str} Prefix for events keys
        :return: list , list events: Events list created from attachments, file_names:
        list of file names only EML/MSG/ICS
        """
        events = []
        attachments = self._get_item_attachments_data(alert)
        for _, value in enumerate(attachments):
            parsed_email_filename, parsed_email = value
            self.logger.info(f"Processing parsed email: {parsed_email_filename}")
            parsed_email_body = parsed_email["body"]["content"] or ""
            parsed_email_subject = parsed_email["subject"] or ""

            additional_info = self._extract_regex_from_content(
                email_subject=parsed_email_subject, email_body=parsed_email_body
            )

            urls, original_src_urls = get_html_urls(parsed_email_body)
            additional_info.update({"urls_from_html_part": original_src_urls})
            additional_info.update({"visible_urls_from_html_part": urls})

            event_data = alert.create_event(
                additional_info=additional_info, attachment_data=parsed_email
            )
            event_data = transform_dict_keys(
                original_dict=event_data,
                prefix=prefix,
                keys_to_except=KEYS_TO_EXCEPT_ON_TRANSFORMATION,
            )

            events.append(event_data)
        return events

    def _create_case(
        self,
        alert: MicrosoftGraphEmail,
        attached_mail_prefix: str,
        original_mail_prefix: str,
        attach_original_attachment: bool,
    ) -> CaseInfo:
        """Create a case from the provided alert, including any associated attachment
            events.

        Args:
            alert (MicrosoftGraphEmail): The email alert object to create a case from.
            attached_mail_prefix (str): The prefix to use for events related to attached
                mail.
            original_mail_prefix (str): The prefix to use for the original mail.
            attach_original_attachment (bool): Whether to attach the original email as
                an attachment in the case.

        Returns:
            CaseInfo: The generated case information, including any events associated
                with the attachments.
        """
        attachment_events = self._get_events_for_attachments(
            alert, attached_mail_prefix
        )
        case_info = self._generate_case_info(
            alert=alert,
            mail_prefix=original_mail_prefix,
            attach_original_attachment=attach_original_attachment,
        )

        case_info.events.extend(attachment_events)
        return case_info

    def _create_cases(
        self,
        alert: MicrosoftGraphEmail,
        attached_mail_prefix: str,
        original_mail_prefix: str,
        attach_original_attachment: bool,
    ) -> CaseInfo:
        """Creates cases from an email alert and its attachments.

        Args:
            alert (MicrosoftGraphEmail): The email alert to process.
            attached_mail_prefix (str): Prefix for the attachment cases.
            original_mail_prefix (str): Prefix for the primary alert case.
            attach_original_attachment (bool): Whether to attach the original email
                to the case.
            email_content (str | None): The content of the email body, if available.
                Defaults to None.

        Returns:
            CaseInfo: A list of generated cases including the primary case and
                attachment cases.
        """
        case_info = self._generate_case_info(
            alert=alert,
            mail_prefix=original_mail_prefix,
            attach_original_attachment=attach_original_attachment,
        )
        cases = [case_info]
        item_attachments = self._get_item_attachments_data(alert)
        for _, attachment_data in item_attachments:
            attachment_case = self._generate_case_info(
                alert=alert,
                mail_prefix=attached_mail_prefix,
                attachment_data=attachment_data,
            )
            attachment_case.events.append(case_info.events[0])
            cases.append(attachment_case)
        return cases

    def _generate_case_info(
        self,
        alert: MicrosoftGraphEmail,
        mail_prefix: str,
        attachment_data: list[defaultdict] = None,
        attach_original_attachment: bool = False,
    ) -> CaseInfo:
        """Generates a CaseInfo object based on alert data."""
        additional_info = self._extract_additional_info(alert)
        event_details = self._create_event_details(
            alert, additional_info, attachment_data, mail_prefix
        )

        case_info = self._initialize_case_info(alert, event_details, attachment_data)
        case_info.environment = self._get_environment(event_details)
        case_info.events = [event_details]

        if attach_original_attachment:
            self._attach_original_email(case_info, alert)

        return case_info

    def _extract_additional_info(self, alert: MicrosoftGraphEmail) -> dict[str, str]:
        """Extracts additional info from email content."""
        text_body_content = alert.parsed_email["uniqueBody"]["content"]
        additional_info = self._extract_regex_from_content(
            email_subject=alert.subject,
            email_body=alert.body_content or text_body_content,
        )
        urls, original_src_urls = get_html_urls(alert.body_content or text_body_content)
        additional_info.update(
            {
                "urls_from_html_part": original_src_urls,
                "visible_urls_from_html_part": urls,
            }
        )
        return additional_info

    def _create_event_details(
        self,
        alert: MicrosoftGraphEmail,
        additional_info: dict[str, str],
        attachment_data: list[defaultdict],
        mail_prefix: str,
    ) -> dict[str, str]:
        """Creates event details with transformation."""
        event_details = alert.create_event(
            additional_info=additional_info,
            attachment_data=attachment_data,
            headers_to_add_to_events=self.params.headers_to_add_to_events,
        )

        if self.params.case_name_template:
            event_details["custom_case_name"] = transform_template_string(
                self.params.case_name_template, event_details
            )

        transformed_event_details = transform_dict_keys(
            original_dict=event_details,
            prefix=mail_prefix,
            keys_to_except=KEYS_TO_EXCEPT_ON_TRANSFORMATION,
        )
        if (
            self.params.case_name_template
            and "custom_case_name" not in transformed_event_details
        ):
            transformed_event_details["custom_case_name"] = transformed_event_details[
                f"{mail_prefix}_custom_case_name"
            ]

        return transformed_event_details

    def _initialize_case_info(
        self,
        alert: MicrosoftGraphEmail,
        event_details: dict[str, str],
        attachment_data: list[defaultdict],
    ) -> CaseInfo:
        """Initializes a CaseInfo object with the given event details."""
        alert_name = transform_template_string(
            self.params.alert_name_template, event_details
        ) if self.params.alert_name_template else ""
        case_info = CaseInfo()
        case_info.name = alert_name or CASE_NAME_PATTERN.format(alert.mailbox_name)
        case_info.rule_generator = case_info.name
        case_info.start_time = convert_datetime_to_unix_time(alert.parsed_time)
        case_info.end_time = convert_datetime_to_unix_time(alert.parsed_time)
        case_info.identifier = alert.internet_message_id
        case_info.ticket_id = f"{alert.internet_message_id}_{int(alert.timestamp)}"
        case_info.display_id = (
            f"{alert.id}_{int(alert.timestamp)}"
            if attachment_data is None
            else str(uuid.uuid4())
        )
        case_info.priority = PRIORITY_DEFAULT
        case_info.device_vendor = event_details.get("device_vendor", "Unknown")
        case_info.device_product = event_details.get("device_product", "Unknown")
        case_info.attachments = self._extract_attachments(alert, attachment_data)
        return case_info

    def _extract_attachments(
        self,
        alert: MicrosoftGraphEmail,
        attachment_data: list[defaultdict],
    ) -> Iterable[Attachment]:
        """Extracts and attaches files to the case if needed."""
        attachments = []
        if attachment_data is None:
            for attachment in alert.file_attachments:
                if (
                    attachment.content_type in SMIME_ATTACHMENT_CONTENT_TYPES
                    and alert.parsed_email["attachments"]
                ):
                    attachment_data, _ = self._get_smime_attachments_from_parsed_alert(
                        attachments_data=alert.parsed_email["attachments"]
                    )
                else:
                    attachment_data = [(attachment.name, attachment.content)]

                for attachment_name, attachment_content in attachment_data:
                    attachment_for_case = self._attach_file_to_case(
                        attachment_name, attachment_content
                    )

                    if attachment_for_case:
                        attachments.append(attachment_for_case)

        return attachments

    def _get_smime_attachments_from_parsed_alert(
        self,
        attachments_data: SingleJson,
    ) -> tuple(list(tuple(str, bytes)), list(tuple(str, bytes))):
        attachment_data = []
        smime_event_type_attachments: list[tuple[str, bytes]] = []
        index = 0
        while True:
            attachment_name: str | None = attachments_data.get(
                f"attachment_name_{index}"
            )
            attachment_content_b64: str | None = attachments_data.get(
                f"base64_encoded_content_{index}"
            )

            if attachment_name is None and attachment_content_b64 is None:
                break

            attachment_content: bytes = base64.b64decode(
                attachment_content_b64.encode()
            )
            if self._is_event_type_attachment(attachment_name):
                smime_event_type_attachments.append(
                    (attachment_name, attachment_content)
                )
            else:
                attachment_data.append((attachment_name, attachment_content))

            index += 1

        return attachment_data, smime_event_type_attachments

    def _is_event_type_attachment(self, attachment_name: str) -> bool:
        attachment_extension = attachment_name.split(".")[-1]
        if attachment_extension in ["ics", "msg", "eml"]:
            return True

        return False

    def _get_environment(self, event_details: dict[str, str]) -> str:
        """Retrieves the environment based on event details."""
        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify=self.siemplify,
            environment_field_name=self.params.environment_field_name,
            environment_regex_pattern=self.params.environment_regex_pattern,
        )
        return environment_common.get_environment(event_details)

    def _attach_original_email(self, case_info: CaseInfo, alert: MicrosoftGraphEmail):
        """Attaches the original email as an EML file to the case."""
        try:
            attachment_object = create_eml_object(
                original_email_content=alert.content,
                attachment_name=alert.subject or EMPTY_EMAIL_SUBJECT,
            )
            case_info.attachments.append(attachment_object)
            self.logger.info("Successfully attached original message as EML.")
        except exceptions.InvalidAttachment as e:
            self.logger.error(f"Failed to attach original EML. Error: {e}.")


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = MicrosoftGraphMailDelegatedConnector(is_test)
    connector.start()
