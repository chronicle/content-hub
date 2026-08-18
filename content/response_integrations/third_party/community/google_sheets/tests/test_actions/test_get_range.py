from __future__ import annotations

import unittest.mock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from google_sheets.actions import GetRange
from google_sheets.tests.common import CONFIG_PATH

CREATE_SPREADSHEET_PATH = "google_sheets.core.google_sheets.GoogleSheetFactory.create_spreadsheet"

DEFAULT_PARAMETERS: dict[str, str] = {
    "Sheet Id": "test-sheet-id",
    "Worksheet Name": "myworksheet",
    "Range": "A:A",
}


class FakeWorksheet:
    def __init__(self, title: str) -> None:
        self.title = title


class FakeSpreadsheet:
    def __init__(self) -> None:
        self.requested_ranges: list[str] = []
        self.sheet1 = FakeWorksheet("Sheet1")
        self._worksheets = {"myworksheet": FakeWorksheet("myworksheet")}

    def worksheet(self, name: str) -> FakeWorksheet:
        return self._worksheets[name]

    def values_batch_get(self, ranges: str) -> dict:
        self.requested_ranges.append(ranges)
        return {"spreadsheetId": "test-sheet-id", "valueRanges": [{"range": ranges}]}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_get_range_scopes_unqualified_range_to_selected_worksheet(
    action_output: MockActionOutput,
) -> None:
    fake_sheet = FakeSpreadsheet()

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        GetRange.main()

    assert fake_sheet.requested_ranges == ["'myworksheet'!A:A"]
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={**DEFAULT_PARAMETERS, "Range": "'myothersheet'!A:A"},
)
def test_get_range_leaves_already_qualified_range_untouched(
    action_output: MockActionOutput,
) -> None:
    fake_sheet = FakeSpreadsheet()

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        GetRange.main()

    assert fake_sheet.requested_ranges == ["'myothersheet'!A:A"]
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={**DEFAULT_PARAMETERS, "Worksheet Name": "O'Brien's Sheet"},
)
def test_get_range_escapes_single_quotes_in_worksheet_title(
    action_output: MockActionOutput,
) -> None:
    fake_sheet = FakeSpreadsheet()
    fake_sheet._worksheets["O'Brien's Sheet"] = FakeWorksheet("O'Brien's Sheet")

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        GetRange.main()

    assert fake_sheet.requested_ranges == ["'O''Brien''s Sheet'!A:A"]
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={**DEFAULT_PARAMETERS, "Worksheet Name": ""},
)
def test_get_range_scopes_to_first_sheet_when_worksheet_name_is_empty(
    action_output: MockActionOutput,
) -> None:
    fake_sheet = FakeSpreadsheet()

    with unittest.mock.patch(CREATE_SPREADSHEET_PATH, return_value=fake_sheet):
        GetRange.main()

    assert fake_sheet.requested_ranges == ["'Sheet1'!A:A"]
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
