from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

from integration_testing.common import get_def_file_content

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")
MOCK_RATES_FILE = pathlib.Path.joinpath(MOCKS_PATH, "mock_rates.json")

MOCK_RATES_DEFAULT: SingleJson = json.loads(MOCK_RATES_FILE.read_text(encoding="utf-8"))[
    "default_response"
]
MOCK_DATA: SingleJson = get_def_file_content(MOCK_RATES_FILE)
GET_CASE_DETAILS: SingleJson = MOCK_DATA.get("get_case_details")
