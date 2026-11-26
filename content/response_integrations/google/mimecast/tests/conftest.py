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

import base64
import importlib
import json
import pkgutil
import sys
from typing import TYPE_CHECKING, NamedTuple

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

from integration_testing.common import use_live_api  # noqa: E402

from mimecast.core.MimecastManager import MimecastManager  # noqa: E402
from mimecast.tests.common import CONFIG_PATH  # noqa: E402
from mimecast.tests.core.product import Mimecast  # noqa: E402
from mimecast.tests.core.session import MimecastSession  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator

    from TIPCommon.types import SingleJson


# pylint: disable=redefined-outer-name
class IntegrationParameters(NamedTuple):
    app_id: str
    api_root: str
    app_key: str
    access_key: str
    secret_key: str
    client_id: str
    client_secret: str
    verify_ssl: bool


def read_config() -> IntegrationParameters:
    """Read config.json to get the integration credentials.

    Returns:
        IntegrationParameters: Integration parameters
    """
    data = CONFIG_PATH.read_text(encoding="utf-8")

    config: SingleJson = json.loads(data)
    api_root: str = config["API Root"]
    application_id: str = config["Application ID"]
    application_key: str = config["Application Key"]
    access_key: str = config["Access Key"]
    secret_key: str = config["Secret Key"]
    client_id: str = config["Client ID"]
    client_secret: str = config["Client Secret"]
    verify_ssl: bool = config["Verify SSL"]

    # Validate secret key
    try:
        base64.b64decode(secret_key)
    except Exception as e:
        raise ValueError(f"Invalid secret key in config.json: {e}") from e

    return IntegrationParameters(
        app_id=application_id,
        api_root=api_root,
        app_key=application_key,
        access_key=access_key,
        secret_key=secret_key,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
    )


@pytest.fixture(name="mimecast")
def mimecast_product() -> Iterator[Mimecast]:
    """Yield a mocked Mimecast product state instance."""
    yield Mimecast()


@pytest.fixture(name="script_session", autouse=True)
def mimecast_script_session(
    monkeypatch: pytest.MonkeyPatch,
    mimecast: Mimecast,
) -> Iterator[MimecastSession]:
    """Create and patch the Mimecast HTTP session."""
    session = MimecastSession(mimecast)
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
    yield session


@pytest.fixture(name="manager")
def mimecast_manager() -> Iterator[MimecastManager]:
    """Create a MimecastManager instance from test configuration."""
    config: IntegrationParameters = read_config()

    yield MimecastManager(
        api_root=config.api_root,
        app_id=config.app_id,
        app_key=config.app_key,
        access_key=config.access_key,
        secret_key=config.secret_key,
        client_id=config.client_id,
        client_secret=config.client_secret,
        verify_ssl=config.verify_ssl,
    )
