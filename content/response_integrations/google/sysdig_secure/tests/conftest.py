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

import pytest
import requests
from requests import Session

from TIPCommon.types import SingleJson

import sysdig_secure.core.SysdigSecureAuthManager
from sysdig_secure.core.SysdigSecureAuthManager import (
    AuthManager,
    AuthManagerParams,
)
from sysdig_secure.core.SysdigSecureManager import ApiManager
from sysdig_secure.tests.core.session import ApiSession
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture(autouse=True)
def sysdig_script_session(
    mocker,
    monkeypatch: pytest.MonkeyPatch,
) -> ApiSession:
    """Mock Sysdig Secure session and get back an object to view request history"""
    session = ApiSession()
    # pylint: disable=protected-access
    session._auth_request = session.credentials = mocker.Mock()
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            Session,
            "__new__",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            sysdig_secure.core.SysdigSecureAuthManager,
            "Session",
            lambda *args, **kwargs: session
        )

    yield session


# pylint: disable=redefined-outer-name
@pytest.fixture
def sysdig_manager() -> ApiManager:
    """SysDid Secure ApiManager."""
    api_root = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    api_token = CONFIG["API Token"]
    auth_params = AuthManagerParams(
        verify_ssl=verify_ssl,
        api_root=api_root,
        api_token=api_token,
    )
    auth_manager = AuthManager(auth_params)

    return ApiManager(
        api_root=api_root,
        session=auth_manager.prepare_session(),
        logger=Logger()
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
