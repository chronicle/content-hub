from __future__ import annotations

import unittest.mock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from google_sheets.actions import AddRow
from google_sheets.tests.common import CONFIG_PATH

CREATE_SPREADSHEET_PATH = "google_sheets.core.google_sheets.GoogleSheetFactory.create_spreadsheet"

DEFAULT_PARAMETERS: dict[str, str] = {
    "Sheet Id": "test-sheet-id",
    "Worksheet Name": "myworksheet",
    "Row Index": "2",
    "Values": "val1,val2",
}


class FakeWorksheet:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.inserted_rows: list[tuple[list[str], int | None]] = []
        self.row_count = 1

    def insert_row(self, values: list[str], index: int | None = None) -> None:
        if self.error:
            raise self.error
        self.inserted_rows.append((values, index))


class FakeSpreadsheet:
    def __init__(self, worksheet: FakeWorksheet) -> None:
        self.sheet1 = worksheet
        self._worksheets = {"myworksheet": worksheet}

    def worksheet(self, name: str) -> FakeWorksheet:
        return self._worksheets[name]


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_add_row_returns_success_result_when_row_is_added(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet()
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        AddRow.main()

    assert worksheet.inserted_rows == [(["val1", "val2"], 2)]
    assert action_output.results.output_message == "Row added to the sheet successfully"
    assert action_output.results.result_value is True
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_add_row_returns_failure_details_when_insert_fails(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet(error=RuntimeError("worksheet unavailable"))
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        AddRow.main()

    assert action_output.results.output_message == (
        "Failed to add row to the sheet. Error: worksheet unavailable"
    )
    assert action_output.results.result_value is False
    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        **DEFAULT_PARAMETERS,
        "Row Index": '[Get Tracking Column.JsonResult| "values" | count()]',
    },
)
def test_add_row_returns_clear_failure_for_invalid_row_index(
    action_output: MockActionOutput,
) -> None:
    fake_sheet = FakeSpreadsheet(FakeWorksheet())

    with unittest.mock.patch(
        CREATE_SPREADSHEET_PATH,
        return_value=fake_sheet,
    ) as create_spreadsheet:
        AddRow.main()

    create_spreadsheet.assert_not_called()
    assert action_output.results.output_message == (
        "Failed to add row to the sheet. Error: Row Index must be a positive integer."
    )
    assert action_output.results.result_value is False
    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED
