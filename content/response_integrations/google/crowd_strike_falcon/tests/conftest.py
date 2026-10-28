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
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import json
import os
from typing import NamedTuple

import pytest
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession, MockJobCase
from integration_testing.common import use_live_api


class IntegrationParameters(NamedTuple):
    client_id: str
    client_secret: str
    use_ssl: bool
    api_root: str
    customer_id: str


def read_config() -> IntegrationParameters:
    """Read config.json to get the integration credentials.

    Returns:
        IntegrationParameters: Integration parameters

    """
    with open(
        os.path.join(os.path.dirname(__file__), "config.json"),
        encoding="UTF-8",
    ) as f:
        data = f.read()

    config = json.loads(data)
    api_root = config.get("API Root")
    client_id = config.get("Client API ID")
    client_secret = config.get("Client API Secret")
    use_ssl = config.get("Verify SSL")
    customer_id = config.get("Customer ID")

    return IntegrationParameters(
        client_id,
        client_secret,
        use_ssl,
        api_root,
        customer_id,
    )


@pytest.fixture(scope="module")
def mock_data() -> dict:
    return json.load(
        open(
            os.path.join(os.path.dirname(__file__), "mock_data.json"),
            encoding="utf-8",
        ),
    )


@pytest.fixture
def crowd_strike_falcon() -> CrowdStrikeFalcon:
    return CrowdStrikeFalcon()


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch) -> CrowdStrikeFalconSession:
    session = CrowdStrikeFalconSession(None)
    """Mock the SDK sessions and get it back to view request and response history"""

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    return session


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    crowd_strike_falcon: CrowdStrikeFalcon,
) -> CrowdStrikeFalconSession:
    session = CrowdStrikeFalconSession(crowd_strike_falcon)
    """Mock CrowdStrike Falcon scripts' session and get back an
    object to view request history
    """
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
    return session


@pytest.fixture
def crowd_strike_falcon_manager() -> CrowdStrikeManager:
    """CrowdStrikeFalcon manager"""
    config = read_config()
    if isinstance(config.use_ssl, str):
        config.use_ssl = config.use_ssl.lower() == "true"

    return CrowdStrikeManager(
        config.client_id,
        config.client_secret,
        config.use_ssl,
        config.api_root,
        config.customer_id,
    )


@pytest.fixture
def mock_job_case() -> type[MockJobCase]:
    """Standard native SIEMPLIFY JobCase object injector."""
    return MockJobCase


_PARAM_TYPE_MAP = {
    "boolean": 0,
    "integer": 1,
    "string": 2,
    "password": 3,
    "ip": 4,
    "email": 8,
}
_PARAM_MODE_MAP = {"regular": 0, "script": 2}


@pytest.fixture(autouse=True)
def _normalize_yaml_def_file(monkeypatch: pytest.MonkeyPatch) -> None:
    import integration_testing.common as it_common
    from integration_testing.platform.external_context import MockExternalContext

    if not hasattr(MockExternalContext, "get_loaded_row_value"):
        def _get_loaded_row_value(self, context_type, identifier, property_key):
            val = self.get_row_value(context_type=context_type, identifier=identifier, property_key=property_key)
            return json.loads(val) if isinstance(val, str) else val
        MockExternalContext.get_loaded_row_value = _get_loaded_row_value

    orig_get_def = it_common.get_def_file_content

    def _wrapped_get_def(def_file_path):
        data = orig_get_def(def_file_path)
        if isinstance(data, dict) and "parameters" in data and "Parameters" not in data:
            data["Parameters"] = [
                {
                    "Name": p["name"],
                    "DefaultValue": p.get("default_value"),
                    "IsMandatory": p.get("is_mandatory", False),
                    "Type": _PARAM_TYPE_MAP.get(str(p.get("type", "string")).lower(), 2),
                    "Mode": _PARAM_MODE_MAP.get(str(p.get("mode", "script")).lower(), 2),
                }
                for p in data["parameters"]
            ]
        return data

    monkeypatch.setattr(it_common, "get_def_file_content", _wrapped_get_def)


