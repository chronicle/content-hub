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
import soar_sdk  # noqa: F401

from cb_cloud.core.CBCloudManager import CBCloudManager
from cb_cloud.tests.core.product import Product
from cb_cloud.tests.core.session import ApiSession
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger
from TIPCommon.types import SingleJson

pytest_plugins = ("integration_testing.conftest",)

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


# pylint: disable=redefined-outer-name
@pytest.fixture
def product() -> Product:
    return Product()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    product: Product,
) -> ApiSession:
    session = ApiSession(product)
    """Mock CBCloud API session and get back an object to view request history"""
    if not use_live_api():
        monkeypatch.setattr(requests, "session", lambda: session)
    yield session


@pytest.fixture
def cb_cloud_api_manager() -> CBCloudManager:
    """CBCloudManager manager"""
    api_root = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    org_key = CONFIG["Organization Key"]
    api_id = CONFIG["API ID"]
    api_secret_key = CONFIG["API Secret Key"]

    return CBCloudManager(
        api_root=api_root,
        org_key=org_key,
        api_id=api_id,
        api_secret_key=api_secret_key,
        verify_ssl=verify_ssl,
        logger=Logger(),
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
