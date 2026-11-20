from __future__ import annotations

import unittest.mock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from google_sheets.actions import GetAll
from google_sheets.tests.common import CONFIG_PATH

CREATE_SPREADSHEET_PATH = "google_sheets.core.google_sheets.GoogleSheetFactory.create_spreadsheet"

DEFAULT_PARAMETERS: dict[str, str] = {
    "Sheet Id": "test-sheet-id",
    "Worksheet Name": "myworksheet",
    "Return Raw Values": "false",
}


class FakeWorksheet:
    def __init__(self) -> None:
        self.records = [{"Name": "Alice", "Status": "Active"}]
        self.raw_values = [
            ["Name", "Name", ""],
            ["Alice", "A.", "Active"],
        ]
        self.get_all_records_calls = 0
        self.get_all_values_calls = 0

    def get_all_records(self) -> list[dict[str, str]]:
        self.get_all_records_calls += 1
        return self.records

    def get_all_values(self) -> list[list[str]]:
        self.get_all_values_calls += 1
        return self.raw_values


class FakeSpreadsheet:
    def __init__(self, worksheet: FakeWorksheet) -> None:
        self.sheet1 = worksheet
        self._worksheets = {"myworksheet": worksheet}

    def worksheet(self, name: str) -> FakeWorksheet:
        return self._worksheets[name]


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_get_all_returns_header_keyed_records_by_default(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet()
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        GetAll.main()

    assert worksheet.get_all_records_calls == 1
    assert worksheet.get_all_values_calls == 0
    assert action_output.results.json_output.json_result == worksheet.records
    assert action_output.results.output_message == "All rows were fetched successfully"
    assert action_output.results.result_value is True
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={**DEFAULT_PARAMETERS, "Return Raw Values": "true"},
)
def test_get_all_returns_raw_rows_without_requiring_unique_headers(
    action_output: MockActionOutput,
) -> None:
    worksheet = FakeWorksheet()
    fake_sheet = FakeSpreadsheet(worksheet)

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        GetAll.main()

    assert worksheet.get_all_values_calls == 1
    assert worksheet.get_all_records_calls == 0
    assert action_output.results.json_output.json_result == worksheet.raw_values
    assert action_output.results.output_message == "All rows were fetched successfully"
    assert action_output.results.result_value is True
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
