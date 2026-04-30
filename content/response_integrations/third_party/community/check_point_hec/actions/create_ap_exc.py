from ..core.base_action import BaseAction
from ..core.constants import CREATE_AP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully created Anti-Phishing exception!"
ERROR_MESSAGE: str = "Failed creating Anti-Phishing exception!"


class CreateAPException(BaseAction):

    def __init__(self) -> None:
        super().__init__(CREATE_AP_EXC_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.exception_type = self.soar_action.extract_action_param(
            param_name="Exception Type",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.entity_id = self.soar_action.extract_action_param(
            param_name="Entity ID",
            print_value=True,
            is_mandatory=False
        )
        self.params.attachment_md5 = self.soar_action.extract_action_param(
            param_name="Attachment MD5",
            print_value=True,
            is_mandatory=False
        )
        self.params.from_email = self.soar_action.extract_action_param(
            param_name="From Email",
            print_value=True,
            is_mandatory=False
        )
        self.params.nickname = self.soar_action.extract_action_param(
            param_name="Nickname",
            print_value=True,
            is_mandatory=False
        )
        self.params.recipient = self.soar_action.extract_action_param(
            param_name="Recipient",
            print_value=True,
            is_mandatory=False
        )
        self.params.sender_client_ip = self.soar_action.extract_action_param(
            param_name="Sender Client IP",
            print_value=True,
            is_mandatory=False
        )
        self.params.from_domain_ends_with = self.soar_action.extract_action_param(
            param_name="From Domain Ends With",
            print_value=True,
            is_mandatory=False
        )
        self.params.sender_ip = self.soar_action.extract_action_param(
            param_name="Sender IP",
            print_value=True,
            is_mandatory=False
        )
        self.params.email_link = self.soar_action.extract_action_param(
            param_name="Email Link",
            print_value=True,
            is_mandatory=False
        )
        self.params.subject = self.soar_action.extract_action_param(
            param_name="Subject",
            print_value=True,
            is_mandatory=False
        )
        self.params.comment = self.soar_action.extract_action_param(
            param_name="Comment",
            print_value=True,
            is_mandatory=False
        )
        self.params.action_needed = self.soar_action.extract_action_param(
            param_name="Action Needed",
            print_value=True,
            is_mandatory=False
        )
        self.params.ignoring_spf_check = self.soar_action.extract_action_param(
            param_name="Ignoring SPF Check",
            print_value=True,
            is_mandatory=False,
            input_type=bool
        )
        self.params.subject_matching = self.soar_action.extract_action_param(
            param_name="Subject Matching",
            print_value=True,
            is_mandatory=False
        )
        self.params.email_link_matching = self.soar_action.extract_action_param(
            param_name="Email Link Matching",
            print_value=True,
            is_mandatory=False
        )
        self.params.from_name_matching = self.soar_action.extract_action_param(
            param_name="From Name Matching",
            print_value=True,
            is_mandatory=False
        )
        self.params.from_domain_matching = self.soar_action.extract_action_param(
            param_name="From Domain Matching",
            print_value=True,
            is_mandatory=False
        )
        self.params.from_email_matching = self.soar_action.extract_action_param(
            param_name="From Email Matching",
            print_value=True,
            is_mandatory=False
        )
        self.params.recipient_matching = self.soar_action.extract_action_param(
            param_name="Recipient Matching",
            print_value=True,
            is_mandatory=False
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        entity_id = self.params.entity_id
        attachment_md5 = self.params.attachment_md5
        from_email = self.params.from_email
        nickname = self.params.nickname
        recipient = self.params.recipient
        sender_client_ip = self.params.sender_client_ip
        from_domain_ends_with = self.params.from_domain_ends_with
        sender_ip = self.params.sender_ip
        email_link = self.params.email_link
        subject = self.params.subject
        comment = self.params.comment
        action_needed = self.params.action_needed
        ignoring_spf_check = self.params.ignoring_spf_check
        subject_matching = self.params.subject_matching
        email_link_matching = self.params.email_link_matching
        from_name_matching = self.params.from_name_matching
        from_domain_matching = self.params.from_domain_matching
        from_email_matching = self.params.from_email_matching
        recipient_matching = self.params.recipient_matching

        exception = {
            "entityId": entity_id,
            "attachmentMd5": attachment_md5,
            "senderEmail": from_email,
            "senderName": nickname,
            "recipient": recipient,
            "senderClientIp": sender_client_ip,
            "senderDomain": from_domain_ends_with,
            "senderIp": sender_ip,
            "linkDomains": email_link,
            "subject": subject,
            "comment": comment,
            "actionNeeded": action_needed,
            "ignoringSpfCheck": ignoring_spf_check,
            "subjectMatching": subject_matching,
            "linkDomainMatching": email_link_matching,
            "senderNameMatching": from_name_matching,
            "senderDomainMatching": from_domain_matching,
            "senderEmailMatching": from_email_matching,
            "recipientMatching": recipient_matching,
        }
        self.api_client.create_ap_exception(exception_type, exception)


def main() -> None:
    CreateAPException().run()


if __name__ == "__main__":
    main()
