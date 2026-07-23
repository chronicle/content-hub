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

import pytest
from soar_sdk.SiemplifyJob import SiemplifyJob

from ...core import FederationSyncManager as manager_module
from ..core.mocks import GetFederationCasesStub, MockHttpClient


@pytest.fixture
def mock_http_client() -> MockHttpClient:
    return MockHttpClient()


@pytest.fixture(autouse=True)
def mock_manager_auth(
    monkeypatch: pytest.MonkeyPatch,
    mock_http_client: MockHttpClient,
) -> None:
    """Bypass GCP credentials creation and replace the AuthorizedSession client."""
    monkeypatch.setattr(
        manager_module.FederationSyncManager,
        "_get_credentials_using_p4sa",
        lambda self, verify_ssl: None,
    )
    monkeypatch.setattr(
        manager_module.FederationSyncManager,
        "_prepare_http_client",
        lambda self: setattr(self, "http_client", mock_http_client),
    )


@pytest.fixture
def federation_cases(monkeypatch: pytest.MonkeyPatch) -> GetFederationCasesStub:
    """Stub the SOAR API call that fetches cases to sync."""
    stub = GetFederationCasesStub()
    monkeypatch.setattr(manager_module, "get_federation_cases", stub)
    return stub


@pytest.fixture
def job_context() -> dict:
    """In-memory replacement for the job context properties storage."""
    return {}


@pytest.fixture(autouse=True)
def mock_job_context(monkeypatch: pytest.MonkeyPatch, job_context: dict) -> None:
    def get_property(self, identifier, property_key):
        return job_context.get((identifier, property_key))

    def set_property(self, identifier, property_key, property_value):
        job_context[(identifier, property_key)] = property_value

    monkeypatch.setattr(SiemplifyJob, "get_job_context_property", get_property)
    monkeypatch.setattr(SiemplifyJob, "set_job_context_property", set_property)