from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.GoogleDriveManager import GoogleDriveManager

IDENTIFIER = "Google Drive"


@output_handler
def main():
    siemplify = SiemplifyAction()

    credentials_json = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Credentials Json",
    )

    file_id = siemplify.extract_action_param(param_name="File Id", is_mandatory=True)
    role = siemplify.extract_action_param(param_name="Role", is_mandatory=True)
    user_emails_to_add = siemplify.extract_action_param(
        param_name="Emails",
        is_mandatory=True,
    )
    should_send_notification_str = siemplify.extract_action_param(
        param_name="Should send notification",
        is_mandatory=True,
    )
    should_send_notification = bool(should_send_notification_str)

    google_drive_manager = GoogleDriveManager(credentials_json)

    emails = user_emails_to_add.split(";")
    for email in emails:
        google_drive_manager.insert_permission(
            file_id,
            role,
            email,
            should_send_notification,
        )

    output_message = (
        f"Permission {role} for file <{file_id}> was granted to {user_emails_to_add}."
    )
    siemplify.end(output_message, file_id)


if __name__ == "__main__":
    main()
