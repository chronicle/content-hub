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
    google_drive_manager.delete_file(file_id)

    output_message = f"File <{file_id}> was successfully deleted."
    siemplify.end(output_message, file_id)


if __name__ == "__main__":
    main()
