from __future__ import annotations

import pathlib

from integration_testing.common import get_def_file_content
from TIPCommon.types import SingleJson

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")
MOCK_RESPONSES_FILE = pathlib.Path.joinpath(MOCKS_PATH, "mock_responses.json")

MOCK_RESPONSES: SingleJson = get_def_file_content(MOCK_RESPONSES_FILE)
