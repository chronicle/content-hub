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
from typing import Any, MutableMapping


@dataclasses.dataclass
class OpenSearchProduct(abc.ABC):
    """Represents a mock OpenSearch cluster's data store."""

    def __init__(self):
        # A dictionary to hold mock indices and their documents
        super().__init__()
        self._indices: MutableMapping[str, list[Any]] = {}
        self._cluster_info: dict = {}
        self._search_results: dict = {}

    def set_cluster_info(self, info: dict) -> None:
        self._cluster_info = info

    def get_cluster_info(self) -> dict:
        return self._cluster_info

    def set_search_results(self, results: dict) -> None:
        self._search_results = results

    def get_search_results(self) -> dict:
        return self._search_results

    def index_exists(self, index_name: str) -> bool:
        return index_name in self._indices
