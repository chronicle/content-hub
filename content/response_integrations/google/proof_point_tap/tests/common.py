# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import json
import pathlib

from TIPCommon.types import SingleJson
from integration_testing.common import get_def_file_content

from ..core.datamodels import (
    Campaign,
    Event,
    ThreatForensic,
)


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
TEST_PING_DATA: SingleJson = MOCK_DATA["test_ping"]
SEARCH_EVENTS_NO_DATA: SingleJson = MOCK_DATA["search_events_no_data"]
SEARCH_EVENTS_WITH_DATA: SingleJson = MOCK_DATA["search_events_with_data"]
LIST_CAMPAIGNS_WITH_DATA: SingleJson = MOCK_DATA["list_campaigns"]
THREAT_FORENSICS: SingleJson = MOCK_DATA["threat_forensics"]

INVALID_ID: int = 99999999
THREAT_ID: str = "353f345g"

THREAT_FORENSICS: ThreatForensic = ThreatForensic.from_json(THREAT_FORENSICS)
SEARCH_EVENTS: Event = Event.from_json(SEARCH_EVENTS_WITH_DATA, "Issues")
SEARCH_EVENTS_NO_DATA: Event = Event.from_json(SEARCH_EVENTS_NO_DATA, "Issues")
PING_DATA: Campaign = Campaign.from_json(TEST_PING_DATA)
LIST_CAMPAIGN: Campaign = Campaign.from_json(LIST_CAMPAIGNS_WITH_DATA)

LIST_ALERTS_URL: str = "/1.0/alerts/"

class AlertIdNotFoundError(Exception):
    """Accessed Alert ID cannot be found"""
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
