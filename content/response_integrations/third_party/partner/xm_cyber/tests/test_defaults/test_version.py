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

"""Tests for resolving the integration version used in the connector header."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from xm_cyber.core import constants


def test_version_read_from_package_metadata() -> None:
    """The installed package metadata wins over the fallback."""
    with patch.object(constants, "version", return_value="9.9") as mock_version:
        assert constants._get_integration_version() == "9.9"

    mock_version.assert_called_once_with(constants.INTEGRATION_IDENTIFIER)


def test_version_falls_back_when_metadata_missing() -> None:
    """A missing distribution falls back instead of raising at import time."""
    with patch.object(constants, "version", side_effect=PackageNotFoundError):
        assert constants._get_integration_version() == constants.FALLBACK_INTEGRATION_VERSION
