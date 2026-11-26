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
from integration_testing.common import get_def_file_content

import pathlib
from unittest.mock import MagicMock

from integration_testing.common import get_def_file_content
from TIPCommon.types import SingleJson


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)

MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

TOKEN_RESPONSE: SingleJson = MOCK_DATA["token_response"]
EVENTS_RESPONSE: SingleJson = MOCK_DATA["events_response"]
EMPTY_EVENTS_RESPONSE: SingleJson = MOCK_DATA["empty_events_response"]

EVENT_ID: str = "pcap_evt_999"
EVENT_NAME: str = "Suspicious Protocol Activity"
PCAP_BYTES: bytes = b"mock_pcap_binary_content"

SUCCESS_RESULT_VALUE: str = "true"
SUCCESS_MESSAGE_PREFIX: str = "Successfully downloaded pcap for events"
EMPTY_MESSAGE: str = "No pcaps were downloaded."


def create_mock_event(id_: str, name: str) -> MagicMock:
    """Create a mock double representing a Protectwise security event."""
    event = MagicMock()
    event.start_time = "1000000000"
    event.end_time = "1000000100"
    event.name = name
    return event


class EventIdNotFoundError(Exception):
    """Accessed Event ID cannot be found."""
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
