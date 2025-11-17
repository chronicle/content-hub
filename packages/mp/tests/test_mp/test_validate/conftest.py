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

import pathlib
import shutil
import tempfile
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def temp_integration(non_built_integration: pathlib.Path) -> Iterator[pathlib.Path]:
    """Create a temporary integration directory with mock files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = pathlib.Path(temp_dir)

        # Get the name of the valid parent directory
        parent_name = non_built_integration.parent.name

        temp_integration_parent = temp_root / parent_name
        temp_integration_parent.mkdir()

        # Copy the integration inside the valid parent directory
        temp_integration_path = temp_integration_parent / non_built_integration.name
        shutil.copytree(non_built_integration.resolve(), temp_integration_path)

        yield temp_integration_path
