
from __future__ import annotations

# Unify the soar_sdk namespace with the flat namespace for mocks
import sys
import pkgutil
import soar_sdk
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    if name not in sys.modules:
        try:
            sys.modules[name] = __import__(f"soar_sdk.{name}", fromlist=[None])
        except Exception:
            pass

import os
import sys
import pkgutil
import pathlib


import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

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

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon

# Add parent directory and integration directory to sys.path to support internal module resolution

import cryptography.hazmat.primitives.serialization
import google.auth.transport.requests
import pytest
from TIPCommon.base.utils import CreateSession
from SiemplifyBase import SiemplifyBase

from okta.tests.core.product import (
    Product,
)
from okta.tests.core.session import (
    Session,
)
from integration_testing.common import use_live_api

# pylint: disable=redefined-outer-name


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
        okta_product: Product,
) -> Session:
    """Mock Okta scripts' session and get back an object to
    view request history
    """
    session: Session = (
        Session(okta_product)
    )

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
        monkeypatch.setattr(SiemplifyBase, "_create_remote_session", lambda *_: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *_, **__: session,
        )
        monkeypatch.setattr(
            cryptography.hazmat.primitives.serialization,
            "load_pem_private_key",
            lambda *_, **__: "private_key",
        )

    return session


@pytest.fixture
def okta_product() -> Product:
    return Product()


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


