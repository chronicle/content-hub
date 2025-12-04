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
from enum import Enum

DEFANG_TEXT_SCRIPT_NAME: str = "Defang Text"
CALCULATE_TIMESTAMP_SCRIPT_NAME: str = "Calculate Timestamp"
DEFAULT_TIMESTAMP_DELTA: str = "+30M,-30M"
TIMESTAMP_DELTA_REGEX = re.compile(r"^([+-])(\d+)([mdHMS])$")
DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR: str = "epoch"


class InputType(str, Enum):
    """Supported input timestamp types."""

    CURRENT_TIME = "Current Time"
    ALERT_CREATION_TIME = "Alert Creation Time"
    CASE_CREATION_TIME = "Case Creation Time"
    CUSTOM_TIMESTAMP = "Custom Timestamp"
