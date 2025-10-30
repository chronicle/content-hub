"""Module for restructuring an integration's code.

This module defines a class, `Code`, responsible for adjusting relative
imports within an integration's Python code after it has been copied to
its output directory. This ensures that the code functions correctly
in its new location.
"""

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

import mp.core.code_manipulation
import mp.core.constants
import mp.core.file_utils

from .restructurable import Restructurable

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class Code(Restructurable):
    out_path: Path

    def restructure(self) -> None:
        """Restructure an integration's code to its "out" path."""
        self._restructure_action_code()
        self._restructure_connectors_code()
        self._restructure_jobs_code()
        self._restructure_widget_code()
        self._restructure_managers_code()

    def _restructure_action_code(self) -> None:
        self._restructure_code(mp.core.constants.OUT_ACTION_SCRIPTS_DIR)

    def _restructure_connectors_code(self) -> None:
        self._restructure_code(mp.core.constants.OUT_CONNECTOR_SCRIPTS_DIR)

    def _restructure_jobs_code(self) -> None:
        self._restructure_code(mp.core.constants.OUT_JOB_SCRIPTS_DIR)

    def _restructure_widget_code(self) -> None:
        self._restructure_code(mp.core.constants.OUT_WIDGET_SCRIPTS_DIR)

    def _restructure_managers_code(self) -> None:
        self._restructure_code(mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR)

    def _restructure_code(self, dir_name: str) -> None:
        out_dir: Path = self.out_path / dir_name
        if not out_dir.exists():
            return

        files: set[Path] = {
            file for file in out_dir.iterdir() if mp.core.file_utils.is_python_file(file)
        }
        mp.core.code_manipulation.restructure_scripts_imports(files)
        mp.core.code_manipulation.format_python_files(files)
