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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class DevEnvClient(abc.ABC):
    """Abstract backend client for the dev-env ``push``/``pull`` commands.

    Concrete clients (the legacy SOAR ``BackendAPI`` and the Chronicle ``ChronicleClient``)
    explicitly subclass this and implement every method, so conformance is enforced at
    class-definition/instantiation time. Command code depends only on this type; which
    concrete client is built is decided by ``mp.dev_env.utils.get_backend_api`` from the
    stored ``auth_mode``.
    """

    @abc.abstractmethod
    def login(self) -> None:
        """Authenticate and/or verify connectivity to the backend."""

    @abc.abstractmethod
    def get_integration_details(self, zip_path: Path, *, is_staging: bool = False) -> dict[str, Any]:
        """Inspect a zipped integration package and return its parsed items/metadata."""

    @abc.abstractmethod
    def upload_integration(self, zip_path: Path, integration_id: str, *, is_staging: bool = False) -> dict[str, Any]:
        """Upload (import) a zipped integration package."""

    @abc.abstractmethod
    def download_integration(self, integration_name: str) -> bytes:
        """Download (export) an integration package and return the raw ZIP bytes."""

    @abc.abstractmethod
    def upload_playbook(self, zip_path: Path) -> dict[str, Any]:
        """Upload (import) a zipped playbook package."""

    @abc.abstractmethod
    def list_playbooks(self) -> list[dict[str, Any]]:
        """List installed playbooks' metadata."""

    @abc.abstractmethod
    def download_playbook(self, playbook_identifier: str) -> dict[str, Any]:
        """Download (export) a playbook definition by identifier."""
