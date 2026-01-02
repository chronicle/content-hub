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
    row_index_str = siemplify.extract_action_param(param_name="Row Index")
    values_str = siemplify.extract_action_param(param_name="Values")

    values = []
    elements = values_str.split(",")
    for elem in elements:
        values.append(elem)
    try:
        sheet = GoogleSheetFactory(credentials_json).create_spreadsheet(sheet_id)

        if worksheet_name:
            worksheet = sheet.worksheet(worksheet_name)
        else:
            worksheet = sheet.sheet1

        if row_index_str:
            row_index = int(row_index_str)
            worksheet.insert_row(values, row_index)
        else:
            worksheet.insert_row(values)

        print(worksheet.row_count)
    except Exception as err:
        siemplify.LOGGER.error(err)
        status = EXECUTION_STATE_FAILED
    else:
        status = EXECUTION_STATE_COMPLETED

    siemplify.end("Row added to the sheet successfully", True, status)


if __name__ == "__main__":
    main()
