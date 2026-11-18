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

import pathlib
from typing import TYPE_CHECKING

import google.auth
import google.auth.compute_engine
import google.auth.transport.requests
import pytest
import requests
import soar_sdk  # noqa: F401
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger

import g_suite.core.GSuiteAuth
from g_suite.core.datamodels import IntegrationParameters
from g_suite.core.GSuiteAuth import GSuiteAuthManager
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession

if TYPE_CHECKING:
    from collections.abc import Iterator

    from TIPCommon.types import SingleJson

pytest_plugins = ("integration_testing.conftest",)

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture
def product() -> Product:
    """Return mock GSuite product state."""
    return Product()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    product: Product,
) -> Iterator[ApiSession]:
    """Mock GSuite API session and credentials for offline testing."""
    session = ApiSession(product)
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *_args, **_kwargs: session,
        )
        monkeypatch.setattr(
            g_suite.core.GSuiteAuth,
            "AuthorizedSession",
            lambda *_args, **_kwargs: session,
        )
        monkeypatch.setattr(
            google.auth,
            "default",
            lambda *_args, **_kwargs: (
                google.auth.compute_engine.Credentials(),
                "mock-project",
            ),
        )
    yield session


@pytest.fixture
def _script_session(script_session: ApiSession) -> ApiSession:
    """Alias for script_session used by tests that discard the session object."""
    return script_session


@pytest.fixture
def _product(product: Product) -> Product:
    """Alias for product used by tests that discard the product object."""
    return product


@pytest.fixture
def gsuite_api_manager() -> GSuiteManager:
    """Return configured GSuiteManager instance for unit tests."""
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    delegated_email = CONFIG["Delegated Email"]
    service_account_creds = CONFIG["Service Account JSON"]
    auth_manager = GSuiteAuthManager(
        service_account_creds=service_account_creds,
        verify_ssl=verify_ssl,
        delegated_email=delegated_email,
        workload_identity_email=workload_identity_email,
    )

    return GSuiteManager(
        session=auth_manager.prepare_session(),
        params=IntegrationParameters(Logger()),
    )
