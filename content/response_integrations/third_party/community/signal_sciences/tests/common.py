from __future__ import annotations

import pathlib

from integration_testing.common import get_def_file_content

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
CONFIG = get_def_file_content(CONFIG_PATH)
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")
SITES_MOCK_PATH = pathlib.Path.joinpath(MOCKS_PATH, "sites.json")
SITES_DATA = get_def_file_content(SITES_MOCK_PATH)
IP_RESPONSES_MOCK_PATH = pathlib.Path.joinpath(MOCKS_PATH, "ip_responses.json")
IP_RESPONSES_DATA = get_def_file_content(IP_RESPONSES_MOCK_PATH)
