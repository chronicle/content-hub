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
    row_number_str = siemplify.extract_action_param(
        param_name="Row Number",
        is_mandatory=True,
    )
    values_str = siemplify.extract_action_param(param_name="Values", is_mandatory=True)
    sheet_id = siemplify.extract_action_param(param_name="Sheet Id", is_mandatory=True)
    worksheet_name = siemplify.extract_action_param(param_name="Worksheet Name")
    rows = row_number_str.split(",")

    try:
        sheet = GoogleSheetFactory(credentials_json).create_spreadsheet(sheet_id)

        if worksheet_name:
            worksheet = sheet.worksheet(worksheet_name)
        else:
            worksheet = sheet.sheet1

        values = values_str.split(",")
        for row_str in rows:
            row = int(row_str)
            column_num = 1
            for val in values:
                worksheet.update_cell(row, column_num, val)
                column_num = column_num + 1
    except Exception as err:
        status = EXECUTION_STATE_FAILED
        message = str(err)
    else:
        status = EXECUTION_STATE_COMPLETED
        message = "The row has been updated successfully"

    siemplify.end(message, status is EXECUTION_STATE_COMPLETED, status)


if __name__ == "__main__":
    main()
