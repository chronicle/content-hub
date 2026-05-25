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

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture()
def mock_akeyless_api() -> MagicMock:
    """Patch akeyless V2Api class.

    Returns a MagicMock representing V2Api instance.
    """
    with patch("akeyless.V2Api") as mock_api_cls:
        mock_instance = MagicMock()
        mock_api_cls.return_value = mock_instance
        yield mock_instance
