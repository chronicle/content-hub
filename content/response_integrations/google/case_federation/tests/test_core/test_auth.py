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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from TIPCommon.base.utils import CreateSession

from ...core import auth as auth_module
from ...core.constants import CLOUD_PLATFORM_SCOPE, GCP_PROJECT_ID_ENV_VAR

if TYPE_CHECKING:
    import pytest
    import requests


def test_get_p4sa_credentials_passes_scope_and_quota_project(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_creds = MagicMock()
    mock_get_creds = MagicMock(return_value=mock_creds)
    mock_soar = MagicMock()
    monkeypatch.setenv(GCP_PROJECT_ID_ENV_VAR, "test-gcp-project")
    monkeypatch.setattr(auth_module, "get_secops_siem_tenant_credentials", mock_get_creds)

    result = auth_module.get_p4sa_credentials(mock_soar)

    assert result is mock_creds
    mock_get_creds.assert_called_once_with(
        chronicle_soar=mock_soar,
        target_scopes=[CLOUD_PLATFORM_SCOPE],
        quota_project_id="test-gcp-project",
    )


def test_refresh_p4sa_credentials_refreshes_and_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_creds = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    monkeypatch.setattr(auth_module, "get_p4sa_credentials", lambda _soar: mock_creds)
    monkeypatch.setattr(CreateSession, "create_session", lambda *_args, **_kwargs: mock_session)

    auth_module.refresh_p4sa_credentials(MagicMock(), verify_ssl=False)

    assert mock_session.verify is False
    mock_creds.refresh.assert_called_once()
    mock_session.__exit__.assert_called_once()


def test_create_p4sa_authorized_session_configures_verify_ssl(
    monkeypatch: pytest.MonkeyPatch,
    script_session: requests.Session,
) -> None:
    mock_creds = MagicMock()
    monkeypatch.setattr(auth_module, "get_p4sa_credentials", lambda _soar: mock_creds)

    http_client = auth_module.create_p4sa_authorized_session(MagicMock(), verify_ssl=False)

    assert script_session.verify is False
    assert isinstance(http_client, auth_module.AuthorizedSession)
    assert http_client.credentials is mock_creds
    assert http_client.verify is False
