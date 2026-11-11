from __future__ import annotations
import json
from integration_testing.common import get_def_file_content

import pathlib

from TIPCommon.types import SingleJson

from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

OAUTH_TOKEN_JSON = MOCK_DATA.get("oauth_token")
ALLOW_LIST_ENTRIES_JSON = MOCK_DATA.get("allow_list_entries")
BLOCK_LIST_ENTRIES_JSON = MOCK_DATA.get("block_list_entries")

INTEGRATION_PATH = pathlib.Path(__file__).parent.parent
