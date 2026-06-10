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

import dataclasses
from typing import Any


@dataclasses.dataclass(slots=True)
class Tools:
    case_title: str = "Original Title"
    workflows: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    case_metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    alerts_full_details: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    def get_case_metadata(self, case_id: str) -> dict[str, Any]:
        """Retrieve simulated case metadata header context."""
        return self.case_metadata

    def set_case_metadata(self, metadata: dict[str, Any]) -> None:
        """Set simulated case metadata header context."""
        self.case_metadata = metadata

    def get_alerts_full_details(self, case_id: str) -> list[dict[str, Any]]:
        """Retrieve simulated full alert details for the case."""
        return self.alerts_full_details

    def set_alerts_full_details(self, alerts: list[dict[str, Any]]) -> None:
        """Set simulated full alert details for the case."""
        self.alerts_full_details = alerts

    def get_workflows(self) -> list[dict[str, Any]]:
        """Retrieve all simulated playbooks/workflows."""
        return self.workflows

    def set_workflows(self, workflows: list[dict[str, Any]]) -> None:
        """Set simulated playbooks/workflows."""
        self.workflows = workflows

    def rename_case(self, new_title: str) -> dict[str, Any]:
        """Simulate case renaming."""
        self.case_title = new_title
        # Sync it into case metadata title too!
        if "title" in self.case_metadata:
            self.case_metadata["title"] = new_title
        return {"isSuccessful": True}
