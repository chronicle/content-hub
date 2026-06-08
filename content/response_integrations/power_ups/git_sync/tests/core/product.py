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

from typing import Any


class GitSyncProduct:
    """Mock in-memory state and mock API client for GitSync product (Chronicle SOAR API)."""

    def __init__(self) -> None:
        self.local_playbook: dict[str, Any] | None = None
        self.saved_playbook: dict[str, Any] | None = None

    def get_playbooks(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [self.local_playbook] if self.local_playbook else []

    def get_playbook(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        return self.local_playbook

    def get_soc_roles(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return []

    def get_playbook_categories(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": 10, "name": "Default"}]

    def save_playbook(self, playbook: dict[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.saved_playbook = playbook
        return {"status": "success"}
