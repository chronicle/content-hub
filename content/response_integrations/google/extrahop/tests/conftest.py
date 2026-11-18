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

from typing import TYPE_CHECKING

import pytest
import soar_sdk  # noqa: F401
from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from TIPCommon.base.utils import CreateSession

from extrahop.core.ExtrahopManager import (
    ApiParameters,
    ExtrahopManager,
)
from extrahop.tests.common import CONFIG
from extrahop.tests.core.product import Extrahop
from extrahop.tests.core.session import ExtrahopSession

if TYPE_CHECKING:
    from collections.abc import Iterator

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(name="extrahop")
def extrahop_product() -> Iterator[Extrahop]:
    yield Extrahop()


@pytest.fixture(name="script_session", autouse=True)
def extrahop_script_session(
    monkeypatch: pytest.MonkeyPatch,
    extrahop: Extrahop,
) -> Iterator[ExtrahopSession]:
    """Create script session."""
    session = ExtrahopSession(extrahop)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    yield session


@pytest.fixture(name="manager")
def extrahop_manager(script_session: ExtrahopSession) -> Iterator[ExtrahopManager]:
    """Extrahop manager."""
    api_root: str = CONFIG["API Root"]
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Client Secret"]

    logger = Logger()
    api_params: ApiParameters = ApiParameters(api_root, client_id, client_secret)

    yield ExtrahopManager(script_session, api_params, logger)
