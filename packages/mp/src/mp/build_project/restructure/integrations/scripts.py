"""Module for restructuring an integration's script files.

This module defines a class, `Scripts`, responsible for copying and organizing
the various script files (actions, connectors, jobs, widgets, managers, and
common scripts) of an integration to its designated output directory. It also
handles the removal of definition files from the script directories.
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

import mp.core.constants
import mp.core.file_utils

from .restructurable import Restructurable

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class Scripts(Restructurable):
    path: Path
    out_path: Path

    def restructure(self) -> None:
        """Restructure an integration's script files to its "out" path."""
        self._restructure_action_scripts()
        self._restructure_connectors_scripts()
        self._restructure_jobs_scripts()
        self._restructure_widget_scripts()
        self._restructure_managers_scripts()
        self._restructure_group_scripts()

    def _restructure_action_scripts(self) -> None:
        self._copy_script_from_dir(
            dir_name=mp.core.constants.ACTIONS_DIR,
            out_dir_name=mp.core.constants.OUT_ACTION_SCRIPTS_DIR,
        )

    def _restructure_connectors_scripts(self) -> None:
        self._copy_script_from_dir(
            dir_name=mp.core.constants.CONNECTORS_DIR,
            out_dir_name=mp.core.constants.OUT_CONNECTOR_SCRIPTS_DIR,
        )

    def _restructure_jobs_scripts(self) -> None:
        self._copy_script_from_dir(
            dir_name=mp.core.constants.JOBS_DIR,
            out_dir_name=mp.core.constants.OUT_JOB_SCRIPTS_DIR,
        )

    def _restructure_widget_scripts(self) -> None:
        self._copy_script_from_dir(
            dir_name=mp.core.constants.WIDGETS_DIR,
            out_dir_name=mp.core.constants.OUT_WIDGET_SCRIPTS_DIR,
        )

    def _restructure_managers_scripts(self) -> None:
        self._copy_script_from_dir(
            dir_name=mp.core.constants.CORE_SCRIPTS_DIR,
            out_dir_name=mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR,
        )

    def _restructure_group_scripts(self) -> None:
        script_dir: Path = self.path.parent / mp.core.constants.COMMON_SCRIPTS_DIR
        if not script_dir.exists():
            return
        out_dir: Path = self.out_path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
        mp.core.file_utils.flatten_dir(script_dir, out_dir)

    def _copy_script_from_dir(self, dir_name: str, out_dir_name: str) -> None:
        script_dir: Path = self.path / dir_name
        if not script_dir.exists():
            return

        out_dir: Path = self.out_path / out_dir_name
        out_dir.mkdir(exist_ok=True)
        mp.core.file_utils.flatten_dir(script_dir, out_dir)
        if out_dir.exists():
            mp.core.file_utils.remove_files_by_suffix_from_dir(
                out_dir,
                suffix=mp.core.constants.YAML_SUFFIX,
            )
