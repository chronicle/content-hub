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
    res = google_drive_manager.get_file_metadata(file_id)

    siemplify.result.add_result_json(res)

    siemplify.end("The file metadata was retrieved successfully", res["id"])


if __name__ == "__main__":
    main()
