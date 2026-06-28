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
import abc

import dataclasses
import pathlib

from TIPCommon.types import SingleJson
from integration_testing.common import get_def_file_content


MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


@dataclasses.dataclass
class Product(abc.ABC):
    messages: list[SingleJson] = dataclasses.field(default_factory=dict)

    def set_messages(self, messages: list[SingleJson]):
        self.messages = messages

    def list_messages(self) -> list[SingleJson]:
        return self.messages
