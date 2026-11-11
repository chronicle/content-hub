from __future__ import annotations
from integration_testing.common import get_def_file_content

import json
import pathlib

from TIPCommon.types import SingleJson

from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

OAUTH_TOKEN_JSON = MOCK_DATA.get("oauth_token")
INCIDENTS_JSON = MOCK_DATA.get("incidents")
MESSAGES_JSON = MOCK_DATA.get("messages")

DEFAULT_INCIDENT = INCIDENTS_JSON[0]
INTEGRATION_PATH = pathlib.Path(__file__).parent.parent
ALERT_NAME: str = f'{DEFAULT_INCIDENT.get("title")}'
DEFAULT_FILTERS: dict = {}
DEFAULT_QUERY: str = json.dumps(DEFAULT_FILTERS, sort_keys=True)
