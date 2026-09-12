from __future__ import annotations

import json
import types
import unittest.mock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from google_sheets.actions import AddOrUpdateRows
from google_sheets.tests.common import CONFIG_PATH

CREATE_SPREADSHEET_PATH = "google_sheets.core.google_sheets.GoogleSheetFactory.create_spreadsheet"

DEFAULT_ROWS = [
    {"Team": "Security", "Dominio": "one.test", "Status": "Active"},
    {"Team": "Operations", "Dominio": "two.test", "Status": "Pending"},
]
DEFAULT_PARAMETERS: dict[str, str] = {
    "Sheet Id": "test-sheet-id",
    "Worksheet Name": "myworksheet",
    "Column Number": "2",
    "Start Column": "1",
    "End Column": "3",
    "Field Name": "Dominio",
    "Json": json.dumps(DEFAULT_ROWS),
}


class FakeWorksheet:
    def __init__(
        self,
        *,
        cells: dict[str, types.SimpleNamespace] | None = None,
        find_error: Exception | None = None,
    ) -> None:
        self.cells = cells or {}
        self.find_error = find_error
        self.find_calls: list[tuple[str, int | None]] = []
        self.updated_rows: list[tuple[list[list[str]], str]] = []
        self.appended_rows: list[list[str]] = []

    def find(
        self,
        query: str,
        in_column: int | None = None,
    ) -> types.SimpleNamespace | None:
        self.find_calls.append((query, in_column))
        if self.find_error:
            raise self.find_error
        return self.cells.get(query)

    def update(self, values: list[list[str]], range_name: str) -> None:
        self.updated_rows.append((values, range_name))

    def append_row(self, values: list[str]) -> dict:
        self.appended_rows.append(values)
        return {"updates": {"updatedRange": "Sheet1!A8:C8"}}


class FakeSpreadsheet:
    def __init__(self, worksheet: FakeWorksheet) -> None:
        self.sheet1 = worksheet
        self._worksheets = {"myworksheet": worksheet}

    def worksheet(self, name: str) -> FakeWorksheet:
        return self._worksheets[name]


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_add_or_update_rows_searches_field_values_in_configured_column(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet(
        cells={
            "one.test": types.SimpleNamespace(row=7, col=2),
            "two.test": types.SimpleNamespace(row=4, col=2),
        },
    )
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        AddOrUpdateRows.main()

    assert worksheet.find_calls == [("one.test", 2), ("two.test", 2)]
    assert worksheet.updated_rows == [
        ([["Security", "one.test", "Active"]], "A7:C7"),
        ([["Operations", "two.test", "Pending"]], "A4:C4"),
    ]
    assert worksheet.appended_rows == []
    assert action_output.results.output_message == "2 rows were updated or added."
    assert action_output.results.result_value == 2
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={**DEFAULT_PARAMETERS, "Json": json.dumps([DEFAULT_ROWS[0]])},
)
def test_add_or_update_rows_appends_when_field_value_is_not_found(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet()
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        AddOrUpdateRows.main()

    assert worksheet.find_calls == [("one.test", 2)]
    assert worksheet.appended_rows == [["Security", "one.test", "Active"]]
    assert worksheet.updated_rows == []
    assert action_output.results.output_message == "1 rows were updated or added."
    assert action_output.results.result_value == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={**DEFAULT_PARAMETERS, "Json": json.dumps([DEFAULT_ROWS[0]])},
)
def test_add_or_update_rows_returns_real_lookup_errors(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet(find_error=RuntimeError("worksheet unavailable"))
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        AddOrUpdateRows.main()

    assert worksheet.appended_rows == []
    assert action_output.results.output_message == "worksheet unavailable"
    assert action_output.results.result_value == 0
    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        **DEFAULT_PARAMETERS,
        "Json": json.dumps([{"Team": "Security", "Status": "Active"}]),
    },
)
def test_add_or_update_rows_returns_clear_error_when_field_is_missing(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet()
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        AddOrUpdateRows.main()

    assert worksheet.find_calls == []
    assert action_output.results.output_message == (
        "Field Name 'Dominio' was not found in the row JSON."
    )
    assert action_output.results.result_value == 0
    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={**DEFAULT_PARAMETERS, "Start Column": "0"},
)
def test_add_or_update_rows_rejects_invalid_column_numbers_before_api_call(
    action_output: MockActionOutput,
) -> None:
    with unittest.mock.patch(CREATE_SPREADSHEET_PATH) as create_spreadsheet:
        AddOrUpdateRows.main()

    create_spreadsheet.assert_not_called()
    assert action_output.results.output_message == (
        "Start Column must be a positive integer."
    )
    assert action_output.results.result_value == 0
    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED
