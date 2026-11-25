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
from unittest.mock import MagicMock, patch

import pytest

from salesforce.actions import Ping

if TYPE_CHECKING:
    from collections.abc import Iterator

CONFIG: dict[str, str] = {
    "Api Root": "https://example.my.salesforce.com",
    "Username": "user",
    "Password": "pass",
    "Token": "token",
    "Verify SSL": "false",
}


@pytest.fixture
def sf_client() -> Iterator[MagicMock]:
    """Mock the Salesforce client used by SalesforceManager."""
    with patch("salesforce.core.SalesforceManager.Salesforce") as salesforce_cls:
        client: MagicMock = salesforce_cls.return_value
        client.query.return_value = {"records": [{"Id": "500A"}], "done": True}
        yield client


def test_ping_executes_lightweight_connectivity_query(sf_client: MagicMock) -> None:
    """Ping validates connectivity with SELECT Id FROM Case LIMIT 1 without paging."""
    with patch.object(Ping, "SiemplifyAction") as action_cls:
        siemplify: MagicMock = action_cls.return_value
        siemplify.get_configuration.return_value = CONFIG
        Ping.main()

    sf_client.query.assert_called_once_with("SELECT Id FROM Case LIMIT 1")
    sf_client.query_more.assert_not_called()
    siemplify.end.assert_called_once_with("Successfully connected.", "true")


def test_ping_propagates_connection_failure(sf_client: MagicMock) -> None:
    """Ping surfaces client exceptions when the connectivity query fails."""
    sf_client.query.side_effect = RuntimeError("INVALID_LOGIN")

    with patch.object(Ping, "SiemplifyAction") as action_cls:
        siemplify: MagicMock = action_cls.return_value
        siemplify.get_configuration.return_value = CONFIG
        with pytest.raises(RuntimeError, match="INVALID_LOGIN"):
            Ping.main()
