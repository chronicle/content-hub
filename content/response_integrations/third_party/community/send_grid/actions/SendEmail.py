from __future__ import annotations

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler, utc_now

from ..core.EmailActions import BaseEmailAction


class SendEmailAction(BaseEmailAction):
    """This class should be used for execution of flow related to SendEmail action.
    SendEmail should simply send an email through selected SendGridAPIClient.
    This action doesn't support any retry logic.
    """

    SCRIPT_NAME = "SendGrid - Send Email"

    def __init__(self):
        """SendEmailAction constructor. Loads integration configuration and initializes EmailManager instance"""
        super(SendEmailAction, self).__init__(SendEmailAction.SCRIPT_NAME)

    def execute_action(self, output_messages, successful_entities, failed_entities):
        """Sends email
        :param output_messages: {list} Mutable list of output messages (str) to form audit trail for this action
        :param successful_entities: {list} N/A in case of SendEmail. List of entity.identifier's, which have been processed successfully
        :param failed_entities: {list} N/A in case of SendEmail. List of entity.identifier's, which have been failed during processing
        :return: {tuple} 1st value - Status of the operation: {int} 0 - success, 1 - failed, 2 - timed out; 2nd value - Success flag: {bool} True - success, False - failure.
        """
        # Create a dict with all required attachments to the email
        # attachments_dict = self.load_attachments_to_dict()
        # siemplifyAction = SiemplifyAction()

        message = Mail(
            from_email=self.email_from,
            to_emails=self.email_to,
            subject=self.subject,
            html_content=self.content,
        )

        try:
            self.logger.info("Sending email")
            sg = SendGridAPIClient(self.api_token)
            response = sg.send(message)
        except Exception as e:
            message = "Failed to send email!"
            self.logger.error(message)
            self.logger.exception(e)
            output_messages.append(message)
            return EXECUTION_STATE_FAILED, False

        message = "Email has been sent successfully"
        # Save result JSON, if required
        if self.return_message_status:
            self.logger.info("Saving result JSON")
            json_result = {
                "response": response.status_code,
                "date": utc_now(),
                "recipients": self.email_to,
            }
            self.siemplify.result.add_result_json(json_result)
            message = f"Mail sent successfully. Mail message status is: {response.status_code}"

        output_messages.append(message)
        self.logger.info(message)
        return EXECUTION_STATE_COMPLETED, True


@output_handler
def main():
    action = SendEmailAction()
    action.run()


if __name__ == "__main__":
    main()
