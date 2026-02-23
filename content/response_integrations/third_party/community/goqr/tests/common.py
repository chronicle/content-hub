from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

from integration_testing.common import get_def_file_content

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")
MOCK_DATA_FILE = pathlib.Path.joinpath(MOCKS_PATH, "mock_data.json")


MOCK_DATA: SingleJson = get_def_file_content(MOCK_DATA_FILE)
SCAN_QR_CODE_RESULT: SingleJson = MOCK_DATA["scan_qr_code_result"]
GENERATE_QR_CODE_RESULT: bytes = bytes(MOCK_DATA["generate_qr_code_result"], encoding="utf-8")
