from __future__ import annotations

import json

import gspread
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.google_sheets import GoogleSheetFactory

IDENTIFIER = "Google Sheet"


def add_or_update_row(
    siemplify,
    worksheet,
    field_name,
    column_number_int,
    values_dict,
    start_column,
    end_column,
    count,
):
    ret_val = {"row_number": -1, "output_message": ""}
    row_index = -1
    value_to_search = values_dict
    row_values_list = list(values_dict.values())

    try:
        cell = worksheet.find(str(value_to_search))
        if cell.col == column_number_int:
            siemplify.result.add_result_json(values_dict)
            row_index = cell.row
            output_msg = f"Found row: {row_index}, with value {field_name} in column {column_number_int}."
    except gspread.exceptions.CellNotFound:
        output_msg = "The cell was not found"
    except Exception as err:
        output_msg = f"Unexpected error: {err}"
    finally:
        print(output_msg)

    updated_range = ""
    if row_index != -1:
        updated_range = (
            f"{start_column}{row_index + count}:{end_column}{row_index + count}"
        )
        worksheet.update(updated_range, [row_values_list])
        output_msg = f"Updated range {updated_range} with values {row_values_list}."

    else:
        res = worksheet.append_row(row_values_list)
        updated_range = res["updates"]["updatedRange"]

        output_msg = f"Added new row in {updated_range} with values {row_values_list}."

    print(updated_range)
    ret_val["updated_range"] = updated_range
    ret_val["output_message"] = output_msg
    return ret_val


@output_handler
def main():
    siemplify = SiemplifyAction()

    credentials_json = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Credentials Json",
    )
    column_number_str = siemplify.extract_action_param(
        param_name="Column Number",
        is_mandatory=True,
    )
    column_header = siemplify.extract_action_param(
        param_name="Field Name",
        is_mandatory=True,
    )
    sheet_id = siemplify.extract_action_param(param_name="Sheet Id", is_mandatory=True)
    worksheet_name = siemplify.extract_action_param(param_name="Worksheet Name")
    start_column = siemplify.extract_action_param(param_name="Start Column")
    end_column = siemplify.extract_action_param(param_name="End Column")

    column_number_int = int(column_number_str)
    json_fields_str = siemplify.extract_action_param(param_name="Json")
    rows = json.loads(json_fields_str)

    updated_rows = []
    try:
        sheet = GoogleSheetFactory(credentials_json).create_spreadsheet(sheet_id)

        if worksheet_name:
            worksheet = sheet.worksheet(worksheet_name)
        else:
            worksheet = sheet.sheet1

        count = 0
        for row in rows:
            ret_val = add_or_update_row(
                siemplify,
                worksheet,
                column_header,
                column_number_int,
                row,
                start_column,
                end_column,
                count,
            )
            count = count + 1
            updated_rows.append(ret_val["updated_range"])
    except Exception as err:
        message = str(err)
        status = EXECUTION_STATE_FAILED
    else:
        message = f"{len(updated_rows)} rows were updated or added."
        status = EXECUTION_STATE_COMPLETED

    siemplify.end(message, len(updated_rows), status)


if __name__ == "__main__":
    main()
