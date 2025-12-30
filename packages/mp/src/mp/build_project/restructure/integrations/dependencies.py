"""Module for managing an integration's dependencies.

This module provides a class, `Dependencies`, that handles the process of
resolving and downloading the required dependencies for an integration.
It leverages temporary directories and files to manage the download process
and then copies the resolved dependencies to the integration's output path.
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
import pathlib
import shutil
import tempfile
from typing import TYPE_CHECKING

import anyio

import mp.core.constants
import mp.core.unix
import mp.core.utils

from .restructurable import AsyncRestructurable

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class Dependencies(AsyncRestructurable):
    path: Path
    out_path: Path

    async def restructure(self) -> None:
        """Restructure an integration's dependencies, downloading them to `out_path`."""
        requirements: anyio.Path = await mp.core.utils.run_threaded(self._prepare_requirements)
        try:
            with tempfile.TemporaryDirectory(prefix="dependencies_") as d:
                deps: Path = pathlib.Path(d)
                await mp.core.unix.download_wheels_from_requirements(
                    project_path=self.path,
                    requirements_path=pathlib.Path(requirements),
                    dst_path=deps,
                )
                await mp.core.utils.run_threaded(self._copy_dependencies, deps)
        finally:
            await requirements.unlink()

    def _prepare_requirements(self) -> anyio.Path:
        with tempfile.NamedTemporaryFile(
            mode="r",
            suffix=".txt",
            prefix="requirements_",
            encoding="utf8",
            delete=False,
        ) as f:
            requirements: anyio.Path = anyio.Path(f.name)

        mp.core.unix.compile_core_integration_dependencies(
            project_path=self.path,
            requirements_path=pathlib.Path(requirements),
        )
        return requirements

    def _copy_dependencies(self, deps: Path) -> None:
        out_deps: Path = self.out_path / mp.core.constants.OUT_DEPENDENCIES_DIR
        shutil.copytree(deps, out_deps)
