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

from typing import Any
from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict[str, Any] = get_def_file_content(CONFIG_PATH)

MOCK_DATA_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: dict[str, Any] = get_def_file_content(MOCK_DATA_PATH)

# Convenience aliases into the mock STIX bundle
ENTERPRISE_ATTACK: dict[str, Any] = MOCK_DATA["enterprise_attack"]

# Known IDs / names used across tests
ATTACK_PATTERN_ID: str = "attack-pattern--001"
ATTACK_PATTERN_ID_2: str = "attack-pattern--002"
ATTACK_PATTERN_EXTERNAL_ID: str = "T1566.001"
ATTACK_PATTERN_EXTERNAL_ID_2: str = "T1059"
ATTACK_PATTERN_NAME: str = "Spearphishing Attachment"
ATTACK_PATTERN_NAME_2: str = "Command and Scripting Interpreter"

INTRUSION_SET_ID: str = "intrusion-set--001"
INTRUSION_SET_NAME: str = "APT28"

COURSE_OF_ACTION_ID: str = "course-of-action--001"
COURSE_OF_ACTION_NAME: str = "Restrict File and Directory Permissions"

# The real GitHub URL used in config.json but for mocking we intercept on the path
MITRE_DATA_PATH: str = "/mitre/cti/master/enterprise-attack/enterprise-attack.json"
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
