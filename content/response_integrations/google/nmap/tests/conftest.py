
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

import pytest

from nmap.core.NmapManager import NmapManager


@pytest.fixture
def mock_soar_action(mocker):
    """Fixture for a mocked ChronicleSOAR action object."""
    action = mocker.MagicMock()
    action.is_remote = True
    return action


@pytest.fixture
def manager(mock_soar_action):  # pylint: disable=redefined-outer-name
    """Fixture for NmapManager instance."""
    return NmapManager(soar_action=mock_soar_action)


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


