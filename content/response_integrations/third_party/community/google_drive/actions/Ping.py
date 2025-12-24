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

    google_drive_manager = GoogleDriveManager(credentials_json)
    google_drive_manager.test_connectivity()

    siemplify.end("Connected successfully", True, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
