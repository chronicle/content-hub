from __future__ import annotations

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

    sheet_id = siemplify.extract_action_param(param_name="Sheet Id", is_mandatory=True)
    worksheet_name = siemplify.extract_action_param(param_name="Worksheet Name")

    try:
        sheet = GoogleSheetFactory(credentials_json).create_spreadsheet(sheet_id)
        if worksheet_name:
            worksheet = sheet.worksheet(worksheet_name)
        else:
            worksheet = sheet.sheet1
        list_of_dicts = worksheet.get_all_records()
        siemplify.result.add_result_json(list_of_dicts)
    except Exception as err:
        status = EXECUTION_STATE_FAILED
        message = str(err)
    else:
        status = EXECUTION_STATE_COMPLETED
        message = "All rows were fetched successfully"
    siemplify.end(message, status is EXECUTION_STATE_COMPLETED, status)


if __name__ == "__main__":
    main()
