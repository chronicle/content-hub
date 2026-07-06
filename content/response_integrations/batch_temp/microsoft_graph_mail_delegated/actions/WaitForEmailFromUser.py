from __future__ import annotations

from typing import NoReturn

from collections.abc import Iterable, MutableMapping, MutableSequence

import dataclasses
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator

from ..core.AsyncActionBaseClass import ActionResult, AsyncActionBaseClass
from ..core.MicrosoftGraphMailDelegatedManager import ApiManager
from ..core import constants
from ..core import exceptions
from ..core.datamodels import MicrosoftGraphEmail
from ..core import utils


@dataclasses.dataclass(slots=True)
class ActionData:
    recipients: MutableSequence[str]
    recipients_replies: MutableMapping[str, MicrosoftGraphEmail]


class WaitForMailFromUserAction(AsyncActionBaseClass):

    def __init__(self, siemplify):
        super().__init__(siemplify)
        self.attachments = {}
        self.results = ActionData(recipients=[], recipients_replies={})

    def _extract_action_configuration(self) -> None:
        self.params.email_id = extract_action_param(
            siemplify=self.siemplify,
            param_name="Mail ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.wait_for_all_recipients = extract_action_param(
            siemplify=self.siemplify,
            param_name="Wait for All Recipients to Reply?",
            input_type=bool,
            print_value=True,
        )
        self.params.body_exclude_pattern = extract_action_param(
            siemplify=self.siemplify,
            param_name="Wait Stage Exclude pattern",
            print_value=True,
        )
        self.params.folder_name = extract_action_param(
            siemplify=self.siemplify,
            param_name="Folder to Check for Reply",
            default_value="Inbox",
            print_value=True,
        )
        self.params.fetch_attachments = extract_action_param(
            siemplify=self.siemplify,
            param_name="Fetch Response Attachments",
            input_type=bool,
            default_value=False,
            print_value=True,
        )
        self.params.limit_json_result = extract_action_param(
            siemplify=self.siemplify,
            param_name="Limit the Amount of Information Returned in the JSON Result",
            input_type=bool,
            default_value=True,
            print_value=True
        )

        self.params.disable_json_result = extract_action_param(
            siemplify=self.siemplify,
            param_name="Disable the Action JSON Result",
            input_type=bool,
            default_value=False,
            print_value=True
        )

    def _validate_params(self, validator: ParameterValidator) -> None:
        pass

    def _perform_action(self, manager: ApiManager) -> ActionResult:
        manager.mail_address = utils.validate_mailbox(
            manager,
            mailbox=manager.mail_address,
            default_mailbox=manager.mail_address,
        )
        email = self._get_email(manager)
        email_replies = self._get_email_replies(manager=manager, email=email)
        recipients_replies = self._find_email_per_recipient(
            replies=email_replies,
            recipients_list=email.recipients,
        )
        self._set_action_result(
            recipients=email.recipients,
            recipients_replies=recipients_replies,
        )
        self._set_result_json(recipients_replies)
        self._set_data_table(recipients_replies)
        if self.params.fetch_attachments:
            self._set_attachments_to_case(manager, recipients_replies)

        self._log_messages()

        return self._finalize_action()

    def _get_email(self, manager: ApiManager) -> MicrosoftGraphEmail:
        folder = manager.get_folder_by_name(self.params.folder_name)
        email = manager.get_mail_details(folder=folder, email_id=self.params.email_id)
        email.reply_folder_id = folder.id
        self.logger.info(self._found_email_msg)

        return email

    def _get_email_replies(
        self,
        manager: ApiManager,
        email: MicrosoftGraphEmail,
    ) -> MutableSequence[MicrosoftGraphEmail]:
        try:
            email_replies = manager.get_all_replies(
                email=email,
                internet_message_id=email.internet_message_id,
                filter_with_extended_property=True,
            )

        except exceptions.MicrosoftGraphMailManagerError as e:
            self.logger.exception(e)
            email_replies = []

        if not email_replies:
            email_replies = manager.get_all_replies(
                email=email,
                conversation_id=email.conversation_id,
            )

        return utils.get_emails_with_updated_metadata(
            manager=manager,
            emails=email_replies,
            smime_auth=self.params.smime_auth,
        )

    def _find_email_per_recipient(
        self,
        replies: MutableSequence[MicrosoftGraphEmail],
        recipients_list: Iterable[str],
    ) -> MutableMapping[str, MicrosoftGraphEmail]:
        """Reviews list of emails found on the server and maps each to a recipient from
            the recipients list.

        Args:
            replies (MutableSequence[MicrosoftGraphEmail]): List of MicrosoftGraphEmail
            objects
            recipients_list (Iterable[str]): List of recipient emails

        Returns:
            MutableMapping[str, MicrosoftGraphEmail]: Map of recipients responses.
        """
        recipients_responses: MutableMapping[str, MicrosoftGraphEmail] = {}
        for recipient in recipients_list:
            email = utils.get_recipient_first_valid_reply(
                sender=recipient,
                replies=replies,
                body_exclude_pattern=self.params.body_exclude_pattern,
                logger=self.logger,
            )
            if email:
                recipients_responses[recipient] = email

        self.logger.info(f"Gathered responses: {list(recipients_responses.keys())}")

        return recipients_responses

    def _set_action_result(
        self,
        recipients: MutableSequence[str],
        recipients_replies: MutableMapping[str, MicrosoftGraphEmail],
    ) -> None:
        self.results.recipients = recipients
        self.results.recipients_replies = recipients_replies

    def _set_result_json(
        self,
        recipients_replies: MutableMapping[str, MicrosoftGraphEmail],
    ) -> None:
        if not self.params.disable_json_result:
            reply_data = [
                self._set_recipient_result(recipient, reply)
                for recipient, reply in recipients_replies.items()
            ]

            self.siemplify.result.add_result_json({"Responses": reply_data})

    def _set_recipient_result(
        self,
        recipient: str,
        reply: MicrosoftGraphEmail,
    ) -> MutableMapping[str, str]:

        if self.params.limit_json_result:
            compact_reply = reply.to_compact_json()
            return {
                "recipient": recipient,
                "content": compact_reply,
            }

        return {"recipient": recipient, "content": reply.to_json()}

    def _set_data_table(
        self,
        recipients_replies: MutableMapping[str, MicrosoftGraphEmail],
    ) -> None:
        if not recipients_replies:
            return

        table_result = self._set_csv_data(recipients_replies.values())
        self.siemplify.result.add_data_table(constants.CASE_TABLE_NAME, table_result)

    def _set_csv_data(self, emails: Iterable[MicrosoftGraphEmail]) -> list[list[str]]:
        return construct_csv([email.to_table() for email in emails])

    def _set_attachments_to_case(
        self,
        manager: ApiManager,
        recipients_replies: MutableMapping[str, MicrosoftGraphEmail],
    ) -> None:
        for recipient in recipients_replies.values():
            if not recipient.has_attachments:
                continue

            attachments = utils.get_attachments(manager=manager, email=recipient)
            self.attachments.update({recipient.sender: attachments})

        self._add_attachments(manager)

    def _add_attachments(self, manager: ApiManager) -> None:
        """Save attachment file to the attachment result for the case."""
        for recipient, attachments in self.attachments.items():
            for attachment in attachments:
                if attachment.is_item_attachment:
                    attachment.content_bytes = utils.encode_content_as_base64(
                        manager.load_attachment_content(
                            folder_id=attachment.folder_id,
                            email_id=attachment.email_id,
                            attachment_id=attachment.id,
                            mail_address=attachment.mailbox_name,
                        )
                    )

                self.siemplify.result.add_attachment(
                    title=f"recipient {recipient} reply attachment",
                    filename=f"{attachment.name}",
                    file_contents=attachment.content_bytes_as_b64_string
                    if attachment.is_smime
                    else attachment.content_bytes,
                )
                self.logger.info(
                    f'Attachment "{attachment.name}" saved for "{recipient}".'
                )

        if self.attachments:
            self.siemplify.logger.info("Saved all attachments to the case.")

    def is_processing_completed(self) -> bool:
        """Identifies if email processing has been completed.

        Returns:
            bool: True - We have successfully received all the responses.
            False - otherwise.
        """
        results = [
            self.results.recipients_replies.get(r) for r in self.results.recipients
        ]

        if not self.params.wait_for_all_recipients:
            return any(results)

        return all(results)

    def _finalize_action(self) -> ActionResult:
        if self._is_timeout():
            return self._finalize_action_on_timeout()

        if not self.is_processing_completed():
            return self._finalize_action_on_inprogress()

        return self._finalize_action_on_success()

    def _finalize_action_on_timeout(self) -> ActionResult:
        if self.results.recipients_replies:
            self.output_messages.append(self._timeout_with_success_msg)

            return ActionResult(ExecutionState.TIMED_OUT, False)

        self.output_messages.append(self._timeout_with_failure_msg)

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_inprogress(self) -> ActionResult:
        self.output_messages.append(self._in_progress_msg)

        return ActionResult(ExecutionState.IN_PROGRESS, True)

    def _finalize_action_on_failure(self) -> ActionResult:
        pass

    def _finalize_action_on_success(self) -> ActionResult:
        self.output_messages.append(self._success_msg)

        return ActionResult(ExecutionState.COMPLETED, True)

    def _log_messages(self) -> None:
        pass

    @property
    def _found_email_msg(self) -> str:
        return (
            f'The email retrieved successfully with email_id="{self.params.email_id}" '
            f'in folder="{self.params.folder_name}"'
        )

    @property
    def _timeout_with_success_msg(self) -> str:
        recipients = ", ".join(self.results.recipients_replies.keys())
        return (
            "The action reached a timeout when waiting for a reply from the "
            f"users {recipients}"
        )

    @property
    def _timeout_with_failure_msg(self) -> str:
        return "The action failed to receive any replies before the timeout."

    @property
    def _in_progress_msg(self) -> str:
        return (
            "Continuing...waiting for response, searching IN-REPLY-TO "
            f'"{self.params.email_id}".'
        )

    @property
    def _success_msg(self) -> str:
        recipients = ", ".join(self.results.recipients_replies.keys())
        return f"The action found the reply for users: {recipients}"


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.WAIT_FOR_MAIL_FROM_USER_SCRIPT_NAME
    action = WaitForMailFromUserAction(siemplify)
    action.run()


if __name__ == "__main__":
    main()
