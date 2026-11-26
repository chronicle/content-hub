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

import importlib
import pkgutil
import sys
from typing import TYPE_CHECKING

import pytest
import requests
import soar_sdk

pytest_plugins = ("integration_testing.conftest",)

sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import TIPCommon  # noqa: E402

try:
    import TIPCommon.extraction
    import TIPCommon.transformation

    for _name in (
        "extract_configuration_param",
        "extract_action_param",
        "extract_script_param",
        "extract_connector_param",
    ):
        if not hasattr(TIPCommon, _name):
            setattr(TIPCommon, _name, getattr(TIPCommon.extraction, _name))
    for _name in (
        "construct_csv",
        "flat_dict_to_csv",
        "string_to_multi_value",
        "dict_to_flat",
        "add_prefix_to_dict",
    ):
        if not hasattr(TIPCommon, _name):
            setattr(TIPCommon, _name, getattr(TIPCommon.transformation, _name))
except ImportError:
    pass

from integration_testing.common import use_live_api  # noqa: E402

from mitre_attck.core.MitreAttckManager import MitreAttckManager  # noqa: E402
from mitre_attck.tests.common import ENTERPRISE_ATTACK  # noqa: E402
from mitre_attck.tests.core.product import MitreAttckProduct  # noqa: E402
from mitre_attck.tests.core.session import MitreAttckSession  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def mitre_product() -> MitreAttckProduct:
    """Provide a fresh MitreAttckProduct pre-loaded with the default STIX bundle."""
    product = MitreAttckProduct()
    product.set_attack_data(ENTERPRISE_ATTACK)
    return product


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    mitre_product: MitreAttckProduct,
) -> Iterator[MitreAttckSession]:
    """Intercept all requests.Session calls and route them to the product mock."""
    session = MitreAttckSession(mitre_product)
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
    yield session


@pytest.fixture
def mock_connectivity_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force MitreAttckManager.test_connectivity to raise an exception."""

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Simulated connectivity failure")

    monkeypatch.setattr(MitreAttckManager, "test_connectivity", _raise)


@pytest.fixture
def _script_session(script_session: MitreAttckSession) -> MitreAttckSession:
    """Alias for script_session — used in tests that reference the session for assertions."""
    return script_session
