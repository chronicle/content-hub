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
MOCK_CONNECTIVITY_RESPONSE: SingleJson = MOCK_DATA.get("test_connectivity")
MOCK_TOKEN_RESPONSE: SingleJson = MOCK_DATA.get("token_response")
MOCK_CDM_CLUSTER_LOCATION: SingleJson = MOCK_DATA.get("cdm_cluster_location")
MOCK_CDM_CLUSTER_CONNECTION_STATE: SingleJson = MOCK_DATA.get("cdm_cluster_connection_state")
MOCK_SONAR_POLICY_OBJECTS_LIST: SingleJson = MOCK_DATA.get("sonar_policy_objects_list")
MOCK_SONAR_OBJECT_DETAIL: SingleJson = MOCK_DATA.get("sonar_object_detail")
MOCK_IOC_SCAN_RESULTS: SingleJson = MOCK_DATA.get("ioc_scan_results")
MOCK_TURBO_IOC_SCAN: SingleJson = MOCK_DATA.get("turbo_ioc_scan")
MOCK_LIST_EVENTS: SingleJson = MOCK_DATA.get("list_events")
MOCK_LIST_OBJECT_SNAPSHOTS: SingleJson = MOCK_DATA.get("list_object_snapshots")
MOCK_LIST_SONAR_FILE_CONTEXTS: SingleJson = MOCK_DATA.get("list_sonar_file_contexts")
MOCK_ADVANCED_IOC_SCAN: SingleJson = MOCK_DATA.get("advanced_ioc_scan")
