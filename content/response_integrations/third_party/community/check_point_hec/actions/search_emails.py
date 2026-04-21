import yaml

from ..core.base_action import BaseAction
from ..core.constants import SEARCH_EMAILS_SCRIPT_NAME, DATE_FORMAT, SAAS_APPS_TO_SAAS_NAMES, \
    CP_DETECTION_VALUES, MS_DETECTION_VALUES, CP_QUARANTINED_VALUES, MS_QUARANTINED_VALUES

SUCCESS_MESSAGE: str = "Successfully got Emails!"
ERROR_MESSAGE: str = "Failed getting Emails!"


class SearchEmails(BaseAction):

    def __init__(self) -> None:
        super().__init__(SEARCH_EMAILS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.start_date = self.soar_action.extract_action_param(
            param_name="Date From",
            print_value=True,
            is_mandatory=True,
        )
        self.params.end_date = self.soar_action.extract_action_param(
            param_name="Date To",
            print_value=True,
            is_mandatory=False,
        )
        self.params.saas = self.soar_action.extract_action_param(
            param_name="SaaS",
            print_value=True,
            is_mandatory=True,
        )
        self.params.direction = self.soar_action.extract_action_param(
            param_name="Direction",
            print_value=True,
            is_mandatory=False,
        )
        self.params.subject_contains = self.soar_action.extract_action_param(
            param_name="Subject Contains",
            print_value=True,
            is_mandatory=False,
        )
        self.params.subject_match = self.soar_action.extract_action_param(
            param_name="Subject Match",
            print_value=True,
            is_mandatory=False,
        )
        self.params.sender_contains = self.soar_action.extract_action_param(
            param_name="Sender Contains",
            print_value=True,
            is_mandatory=False,
        )
        self.params.sender_match = self.soar_action.extract_action_param(
            param_name="Sender Match",
            print_value=True,
            is_mandatory=False,
        )
        self.params.domain = self.soar_action.extract_action_param(
            param_name="Domain",
            print_value=True,
            is_mandatory=False,
        )
        self.params.cp_detection = self.soar_action.extract_action_param(
            param_name="CP Detection",
            print_value=True,
            is_mandatory=False,
            default_value="",
        )
        self.params.ms_detection = self.soar_action.extract_action_param(
            param_name="MS Detection",
            print_value=True,
            is_mandatory=False,
            default_value="",
        )
        self.params.detection_op = self.soar_action.extract_action_param(
            param_name="Detection Op",
            print_value=True,
            is_mandatory=False,
            default_value="OR",
        )
        self.params.server_ip = self.soar_action.extract_action_param(
            param_name="Server IP",
            print_value=True,
            is_mandatory=False,
        )
        self.params.recipients_contains = self.soar_action.extract_action_param(
            param_name="Recipients Contains",
            print_value=True,
            is_mandatory=False,
        )
        self.params.recipients_match = self.soar_action.extract_action_param(
            param_name="Recipients Match",
            print_value=True,
            is_mandatory=False,
        )
        self.params.links = self.soar_action.extract_action_param(
            param_name="Links",
            print_value=True,
            is_mandatory=False,
        )
        self.params.message_id = self.soar_action.extract_action_param(
            param_name="Message ID",
            print_value=True,
            is_mandatory=False,
        )
        self.params.cp_quarantined_state = self.soar_action.extract_action_param(
            param_name="CP Quarantined State",
            print_value=True,
            is_mandatory=False,
        )
        self.params.ms_quarantined_state = self.soar_action.extract_action_param(
            param_name="MS Quarantined State",
            print_value=True,
            is_mandatory=False,
        )
        self.params.quarantined_state_op = self.soar_action.extract_action_param(
            param_name="Quarantined State Op",
            print_value=True,
            is_mandatory=False,
            default_value="OR",
        )
        self.params.name_contains = self.soar_action.extract_action_param(
            param_name="Name Contains",
            print_value=True,
            is_mandatory=False,
        )
        self.params.name_match = self.soar_action.extract_action_param(
            param_name="Name Match",
            print_value=True,
            is_mandatory=False,
        )
        self.params.client_ip = self.soar_action.extract_action_param(
            param_name="Client IP",
            print_value=True,
            is_mandatory=False,
        )
        self.params.attachment_md5 = self.soar_action.extract_action_param(
            param_name="Attachment MD5",
            print_value=True,
            is_mandatory=False,
        )

    def _perform_action(self, _=None) -> None:
        start_date = self.params.start_date
        end_date = self.params.end_date
        saas = SAAS_APPS_TO_SAAS_NAMES[self.params.saas] if self.params.saas else None
        direction = self.params.direction
        subject_contains = self.params.subject_contains
        subject_match = self.params.subject_match
        sender_contains = self.params.sender_contains
        sender_match = self.params.sender_match
        domain = self.params.domain
        cp_detection = [CP_DETECTION_VALUES[detection] for detection in \
                        yaml.safe_load(self.params.cp_detection) if detection != ''] if (self.params.cp_detection != '') else None
        if cp_detection == ['']:
            cp_detection = None
        ms_detection = [MS_DETECTION_VALUES[detection] for detection in \
                        yaml.safe_load(self.params.ms_detection) if detection != ''] if (self.params.ms_detection != '') else None
        if ms_detection == ['']:
            ms_detection = None
        detection_op = self.params.detection_op
        server_ip = self.params.server_ip
        recipients_contains = self.params.recipients_contains
        recipients_match = self.params.recipients_match
        links = self.params.links
        message_id = self.params.message_id
        cp_quarantined_state = CP_QUARANTINED_VALUES.get(self.params.cp_quarantined_state)
        ms_quarantined_state = MS_QUARANTINED_VALUES.get(self.params.ms_quarantined_state)
        quarantined_state_op = self.params.quarantined_state_op
        name_contains = self.params.name_contains
        name_match = self.params.name_match
        client_ip = self.params.client_ip
        attachment_md5 = self.params.attachment_md5

        self.json_results = self.api_client.search_emails(
            start_date,
            end_date,
            saas,
            direction,
            subject_contains,
            subject_match,
            sender_contains,
            sender_match,
            domain,
            cp_detection,
            ms_detection,
            detection_op,
            server_ip,
            recipients_contains,
            recipients_match,
            links,
            message_id,
            cp_quarantined_state,
            ms_quarantined_state,
            quarantined_state_op,
            name_contains,
            name_match,
            client_ip,
            attachment_md5,
        )


def main() -> None:
    SearchEmails().run()


if __name__ == "__main__":
    main()
