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

import pathlib
from typing import TYPE_CHECKING

from integration_testing.common import get_def_file_content

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
MOCK_DATA_PATH: pathlib.Path = INTEGRATION_PATH / "tests" / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_DATA_PATH)

SAMPLE_EMAIL_WITH_ENTITIES: SingleJson = MOCK_DATA["sample_email_with_entities"]

