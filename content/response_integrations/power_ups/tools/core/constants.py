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
OCR_IMAGE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - OCR Image"

MAX_SYNC_DELAY_TIME_IN_SECONDS: int = 30
MIN_SYNC_DELAY_TIME_IN_SECONDS: int = 0
LABEL_REGEX: str = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
