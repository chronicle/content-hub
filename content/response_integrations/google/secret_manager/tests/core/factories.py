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

"""Factory helpers for building mock Secret Manager API objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from secret_manager.core.manager import SecretManagerClient

if TYPE_CHECKING:
    from TIPCommon.base.interfaces import ScriptLogger


def make_client(
    service_account_json: str | None = None,
    project_id: str | None = None,
    workload_identity_email: str | None = None,
    logger: ScriptLogger | MagicMock | None = None,
    verify_ssl: bool = True,
) -> SecretManagerClient:
    """Build a SecretManagerClient with a default mock logger."""
    if logger is None:
        logger = MagicMock()

    return SecretManagerClient(
        service_account_json=service_account_json,
        project_id=project_id,
        workload_identity_email=workload_identity_email,
        logger=logger,
        verify_ssl=verify_ssl,
    )


# ---------------------------------------------------------------------------
# Config dict helpers
# ---------------------------------------------------------------------------


def make_config(
    sa_json: str | None = None,
    project_id: str | None = None,
    workload_identity_email: str | None = None,
) -> dict[str, Any]:
    """Build an integration config dict for use with set_metadata."""

    return {
        "Service Account JSON": sa_json,
        "Project ID": project_id,
        "Workload Identity Email": workload_identity_email,
    }
