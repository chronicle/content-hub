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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import SingleJson


class DevEnvClient(abc.ABC):
    """Abstract backend client for dev-env push and pull commands.

    Concrete clients (legacy BackendAPI and ChronicleClient) subclass this
    and implement all methods.
    """

    @abc.abstractmethod
    def login(self) -> None:
        """Authenticate and verify connectivity to the backend."""

    @abc.abstractmethod
    def get_integration_details(
        self,
        zip_path: Path,
        *,
        is_staging: bool = False,
    ) -> SingleJson:
        """Inspect a zipped integration package and return parsed metadata."""

    @abc.abstractmethod
    def upload_integration(
        self,
        zip_path: Path,
        integration_id: str,
        *,
        is_staging: bool = False,
    ) -> SingleJson:
        """Upload an integration package to the backend."""

    @abc.abstractmethod
    def download_integration(self, integration_name: str) -> bytes:
        """Download an integration package as raw ZIP bytes."""

    @abc.abstractmethod
    def upload_playbook(self, zip_path: Path) -> SingleJson:
        """Upload a playbook package to the backend."""

    @abc.abstractmethod
    def list_playbooks(self) -> list[SingleJson]:
        """List installed playbooks metadata."""

    @abc.abstractmethod
    def download_playbook(self, playbook_identifier: str) -> SingleJson:
        """Download a playbook definition by identifier."""
