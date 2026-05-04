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

from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture()
def mock_sm_service_client() -> MagicMock:
    """Patch the gRPC SecretManagerServiceClient.

    Returns a ``MagicMock`` that stands in for the real client so
    tests can configure return values on ``list_secrets``,
    ``list_secret_versions``, and ``access_secret_version``.
    """
    with patch(
        "google.cloud.secretmanager.SecretManagerServiceClient",
    ) as mock_cls:
        mock_instance: MagicMock = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture()
def mock_sa_credentials() -> MagicMock:
    """Patch ``service_account.Credentials.from_service_account_info``.

    Returns the mock credentials object.
    """
    with patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
    ) as mock_from_sa:
        mock_creds: MagicMock = MagicMock()
        mock_from_sa.return_value = mock_creds
        yield mock_creds
