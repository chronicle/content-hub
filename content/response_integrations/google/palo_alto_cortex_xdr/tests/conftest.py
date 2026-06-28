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

# Unify the soar_sdk namespace with the flat namespace for mocks
import sys
import pkgutil
import soar_sdk
changed = True
while changed:
    changed = False
    for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
        if name not in sys.modules:
            try:
                sys.modules[name] = __import__(f"soar_sdk.{name}", fromlist=[None])
                changed = True
            except Exception:
                pass

import os
import sys
import pkgutil
import pathlib


import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

import pytest
import requests
from SiemplifyBase import SiemplifyBase
from palo_alto_cortex_xdr.tests.core.product import PaloAltoCortexXDR
from palo_alto_cortex_xdr.tests.core.session import PaloAltoCortexXDRSession, PaloAltoCortexXDRSOARSession

@pytest.fixture(name="palo_alto_cortex_xdr")
def palo_alto_cortex_xdr_fixture() -> PaloAltoCortexXDR:
    return PaloAltoCortexXDR()

@pytest.fixture(name="script_session", autouse=True)
def script_session_fixture(
    monkeypatch: pytest.MonkeyPatch, palo_alto_cortex_xdr: PaloAltoCortexXDR
) -> PaloAltoCortexXDRSession:
    session = PaloAltoCortexXDRSession(palo_alto_cortex_xdr)
    monkeypatch.setattr(requests, "Session", lambda: session)
    return session

@pytest.fixture(name="soar_sdk_session", autouse=True)
def soar_sdk_session_fixture(
    monkeypatch: pytest.MonkeyPatch, palo_alto_cortex_xdr: PaloAltoCortexXDR
) -> PaloAltoCortexXDRSOARSession:
    session = PaloAltoCortexXDRSOARSession(palo_alto_cortex_xdr)
    monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    monkeypatch.setattr(SiemplifyBase, "_create_remote_session", lambda *_: session)
    return session

from palo_alto_cortex_xdr.core.XDRManager import XDRManager, ApiParameters
from unittest.mock import MagicMock

@pytest.fixture(name="manager")
def manager_fixture(script_session: PaloAltoCortexXDRSession) -> XDRManager:
    return XDRManager(
        session=requests.Session(),
        api_params=ApiParameters(api_root="https://test.com/"),
        logger=MagicMock(),
    )
