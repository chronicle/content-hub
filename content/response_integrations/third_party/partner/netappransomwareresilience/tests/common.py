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
MOCK_RESPONSES_FILE = pathlib.Path.joinpath(MOCKS_PATH, "mock_responses.json")

MOCK_DATA: SingleJson = json.loads(MOCK_RESPONSES_FILE.read_text(encoding="utf-8"))
MOCK_TOKEN_RESPONSE: SingleJson = MOCK_DATA.get("token_response")
MOCK_ENRICH_IP_RESPONSE: SingleJson = MOCK_DATA.get("enrich_ip")
MOCK_ENRICH_STORAGE_RESPONSE: SingleJson = MOCK_DATA.get("enrich_storage")
MOCK_CHECK_JOB_STATUS_RESPONSE: SingleJson = MOCK_DATA.get("check_job_status")
MOCK_TAKE_SNAPSHOT_RESPONSE: SingleJson = MOCK_DATA.get("take_snapshot")
MOCK_VOLUME_OFFLINE_RESPONSE: SingleJson = MOCK_DATA.get("volume_offline")
