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

import pytest

from csv_integration.tests.core.csv import CSV
from integration_testing.common import use_live_api


@pytest.fixture
def mock_csv_product() -> CSV:
    """Provides a mock CSV product (a simulated file system)."""
    yield CSV()


@pytest.fixture(autouse=True)
def mock_filesystem( # pylint: disable=redefined-outer-name
    monkeypatch: pytest.MonkeyPatch,
    mock_csv_product: CSV,
) -> None:
    """
    Mocks file system access for CSV tests by patching the built-in 'open'
    function.
    """
    if not use_live_api():
        monkeypatch.setattr("builtins.open", mock_csv_product.mock_open)

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
