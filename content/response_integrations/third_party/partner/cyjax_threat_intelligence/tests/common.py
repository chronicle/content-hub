from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from integration_testing.common import get_def_file_content

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


INTEGRATION_PATH: Path = Path(__file__).parent.parent
CONFIG_PATH = INTEGRATION_PATH / "tests" / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCKS_PATH = INTEGRATION_PATH / "tests" / "mocks"
MOCK_RESPONSES_FILE = MOCKS_PATH / "mock_responses.json"

MOCK_DATA: SingleJson = json.loads(MOCK_RESPONSES_FILE.read_text(encoding="utf-8"))
MOCK_PING_RESPONSE: SingleJson = MOCK_DATA.get("ping")
MOCK_DOMAIN_MONITOR_RESPONSE: SingleJson = MOCK_DATA.get("domain_monitor")
MOCK_ENRICH_IOCS_RESPONSE: SingleJson = MOCK_DATA.get("enrich_iocs")
MOCK_LIST_DATA_BREACHES_RESPONSE: SingleJson = MOCK_DATA.get("list_data_breaches")
