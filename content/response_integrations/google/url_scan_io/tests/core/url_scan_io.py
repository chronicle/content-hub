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


@dataclasses.dataclass
class UrlScanIo(abc.ABC):
    """
    Imitates the UrlScanIo product backend state.
    """
    scans: list[dict] = dataclasses.field(default_factory=list)

    def add_scan(self, scan_data: dict) -> None:
        """Adds a new scan to the mock database."""
        self.scans.append(scan_data)

    def search_scans(self, query: str) -> list[dict]:
        """Searches for scans matching the query."""
        # Simple mock implementation: return all if query matches domain
        return [
            scan for scan in self.scans
            if query in scan.get("task", {}).get("domain", "") or query in scan.get(
                "task",
                {}
            ).get("url", "")
        ]
