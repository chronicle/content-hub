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

from ...core import federation_sync_manager as manager_module
from ..core.mocks import GetFederationCasesStub, MockHttpClient


@pytest.fixture
def mock_http_client(monkeypatch: pytest.MonkeyPatch) -> MockHttpClient:
    """Mock HTTP client that bypasses GCP credentials and replaces the AuthorizedSession."""
    client = MockHttpClient()
    monkeypatch.setattr(
        manager_module.FederationSyncManager,
        "_get_credentials_using_p4sa",
        lambda self: None,
    )
    monkeypatch.setattr(
        manager_module.FederationSyncManager,
        "_prepare_http_client",
        lambda self: setattr(self, "http_client", client),
    )
    return client


@pytest.fixture
def federation_cases(monkeypatch: pytest.MonkeyPatch) -> GetFederationCasesStub:
    """Stub the SOAR API call that fetches cases to sync."""
    stub = GetFederationCasesStub()
    monkeypatch.setattr(manager_module, "get_federation_cases", stub)
    return stub


@pytest.fixture
def job_context(monkeypatch: pytest.MonkeyPatch) -> dict:
    """In-memory replacement for the job context properties storage."""
    context: dict = {}

    def get_property(identifier: str, property_key: str) -> str | None:
        return context.get((identifier, property_key))

    def set_property(identifier: str, property_key: str, property_value: str) -> None:
        context[identifier, property_key] = property_value

    monkeypatch.setattr(SiemplifyJob, "get_job_context_property", get_property)
    monkeypatch.setattr(SiemplifyJob, "set_job_context_property", set_property)
    return context
