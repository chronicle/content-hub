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

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class DevEnvClient(Protocol):
    """Backend client contract shared by the legacy SOAR and Chronicle API clients.

    Both ``mp.dev_env.api.BackendAPI`` (legacy Siemplify external API) and
    ``mp.dev_env.chronicle_api.ChronicleClient`` (GCP-native Chronicle API) implement
    this protocol so that the ``push``/``pull`` sub-commands remain agnostic to which
    backend is in use. Dispatch happens in ``mp.dev_env.utils.get_backend_api`` based on
    the stored ``auth_mode``.
    """

    def login(self) -> None:
        """Authenticate and/or verify connectivity to the backend."""
        ...

    def get_integration_details(self, zip_path: Path, *, is_staging: bool = False) -> dict[str, Any]:
        """Inspect a zipped integration package and return its parsed items/metadata."""
        ...

    def upload_integration(
        self,
        zip_path: Path,
        integration_id: str,
        *,
        is_staging: bool = False,
    ) -> dict[str, Any]:
        """Upload (import) a zipped integration package."""
        ...

    def download_integration(self, integration_name: str) -> bytes:
        """Download (export) an integration package and return the raw ZIP bytes."""
        ...

    def upload_playbook(self, zip_path: Path) -> dict[str, Any]:
        """Upload (import) a zipped playbook package."""
        ...

    def list_playbooks(self) -> list[dict[str, Any]]:
        """List installed playbooks' metadata."""
        ...

    def download_playbook(self, playbook_identifier: str) -> dict[str, Any]:
        """Download (export) a playbook definition by identifier."""
        ...
