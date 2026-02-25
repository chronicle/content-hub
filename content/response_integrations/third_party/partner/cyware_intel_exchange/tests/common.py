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
MOCK_BULK_LOOKUP: SingleJson = MOCK_DATA.get("bulk_lookup")
MOCK_ADD_ALLOWED_IOCS: SingleJson = MOCK_DATA.get("add_allowed_iocs")
MOCK_REMOVE_ALLOWED_IOCS: SingleJson = MOCK_DATA.get("remove_allowed_iocs")
MOCK_GET_ALLOWED_IOCS: SingleJson = MOCK_DATA.get("get_allowed_iocs")
MOCK_ADD_NOTE: SingleJson = MOCK_DATA.get("add_note")
MOCK_CREATE_INTEL: SingleJson = MOCK_DATA.get("create_intel")
MOCK_QUICK_INTEL_STATUS: SingleJson = MOCK_DATA.get("quick_intel_status")
MOCK_GET_IOC_DETAILS: SingleJson = MOCK_DATA.get("get_ioc_details")
MOCK_ADD_TAGS: SingleJson = MOCK_DATA.get("add_tags")
MOCK_REMOVE_TAGS: SingleJson = MOCK_DATA.get("remove_tags")
MOCK_MARK_FALSE_POSITIVE: SingleJson = MOCK_DATA.get("mark_false_positive")
MOCK_CREATE_TASK: SingleJson = MOCK_DATA.get("create_task")
MOCK_GET_USER_BY_EMAIL: SingleJson = MOCK_DATA.get("get_user_by_email")
