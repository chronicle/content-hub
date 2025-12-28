from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
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

    base64_string = siemplify.extract_action_param(
        param_name="Base64 String",
        is_mandatory=True,
    )
    file_name = siemplify.extract_action_param(
        param_name="File Name",
        is_mandatory=True,
    )
    share_to_emails = siemplify.extract_action_param(param_name="Share with emails")

    google_drive_manager = GoogleDriveManager(credentials_json)
    res = google_drive_manager.upload_file_from_base64(file_name, base64_string)
    file_id = res["id"]
    if share_to_emails:
        emails = share_to_emails.split(";")
        for email in emails:
            google_drive_manager.insert_permission(file_id, "writer", email)

    siemplify.result.add_result_json(res)

    siemplify.end(
        "File was uploaded to Google Drive successfully",
        res["id"],
        EXECUTION_STATE_COMPLETED,
    )


if __name__ == "__main__":
    main()
