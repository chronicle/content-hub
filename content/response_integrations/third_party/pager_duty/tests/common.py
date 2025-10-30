from __future__ import annotations

import pathlib

from integration_testing.common import get_def_file_content
from TIPCommon.types import SingleJson

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")

MOCK_INCIDENTS_FILE = pathlib.Path.joinpath(MOCKS_PATH, "incidents.json")
