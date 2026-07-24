# Copyright 2025 Google LLC
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

import re

INTEGRATION_NAME: str = "Tools"
DELAY_PLAYBOOK_SYNCHRONOUS_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Delay Playbook Synchronous"
)

MAX_SYNC_DELAY_TIME_IN_SECONDS: int = 30
MIN_SYNC_DELAY_TIME_IN_SECONDS: int = 0
LABEL_REGEX = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")

CASE_TYPE_MAP: dict[int, str] = {
    1: "EXTERNAL",
    2: "TEST",
    3: "REQUEST",
}

DATA_TYPE_MAP: dict[int, str] = {
    1: "1",
    2: "2",
}

SOURCE_TYPE_MAP: dict[int, str] = {
    1: "CONNECTOR",
    2: "API",
    3: "SIEMPLIFY",
}

RAW_FIELDS_KEY: str = "_fields"
FIELDS_KEY: str = "fields"
RAW_DATA_FIELDS_KEY: str = "_rawDataFields"
DATA_FIELDS_KEY: str = "rawDataFields"
UNDEFINED_VALUE: str = "undefined"

CASE_TYPE_KEYS: list[str] = ["Type", "type"]
DATA_TYPE_KEYS: list[str] = ["DataType", "Datatype", "dataType", "datatype"]
SOURCE_TYPE_KEYS: list[str] = ["SourceType", "sourceType", "sourcetype"]
