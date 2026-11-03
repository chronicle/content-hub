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

import pytest
import requests
from requests import Session

from TIPCommon.types import SingleJson

import Integrations.SysdigSecure.Managers.SysdigSecureAuthManager
from Integrations.SysdigSecure.Managers.SysdigSecureAuthManager import (
    AuthManager,
    AuthManagerParams,
)
from Integrations.SysdigSecure.Managers.SysdigSecureManager import ApiManager
from Tests.integrations.SysdigSecure.core.session import ApiSession
from Tests.mocks.common import get_json_file_content, use_live_api
from Tests.mocks.logger import Logger

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_json_file_content(CONFIG_PATH)


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
            Integrations.SysdigSecure.Managers.SysdigSecureAuthManager,
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
