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

import os
import site
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from TIPCommon.rest.soar_platform_clients.legacy_soar_api import LegacySoarApi
    from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi


def pytest_configure(config: pytest.Config) -> None:
    """Lifecycle hook called when pytest starts up.

    Dynamically finds the installed soar-sdk site-packages directory
    and appends it to sys.path before any test imports happen.
    """
    sys.path.extend([
        os.path.join(d, "soar_sdk") for d in site.getsitepackages() if os.path.isdir(os.path.join(d, "soar_sdk"))
    ])


@pytest.fixture
def mock_chronicle_soar(mocker: MockerFixture) -> MagicMock:
    chronicle_soar = mocker.MagicMock()
    chronicle_soar.session = mocker.MagicMock()
    chronicle_soar.LOGGER = mocker.MagicMock()
    return chronicle_soar


@pytest.fixture
def mock_get_sdk_api_uri(mocker: MockerFixture) -> MagicMock:
    mock_uri = mocker.patch("TIPCommon.rest.soar_platform_clients.base_soar_api.get_sdk_api_uri")
    mock_uri.return_value = "https://mock-soar-api.com"
    return mock_uri


@pytest.fixture
def mock_platform_supports_1p(mocker: MockerFixture) -> MagicMock:
    mock_support = mocker.patch("TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api")
    mock_support.return_value = True
    return mock_support


@pytest.fixture
def mock_legacy_client(mock_chronicle_soar: MagicMock) -> "LegacySoarApi":
    # Import is placed inside the fixture to defer its execution until
    # after `pytest_configure` runs and updates `sys.path` with `soar_sdk`.
    from TIPCommon.rest.soar_platform_clients.legacy_soar_api import LegacySoarApi

    client = LegacySoarApi(mock_chronicle_soar)
    return client


@pytest.fixture
def mock_oneplatform_client(mock_chronicle_soar: MagicMock) -> "OnePlatformSoarApi":
    # Import is placed inside the fixture to defer its execution until
    # after `pytest_configure` runs and updates `sys.path` with `soar_sdk`.
    from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi

    client = OnePlatformSoarApi(mock_chronicle_soar)
    return client
