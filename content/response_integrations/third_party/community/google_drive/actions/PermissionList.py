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

    google_drive_manager = GoogleDriveManager(credentials_json)
    res = google_drive_manager.list_permissions(file_id)

    perms_count = len(res)
    siemplify.result.add_result_json(res)

    output_message = f"{perms_count} permissions were found for file <{file_id}>."
    siemplify.end(output_message, perms_count)


if __name__ == "__main__":
    main()
