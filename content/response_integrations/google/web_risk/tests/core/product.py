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
import pathlib
import abc

import dataclasses


@dataclasses.dataclass
class Product(abc.ABC):
    _threat_types_map: dict[str, list[str]] = dataclasses.field(default_factory=dict)

    def add_uri(self, uri: str, threat_types: list[str]) -> None:
        self._threat_types_map[uri] = threat_types

    def get_threat_types(self, uri: str) -> list[str]:
        return self._threat_types_map.get(uri)
