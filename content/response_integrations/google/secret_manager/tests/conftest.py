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

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def mock_sa_credentials() -> MagicMock:
    """Patch ``service_account.Credentials.from_service_account_info``.

    Returns the mock credentials object.
    """
    with patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
    ) as mock_from_sa:
        mock_creds: MagicMock = MagicMock()
        mock_creds.with_scopes.return_value = mock_creds
        mock_from_sa.return_value = mock_creds
        yield mock_creds


@pytest.fixture
def make_sa_json() -> Callable[..., str]:
    """Fixture that returns a function to create a service account JSON string."""

    def _make_sa_json(project_id: str = "test-project") -> str:
        info = {
            "type": "service_account",
            "project_id": project_id,
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
        return json.dumps(info)

    return _make_sa_json
