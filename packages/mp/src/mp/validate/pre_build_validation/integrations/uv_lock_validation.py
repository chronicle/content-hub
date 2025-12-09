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

import dataclasses
from typing import TYPE_CHECKING

import mp.core.file_utils
import mp.core.unix
from mp.core.unix import NonFatalCommandError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class UvLockValidation:
    name: str = "Uv Lock"

    @staticmethod
    def run(integration_path: Path) -> None:
        """Check if the 'uv.lock' file is consistent with the 'pyproject.toml' file.

        Args:
            integration_path (Path): Path to the integration directory.

        Raises:
        NonFatalCommandError: If the 'uv lock --check' command indicates that the
                      'uv.lock' file is out of sync or if another error
                      occurs during the check.

        """
        if not mp.core.file_utils.is_built(integration_path):
            try:
                mp.core.unix.check_lock_file(integration_path)
            except NonFatalCommandError as e:
                raise NonFatalCommandError(str(e)) from e
