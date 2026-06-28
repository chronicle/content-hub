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

import binascii
import sys

import asyncio

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import AsyncConnector
from TIPCommon.base.utils import coros_to_tasks_with_limit
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.data_models import BaseAlert
from TIPCommon.smp_io import read_ids
from TIPCommon.smp_io import write_ids
from TIPCommon.smp_time import unix_now
from TIPCommon.utils import is_test_run
from TIPCommon.validation import ParameterValidator

from gmail.core.GoogleGmailApiManager import GoogleGmailApiManager
from gmail.core.GoogleGmailAuth import build_auth_manager
from gmail.core import GoogleGmailConsts
from gmail.core.GoogleGmailDatamodel import GmailMessage
from gmail.core.GoogleGmailDatamodel import GmailMessagePart
from gmail.core.GoogleGmailDatamodel import MailboxReadEnum
from gmail.core.GoogleGmailServices import MessagesService, LabelsService
from gmail.core.GoogleGmailUtils import build_regex_map
from gmail.core.GoogleGmailUtils import extract_regex_from_content
from gmail.core.GoogleGmailUtils import get_html_urls
from gmail.core.GoogleGmailUtils import transform_dict_keys, transform_template_string


class GoogleGmailConnector(AsyncConnector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gmail_service: MessagesService | None = None
        self.labels_service: LabelsService | None = None
        self.regex_map = build_regex_map(self.logger, self.siemplify.whitelist)

    def validate_params(self) -> None:
        """Validate connector parameters."""
        validator = ParameterValidator(self.siemplify)

        self.params.default_mailbox = validator.validate_email(
            param_name="Default Mailbox",
            email=self.params.default_mailbox
        )
        self.params.max_hours_backwards = validator.validate_positive(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_backwards
        )
        self.params.max_emails_per_cycle = validator.validate_range(
            param_name="Max Emails Per Cycle",
            value=self.params.max_emails_per_cycle,
            min_limit=1,
            max_limit=GoogleGmailConsts.MAX_EMAILS_PER_CYCLE_LIMIT
        )

        self.params.label_list = validator.validate_csv(
            param_name="Labels Filter",
            csv_string=self.params.labels_filter
        )
        self.params.headers_to_add_to_events_list = validator.validate_csv(
            param_name="Extract Headers",
            csv_string=self.params.extract_headers
        )
        self.params.mailbox_read_status = getattr(
            MailboxReadEnum,
            validator.validate_ddl(
                param_name="Email Status",
                value=self.params.email_status,
                ddl_values=[el.name for el in MailboxReadEnum]
            ).upper()
        )

    def init_managers(self) -> None:
        """Init Auth and API managers, prepare Messages Service."""
        auth_manager = build_auth_manager(
            self.siemplify,
            self.params.default_mailbox
        )
        api_client = GoogleGmailApiManager(
            auth_manager.prepare_session()
        )

        self.gmail_service = MessagesService(
            api_manager=api_client,
            logger=self.logger,
            user_email=self.params.default_mailbox
        )
        self.labels_service = LabelsService(
            api_manager=api_client,
            logger=self.logger,
            user_email=self.params.default_mailbox
        )

    def read_context_data(self) -> None:
        self.context.existing_ids = read_ids(self.siemplify)
        self.context.read_emails = []

    def write_context_data(
            self,
            _: list[BaseAlert],
            __: list[BaseAlert]
    ) -> None:
        """Write connector context data into FS or DB."""
        write_ids(self.siemplify, self.context.existing_ids)

    def get_last_success_time(self, *_) -> int:
        """Get last_success_time for connector from DB (or FileStorage)."""
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            time_format=UNIX_FORMAT
        )

    def set_last_success_time(
            self,
            filtered_alerts: list[GmailMessage],
            unprocessed_alerts: list[GmailMessage],
            *_
    ):
        """Set last_success_time for connector to DB (or FileStorage)."""
        super().set_last_success_time(
            filtered_alerts,
            unprocessed_alerts,
            timestamp_key="internal_date"
        )

    def store_alert_in_cache(self, alert: GmailMessage):
        self.context.existing_ids.append(alert.alert_id)
        self.context.read_emails.append(alert.id)

    async def get_alerts(self) -> list[GmailMessage]:
        """Fetch new emails from Gmail service."""
        self.context.labels_map = {
            label.id: label.name
            for label in await self.labels_service.list_labels()
        }

        return await self.gmail_service.list_messages(
            after_ts=self.get_last_success_time() // NUM_OF_MILLI_IN_SEC,
            labels=self.params.label_list,
            limit=self.params.max_emails_per_cycle,
            skip_ids=set(self.context.existing_ids),
            mailbox_read_status=self.params.mailbox_read_status,
        )

    def filter_alerts(self, alerts: list[GmailMessage]) -> list[GmailMessage]:
        """Filter email messages."""
        if not self.params.email_exclude_pattern:
            return alerts

        filtered_alerts = []
        for message in alerts:
            if message.matches_exclude_pattern(self.params.email_exclude_pattern):
                self.context.read_emails.append(message.alert_id)
                continue

            filtered_alerts.append(message)

        return filtered_alerts

    async def process_alert(self, alert: GmailMessage) -> GmailMessage:
        """Load additional data for the email message."""
        await self.gmail_service.enrich_attachments(
            message_id=alert.id,
            message_part=alert.payload
        )

        if self.params.attach_original_eml:
            await self.gmail_service.set_message_mime_content(alert)

        return alert

    def prepare_additional_info(
            self,
            message: GmailMessage,
            message_part: GmailMessagePart | None = None
    ) -> dict[str, str]:
        """Prepare additional info for the event."""
        if message_part is None:
            message_part = message.payload
            additional_info = {
                "event_name":  GoogleGmailConsts.ORIGINAL_EMAIL_EVENT_NAME,
            }
            additional_info.update(message.to_flat())
            additional_info["label_names"] = ",".join(
                self.context.labels_map.get(_id) for _id in message.label_ids
            )
        else:
            additional_info = {
                "event_name": GoogleGmailConsts.ATTACHED_EMAIL_EVENT_NAME,
                "original_email_id": message.alert_id
            }

        additional_info["device_product"] = GoogleGmailConsts.DEVICE_PRODUCT
        additional_info["device_vendor"] = GoogleGmailConsts.VENDOR
        additional_info["monitored_mailbox_name"] = self.gmail_service.user_email
        additional_info["attachment_sha1_hashes"] = ",".join(
            file_attachment.sha1_hash
            for file_attachment in message_part.file_attachments
            if file_attachment.sha1_hash is not None
        )

        additional_info.update(
            extract_regex_from_content(
                regex_map=self.regex_map,
                email_subject=message_part.subject,
                email_bodies=message_part.html_bodies + message_part.text_bodies
            )
        )
        urls, original_src_urls = get_html_urls(message_part.html_bodies)
        additional_info.update({"urls_from_html_part": original_src_urls})
        additional_info.update({"visible_urls_from_html_part": urls})

        return additional_info

    def generate_case_info(
            self,
            message: GmailMessage,
            message_part: GmailMessagePart | None = None
    ) -> AlertInfo:
        """Generate a SOAR Alert Info object.

        Args:
            message (GmailMessage): Message that Alert Info originates from.
            message_part (GmailMessagePart): Message body to be used for event data.

        Returns:
            AlertInfo: Alert Info object.
        """
        additional_info = self.prepare_additional_info(message, message_part)

        is_attached = True
        if message_part is None:
            is_attached = False
            message_part = message.payload

        mail_prefix = (
            self.params.original_mail_file_prefix if not is_attached
            else self.params.attached_mail_file_prefix
        )

        event_details = message_part.create_event(
            additional_info=additional_info,
            headers_to_add_to_events=self.params.headers_to_add_to_events_list,
        )

        # Construct case name if case name template provided
        case_name = (
            transform_template_string(self.params.case_name_template, event_details)
            if self.params.case_name_template else ""
        )
        # Construct alert name if alert name template provided
        alert_name = (
            transform_template_string(self.params.alert_name_template, event_details)
            if self.params.alert_name_template else ""
        )

        event_details = transform_dict_keys(
            original_dict=event_details,
            prefix=mail_prefix,
            keys_to_except=GoogleGmailConsts.KEYS_TO_EXCEPT_ON_TRANSFORMATION
        )
        if case_name:
            event_details["custom_case_name"] = case_name

        # Create case info object
        alert_info = AlertInfo()
        alert_info.name = (
            alert_name
            or GoogleGmailConsts.CASE_NAME_PATTERN.format(self.gmail_service.user_email)
        )
        alert_info.rule_generator = alert_info.name
        alert_info.source_grouping_identifier = message.thread_id
        alert_info.start_time = message.internal_date
        alert_info.end_time = message.internal_date
        alert_info.priority = GoogleGmailConsts.PRIORITY_DEFAULT
        alert_info.display_id = (
            message.alert_id if not is_attached else
            f"{message.alert_id}_attachment_{message_part.body.attachment_id}"
        )
        alert_info.ticket_id = message.alert_id

        alert_info.device_vendor = event_details["device_vendor"]
        alert_info.device_product = event_details["device_product"]
        alert_info.attachments = []
        alert_info.environment = self.env_common.get_environment(event_details)
        alert_info.events = [event_details]

        # Attachments are set only for original email
        if is_attached:
            return alert_info

        for attachment in message_part.file_attachments:
            try:
                alert_info.attachments.append(
                    attachment.create_case_wall_attachment_object()
                )
            except (binascii.Error, TypeError, UnicodeDecodeError, ValueError) as e:
                self.logger.error(
                    f"Error creating case wall attachment for email {message.alert_id} "
                    f"attachment {attachment.filename}. Error is {e}"
                )

        if self.params.attach_original_eml and message.mime_content:
            alert_info.attachments.append(
                message.create_case_wall_attachment_object()
            )

        return alert_info

    def create_alert_info(self, alert: GmailMessage) -> AlertInfo:
        """Create single SOAR alert info from gmail message."""
        events = []

        for attachment in alert.payload.file_attachments:
            if not attachment.filename.endswith(".eml"):
                continue

            events.append(
                transform_dict_keys(
                    attachment.create_event(
                        additional_info=self.prepare_additional_info(
                            message=alert,
                            message_part=attachment
                        ),
                        headers_to_add_to_events=(
                            self.params.headers_to_add_to_events_list
                        ),
                    ),
                    prefix=self.params.attached_mail_file_prefix,
                    keys_to_except=GoogleGmailConsts.KEYS_TO_EXCEPT_ON_TRANSFORMATION,
                )
            )

        alert_info = self.generate_case_info(alert)
        alert_info.events.extend(events)
        return alert_info

    def create_alert_infos(self, alert: GmailMessage) -> list[AlertInfo]:
        """Create multiple SOAR alerts info from gmail message."""
        alert_infos = [
            self.generate_case_info(message=alert, message_part=attachment)
            for attachment in alert.payload.file_attachments
            if attachment.filename.endswith(".eml")
        ]
        alert_infos.append(self.generate_case_info(alert))
        return alert_infos

    @property
    def multiple_alerts_mode_enabled(self) -> bool:
        return self.params.create_alert_per_attachment_file

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return (
            not self.params.disable_overflow
            and super().is_overflow_alert(alert_info)
        )

    async def process_alerts(
            self,
            filtered_alerts: list[GmailMessage],
            timeout_threshold: float = TIMEOUT_THRESHOLD
    ) -> tuple[list[AlertInfo], list[GmailMessage]]:
        """Main alert processing loop.
        Steps for each alert object:

        1. Schedule alert processing, once completed
        1. Check if connector is approaching timeout
        2. Check max alert count for test run
        3. Check max alert count for commercial run (override)
        4. Remove alert from unprocessed_alerts list
        5. Check if alert pass filters
        6. Store alert in cache (id.json etc) (override)
        7. Create AlertInfo object
        8. Check is alert overflowed
        9. append alert to processed alerts

        Args:
            filtered_alerts (list[BaseAlert]):list of filtered BaseAlert objects
            timeout_threshold (float, optional): timeout threshold for connector
                execution. Defaults to 0.9

        Note:
            To provide other value for timeout threshold,
            you can override this method as follows::

                my_threshold = 0.9
                def process_alerts(self, filtered_alerts, timeout_threshold):
                    return super().process_alerts(filtered_alerts, my_threshold)

        Returns:
            tuple containing a list of AlertInfo objects,
            and a list of BaseAlert objects
        """
        unprocessed_alerts = filtered_alerts.copy()
        processed_alerts = []
        processed_alerts_tasks = coros_to_tasks_with_limit(
            (self.process_alert(alert) for alert in filtered_alerts),
            limit=self.coros_limit
        )

        processing_time = (
            (unix_now() - self.connector_start_time) / NUM_OF_MILLI_IN_SEC
        )
        concurrent_timeout = (
            (self.params.python_process_timeout - processing_time)
            * timeout_threshold
        )

        try:
            for processed_alerts_cor in asyncio.as_completed(
                processed_alerts_tasks,
                timeout=concurrent_timeout,
            ):
                try:
                    if self.is_test_run and processed_alerts:
                        self.logger.info(
                            "Maximum alert count (1) for test run reached!"
                        )
                        break

                    if self.max_alerts_processed(processed_alerts):
                        self.logger.info(
                            f"Maximum alert count {len(processed_alerts)} "
                            f"for connector execution reached!."
                        )
                        break

                    processed_alert = await processed_alerts_cor
                    unprocessed_alerts.remove(processed_alert)

                    if not self.pass_filters(processed_alert):
                        self.logger.info(
                            f"Alert {processed_alert.alert_id} did not pass "
                            "filters. Skipping..."
                        )
                        continue

                    self.store_alert_in_cache(processed_alert)
                    self.logger.info(
                        f"Alert {processed_alert.alert_id} processed "
                        f"successfully"
                    )

                    if self.multiple_alerts_mode_enabled:
                        alert_infos = self.create_alert_infos(processed_alert)
                    else:
                        alert_infos = [self.create_alert_info(processed_alert)]

                    for alert_info in alert_infos:
                        self.logger.info(
                            f"Created AlertInfo object for alert "
                            f"{processed_alert.alert_id}"
                        )

                        if self.is_overflow_alert(alert_info):
                            self.logger.info(
                                f"{alert_info.rule_generator}-"
                                f"{alert_info.ticket_id}-"
                                f"{alert_info.environment}-"
                                f"{alert_info.device_product} "
                                "found as overflow alert. Skipping."
                            )
                            # If is overflowed we should skip
                            continue

                        processed_alerts.append(alert_info)
                        self.logger.info(
                            f"Finished processing {processed_alert.alert_id}"
                        )

                except asyncio.TimeoutError:
                    raise

                # pylint: disable=broad-exception-caught
                # We want to catch any exception here, and its being logged properly
                except Exception as e:
                    self.logger.error(
                        f"Failed to process alert. Error is: {e}"
                    )
                    self.logger.exception(e)

                    if self.is_test_run:
                        raise

        except asyncio.TimeoutError:
            self.logger.info(
                "Timeout is approaching. Connector will gracefully exit"
            )

        finally:
            for task in processed_alerts_tasks:
                if not task.done():
                    task.cancel()

        return processed_alerts, unprocessed_alerts

    async def finalize(self) -> None:
        """Finalize connector: acknowledge messages and close session."""
        if self.gmail_service is None:
            return

        if not self.is_test_run and getattr(self.params, "mark_emails_as_read", False):
            await self.gmail_service.mark_messages_as_read(self.context.read_emails)

        await self.gmail_service.api_manager.close()


async def main() -> None:
    """main"""
    script_name = GoogleGmailConsts.GOOGLE_GMAIL_CONNECTOR
    is_test = is_test_run(sys.argv)
    connector = GoogleGmailConnector(script_name, is_test)
    await asyncio.ensure_future(connector.start())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
