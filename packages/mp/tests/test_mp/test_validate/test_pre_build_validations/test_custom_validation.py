# Copyright 2025 Google LLC
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

import typing
from unittest import mock

import pytest

from mp.core.data_models.integration import Integration
from mp.core.unix import NonFatalCommandError
from mp.validate.pre_build_validation.custom_validation import (
    CustomValidation,
)

if typing.TYPE_CHECKING:
    import pathlib


def test_validation_fails_for_custom_integration(temp_integration: pathlib.Path) -> None:
    """
    Test that the validation fails with a NonFatalCommandError
    when an integration is marked as custom.
    """
    mock_integration = mock.MagicMock()

    mock_integration.raise_error_if_custom.side_effect = RuntimeError(
        "mock integration contains custom scripts:"
    )

    with mock.patch.object(Integration, "from_non_built_path", return_value=mock_integration):
        error_msg = "contains custom scripts"
        with pytest.raises(NonFatalCommandError, match=error_msg):
            CustomValidation.run(temp_integration)
