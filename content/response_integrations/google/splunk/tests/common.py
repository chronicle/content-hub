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
from collections.abc import MutableMapping
import pathlib
import time

from TIPCommon.types import SingleJson
from ..actions.UpdateNotableEvents import EMPTY_DROPDOWN_VALUE
from ..core.SplunkParser import SplunkParser
from ..core.constants import MAX_EVENTS_COUNT
from ..core.datamodels import NotableEvent
from integration_testing.common import get_def_file_content


MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
class EventIdNotFoundError(Exception):
    """Accessed Event ID cannot be found"""


def create_error_content(
    message: str,
) -> dict[str, list[MutableMapping[str, str]]]:
    return {"message": [{"text": f"Mock Message: {message}"}]}


def create_notable_event(  # pylint: disable=too-many-arguments
    event_id: str,
    disposition: str | None = None,
    owner: str | None = None,
    count: int = MAX_EVENTS_COUNT,
    search_name: str | None = None,
    rule_description: str | None = None,
    saved_search_description: str | None = None,
    urgency: str = EMPTY_DROPDOWN_VALUE,
    rule_name: str | None = None,
    epoch: str | None = None,
    timestamp: str | None = None,
    orig_sid: str | None = None,
    info_max_time: str | None = None,
    info_min_time: str | None = None,
    info_search_time: str | None = None,
    comments: str | list[str] | None = None,
    status: str | None = None,
    drilldown_search: str | None = None,
    drilldown_earliest: str | None = None,
    drilldown_latest: str | None = None,
    drilldown_latest_offset: str | None = None,
    drilldown_earliest_offset: str | None = None,
    rule_title: str | None = None,
) -> NotableEvent:
    """Create a notable event object"""
    return SplunkParser().build_notable_event_object(
        {
            "event_id": event_id,
            "disposition": disposition,
            "owner": owner,
            "count": count,
            "search_name": search_name,
            "rule_description": rule_description,
            "savedsearch_description": saved_search_description,
            "urgency": urgency,
            "rule_name": rule_name,
            "_time": timestamp or time.time(),
            "epoch": epoch or time.time(),
            "orig_sid": orig_sid,
            "info_max_time": info_max_time,
            "info_min_time": info_min_time,
            "info_search_time": info_search_time,
            "comment": comments,
            "status": status,
            "drilldown_search": drilldown_search,
            "drilldown_earliest": drilldown_earliest,
            "drilldown_latest": drilldown_latest,
            "drilldown_latest_offset": drilldown_latest_offset,
            "drilldown_earliest_offset": drilldown_earliest_offset,
            "rule_title": rule_title,
        }
    )
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / 'config.json'
CONFIG: dict = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
