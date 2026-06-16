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

from typing import Any

import pytest
import requests
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from proof_point_ps.tests.core.product import ProofPointPSProduct
from proof_point_ps.tests.core.session import ProofPointPSSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def proofpoint() -> ProofPointPSProduct:
    """Fixture for mock product database."""
    return ProofPointPSProduct()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    proofpoint: ProofPointPSProduct,
) -> ProofPointPSSession:
    """Mock Proofpoint scripts' session and return the mock session object."""
    session = ProofPointPSSession(proofpoint)

    if not use_live_api():
        class MockSessionClass(requests.Session):
            def __new__(cls, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401, PYI034
                return session

        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
        monkeypatch.setattr("requests.Session", MockSessionClass)

    return session


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    proofpoint: ProofPointPSProduct,
) -> ProofPointPSSession:
    """Mock the SDK session and return the mock session object."""
    session = ProofPointPSSession(proofpoint)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    return session
