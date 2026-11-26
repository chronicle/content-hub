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

from my_sql.core import MySQLManager
from my_sql.tests.core.session import MySQLSession

if TYPE_CHECKING:
    from integration_testing.requests.session import DefaultSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(autouse=True)
def mysql_session(monkeypatch: pytest.MonkeyPatch) -> MySQLSession:
    """Mock MySQL session connection."""
    session = MySQLSession()
    monkeypatch.setattr(
        MySQLManager.mysql.connector,
        "connect",
        lambda **_kwargs: session,
    )
    return session


@pytest.fixture(name="sdk_session", autouse=True)
def sdk_session_fixture(script_session: DefaultSession) -> DefaultSession:
    return script_session
