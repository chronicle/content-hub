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
    folder_to_save = siemplify.extract_action_param(
        param_name="Folder Path",
        is_mandatory=True,
    )

    google_drive_manager = GoogleDriveManager(credentials_json)
    res = google_drive_manager.download_file_to_path(file_id, folder_to_save)

    siemplify.result.add_result_json(res)

    output_message = f"File <{res['name']}:{file_id}> was successfully downloaded to path {res['saved_to']}."
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
