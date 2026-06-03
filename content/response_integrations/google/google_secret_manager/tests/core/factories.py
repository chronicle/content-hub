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

import json
from typing import Any
from unittest.mock import MagicMock

from google.cloud import secretmanager


# ---------------------------------------------------------------------------
# Fake Service Account JSON
# ---------------------------------------------------------------------------

_FAKE_SA_INFO: dict[str, str] = {
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key-id",
    "private_key": (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWep4PAtGoRBh0VFnMD"
        "lOIA7RkVhmFJR\n"
        "-----END RSA PRIVATE KEY-----\n"
    ),
    "client_email": "test@test-project.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def make_sa_json(
    project_id: str = "test-project",
) -> str:
    """Return a fake Service Account JSON string."""
    info: dict[str, str] = {**_FAKE_SA_INFO, "project_id": project_id}

    return json.dumps(info)


# ---------------------------------------------------------------------------
# Mock SecretVersion proto
# ---------------------------------------------------------------------------


def make_secret_version(
    project_id: str = "test-project",
    secret_id: str = "my-secret",
    version_id: str = "1",
    state: int = secretmanager.SecretVersion.State.ENABLED,
) -> MagicMock:
    """Build a mock ``SecretVersion`` protobuf object."""
    version: MagicMock = MagicMock()
    version.name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    version.state = state

    return version


# ---------------------------------------------------------------------------
# Mock AccessSecretVersionResponse
# ---------------------------------------------------------------------------


def make_access_response(
    payload_data: bytes = b"super-secret-value",
) -> MagicMock:
    """Build a mock ``AccessSecretVersionResponse``."""
    response: MagicMock = MagicMock()
    response.payload.data = payload_data

    return response


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
