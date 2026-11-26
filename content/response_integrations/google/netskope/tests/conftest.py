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

import sys
from unittest.mock import MagicMock

import pytest
import soar_sdk  # noqa: F401

sys.stdout = sys.__stdout__


@pytest.fixture(autouse=True)
def mock_siemplify(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock SiemplifyAction for all actions to prevent sys.argv crashes.

    Args:
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        MagicMock: mock siemplify object.
    """
    mock_api: MagicMock = MagicMock()
    mock_api.LOGGER = MagicMock()
    mock_api.result = MagicMock()
    mock_api.end = MagicMock()

    # List of actions to mock
    actions: list[str] = [
        "Ping",
        "ListAlerts",
        "AddEntitiesToURLList",
        "AllowFile",
        "BlockFile",
        "DeployURLListChanges",
        "DownloadFile",
        "ListClients",
        "ListEvents",
        "ListQuarantinedFiles",
    ]

    for action in actions:
        try:
            monkeypatch.setattr(
                f"netskope.actions.{action}.SiemplifyAction",
                MagicMock(return_value=mock_api, LOGGER=mock_api.LOGGER),
            )
        except (AttributeError, ModuleNotFoundError):
            pass

    return mock_api
