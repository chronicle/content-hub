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
import sys
import sysconfig

# Replicate SOAR runtime environment where soar_sdk modules are at the root of sys.path.
_SITE_PACKAGES = pathlib.Path(sysconfig.get_paths()["purelib"])
_SOAR_SDK_DIR = _SITE_PACKAGES / "soar_sdk"
if _SOAR_SDK_DIR.is_dir() and str(_SOAR_SDK_DIR) not in sys.path:
    sys.path.insert(0, str(_SOAR_SDK_DIR))

# Replicate integration packaging environment where parent integration directory is in sys.path.
_INTEGRATION_PARENT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_INTEGRATION_PARENT) not in sys.path:
    sys.path.insert(0, str(_INTEGRATION_PARENT))


from typing import Any
from unittest.mock import MagicMock

import pytest
from integration_testing.common import create_entity, use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from TIPCommon.base.action import EntityTypesEnum

from misp.actions import AddAttribute
from misp.tests import common
from misp.tests.core.product import MISPProduct
from misp.tests.core.session import MISPSession

pytest_plugins: tuple[str, ...] = ("integration_testing.conftest",)


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "execution_scope(scope): mark test case to run under execution scope",
    )


@pytest.fixture(name="misp_product")
def misp_mock_product() -> MISPProduct:
    """Yield configured MISP mock product instance."""
    return MISPProduct()


@pytest.fixture(name="script_session", autouse=True)
def misp_mock_script_session(
    monkeypatch: pytest.MonkeyPatch,
    misp_product: MISPProduct,
) -> MISPSession:
    """Yield script session intercepting all HTTP calls to map mock API routing."""
    session: MISPSession[MockRequest, MockResponse, MISPProduct] = MISPSession(
        misp_product
    )
    if not use_live_api():
        monkeypatch.setattr("misp.core.MISPManager.requests.Session", lambda *_: session)

    return session


@pytest.fixture(autouse=True)
def configure_execution_scope(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Patch execution scope dynamically based on test markers."""
    marker: Any = request.node.get_closest_marker("execution_scope")
    scope_value: Any = AddAttribute.ExecutionScope.Alert

    if marker:
        scope_name: str = str(marker.args[0]).strip().title()
        if scope_name == "Case":
            scope_value = AddAttribute.ExecutionScope.Case
        elif scope_name == "Alert":
            scope_value = AddAttribute.ExecutionScope.Alert

    monkeypatch.setattr(
        AddAttribute.SiemplifyAction, "execution_scope", scope_value, raising=False
    )
    monkeypatch.setattr(
        AddAttribute.SiemplifyAction,
        "execution_deadline_unix_time_ms",
        sys.maxsize,
        raising=False,
    )
    monkeypatch.setattr(AddAttribute, "unix_now", lambda: -1, raising=False)

    entity: Any = create_entity(
        identifier=common.HOSTNAME_ENTITY_ID, type_=EntityTypesEnum.HOST_NAME
    )
    mock_alert: MagicMock = MagicMock()
    mock_alert.name = "MISP Alert"
    mock_alert.entities = [entity]
    mock_alert.relations = []

    if scope_value == AddAttribute.ExecutionScope.Case:
        mock_case: MagicMock = MagicMock()
        mock_case.open_alerts = [mock_alert]
        mock_case.alerts = [mock_alert]
        monkeypatch.setattr(
            AddAttribute.SiemplifyAction, "case", mock_case, raising=False
        )
    else:
        monkeypatch.setattr(
            AddAttribute.SiemplifyAction, "current_alert", mock_alert, raising=False
        )
        monkeypatch.setattr(
            AddAttribute.SiemplifyAction,
            "_get_current_alert",
            lambda self: mock_alert,
            raising=False,
        )
