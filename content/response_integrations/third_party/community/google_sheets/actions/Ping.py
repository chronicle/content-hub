from __future__ import annotations

import uuid

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.google_sheets import GoogleSheetFactory

IDENTIFIER = "Google Sheet"


@output_handler
def main():
    siemplify = SiemplifyAction()

    credentials_json = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Credentials Json",
    )

    try:
        client = GoogleSheetFactory(credentials_json).create_client()
        sheet = client.create("Test-" + str(uuid.uuid4()))
        client.del_spreadsheet(sheet.id)

    except Exception as err:
        status = EXECUTION_STATE_FAILED
        message = str(err)
    else:
        status = EXECUTION_STATE_COMPLETED
        message = "Connected successfully"
    siemplify.end(message, status is EXECUTION_STATE_COMPLETED, status)


if __name__ == "__main__":
    main()
