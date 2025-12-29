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
    permission_id = siemplify.extract_action_param(
        param_name="Permission Id",
        is_mandatory=True,
    )

    google_drive_manager = GoogleDriveManager(credentials_json)
    google_drive_manager.remove_permission(file_id, permission_id)

    output_message = (
        f"Permission <{permission_id}> for file <{file_id}> was successfully removed."
    )
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
