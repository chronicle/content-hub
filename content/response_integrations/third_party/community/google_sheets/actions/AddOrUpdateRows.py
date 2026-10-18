from __future__ import annotations

import json

from gspread.utils import rowcol_to_a1
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.google_sheets import GoogleSheetFactory

IDENTIFIER = "Google Sheet"


def parse_column_number(value, parameter_name):
    try:
        column_number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{parameter_name} must be a positive integer.") from None

    if column_number < 1:
        raise ValueError(f"{parameter_name} must be a positive integer.")

    return column_number


def add_or_update_row(
    siemplify,
    worksheet,
    field_name,
    column_number_int,
    values_dict,
    start_column_int,
    end_column_int,
):
    ret_val = {"row_number": -1, "output_message": ""}
    if field_name not in values_dict:
        raise ValueError(f"Field Name '{field_name}' was not found in the row JSON.")

    value_to_search = values_dict[field_name]
    row_values_list = list(values_dict.values())

    cell = worksheet.find(
        str(value_to_search),
        in_column=column_number_int,
    )

    if cell is not None:
        siemplify.result.add_result_json(values_dict)
        row_index = cell.row
        updated_range = (
            f"{rowcol_to_a1(row_index, start_column_int)}:"
            f"{rowcol_to_a1(row_index, end_column_int)}"
        )
        worksheet.update([row_values_list], updated_range)
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
    start_column_str = siemplify.extract_action_param(param_name="Start Column")
    end_column_str = siemplify.extract_action_param(param_name="End Column")

    json_fields_str = siemplify.extract_action_param(param_name="Json")

    updated_rows = []
    try:
        column_number_int = parse_column_number(column_number_str, "Column Number")
        start_column_int = parse_column_number(start_column_str, "Start Column")
        end_column_int = parse_column_number(end_column_str, "End Column")
        if start_column_int > end_column_int:
            raise ValueError("Start Column must not be greater than End Column.")

        rows = json.loads(json_fields_str)
        sheet = GoogleSheetFactory(credentials_json).create_spreadsheet(sheet_id)

        if worksheet_name:
            worksheet = sheet.worksheet(worksheet_name)
        else:
            worksheet = sheet.sheet1

        for row in rows:
            ret_val = add_or_update_row(
                siemplify,
                worksheet,
                column_header,
                column_number_int,
                row,
                start_column_int,
                end_column_int,
            )
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
