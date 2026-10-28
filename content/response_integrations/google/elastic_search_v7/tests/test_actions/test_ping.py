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

from unittest.mock import MagicMock, patch

import pytest

from ...actions import Ping
from .. import common


def test_ping_success() -> None:
    mock_siemplify = MagicMock()
    mock_siemplify.get_configuration.return_value = dict(common.CONFIG)

    with (
        patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify),
        patch.object(Ping, "ElasticsearchManager") as mock_manager_cls,
    ):
        mock_manager_cls.return_value.test_connectivity.return_value = True
        Ping.main.__wrapped__()

    mock_manager_cls.return_value.test_connectivity.assert_called_once()
    mock_siemplify.end.assert_called_once_with("Connected Successfully", True)


def test_ping_failure() -> None:
    mock_siemplify = MagicMock()
    mock_siemplify.get_configuration.return_value = dict(common.CONFIG)

    with (
        patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify),
        patch.object(Ping, "ElasticsearchManager") as mock_manager_cls,
    ):
        mock_manager_cls.return_value.test_connectivity.side_effect = RuntimeError(
            "Connection refused"
        )
        with pytest.raises(RuntimeError, match="Connection refused"):
            Ping.main.__wrapped__()
