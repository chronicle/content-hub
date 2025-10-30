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

from typing import TYPE_CHECKING

import mp.core.file_utils
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    import pathlib


class StructureValidation:
    name: str = "Integration Structure Check"

    def run(self, integration_path: pathlib.Path) -> None:  # noqa: PLR6301
        """Check basic integration structure, including file presence and parity.

        Args:
            integration_path: Path to the integration directory.

        Raises:
            FatalValidationError: If the structure is invalid (missing files, parity error).

        """
        try:
            if not mp.core.file_utils.is_integration(integration_path):
                msg = "Missing essential files like pyproject.toml or integration def file."
                raise FatalValidationError(msg)
        except RuntimeError as e:
            raise FatalValidationError(str(e)) from e
