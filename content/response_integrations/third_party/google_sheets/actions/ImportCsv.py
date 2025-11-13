from __future__ import annotations

import gspread
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
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
    sheet_id = siemplify.extract_action_param(param_name="Sheet Id", is_mandatory=True)
    csv_path = siemplify.extract_action_param(param_name="CSV Path")
    try:
        sheet = GoogleSheetFactory(credentials_json).create_spreadsheet(sheet_id)

        content = open(csv_path).read()

        client = gspread.service_account(filename="./credentials.json")
        client.import_csv(sheet_id, content)

    except Exception as err:
        message = str(err)
        sheet_id = -1
    else:
        message = "CSV imported successfully"
        sheet_id = sheet.id

    siemplify.end(message, sheet_id, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
