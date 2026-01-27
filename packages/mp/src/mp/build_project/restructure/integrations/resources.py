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
import shutil
from typing import TYPE_CHECKING

import mp.core.constants

from .restructurable import Restructurable

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class Resources(Restructurable):
    path: Path
    out_path: Path

    def restructure(self) -> None:
        """Restructure an integration's resource files to its "out" path."""
        src_resources: Path = self.path / mp.core.constants.RESOURCES_DIR
        if not src_resources.exists():
            return

        dest_resources: Path = self.out_path / mp.core.constants.RESOURCES_DIR
        shutil.copytree(src_resources, dest_resources, dirs_exist_ok=True)
