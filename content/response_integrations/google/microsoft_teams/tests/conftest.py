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
import pathlib
import json
import pytest
import requests
from microsoft_teams.core.MicrosoftManager import MicrosoftTeamsManager
from microsoft_teams.tests.core.microsoft_teams import MicrosoftTeams
from microsoft_teams.tests.core.session import MicrosoftTeamsSession
from integration_testing.common import get_def_file_content, use_live_api


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = get_def_file_content(CONFIG_PATH)


@pytest.fixture(scope="module")
def mock_data() -> dict:
    """Loads mock data from the JSON file for the entire test module."""
    mock_data_path: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
    with open(mock_data_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def microsoft_teams() -> MicrosoftTeams:
    """Fixture for the mock product."""
    yield MicrosoftTeams()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    microsoft_teams: MicrosoftTeams,  # pylint: disable=redefined-outer-name
    mock_data: dict,  # pylint: disable=redefined-outer-name
) -> MicrosoftTeamsSession:
    session = MicrosoftTeamsSession(microsoft_teams, mock_data)
    """Main fixture: replaces requests.Session with our mock session."""
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
    yield session


@pytest.fixture
def microsoft_teams_manager() -> MicrosoftTeamsManager:
    """Fixture that creates an instance of our manager with parameters"""
    manager: MicrosoftTeamsManager = MicrosoftTeamsManager(
        client_id=CONFIG["Client ID"],
        client_secret=CONFIG["Secret ID"],
        tenant=CONFIG["Tenant"],
        refresh_token=CONFIG["Refresh Token"],
        redirect_url=CONFIG["Redirect URL"],
        verify_ssl=CONFIG["Verify SSL"],
        api_root=CONFIG.get("API Root"),
        login_api_root=CONFIG.get("Login API Root"),
    )
    yield manager

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
