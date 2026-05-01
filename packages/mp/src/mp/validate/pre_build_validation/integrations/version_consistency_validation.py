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

import dataclasses
import os
import tomllib
from typing import TYPE_CHECKING

import yaml

import mp.core.unix
from mp.core import constants
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class VersionConsistencyValidation:
    """Validate that pyproject.toml and release_notes.yaml versions match."""

    name: str = "Version Consistency Check"

    @staticmethod
    def run(path: Path) -> None:
        """Check that the version in pyproject.toml matches release_notes.yaml.

        Args:
            path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the versions don't match.

        """
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch("main", head_sha, path)
            if not changed:
                return

        pyproject = path / constants.PROJECT_FILE
        rn_path = path / constants.RELEASE_NOTES_FILE

        if not pyproject.exists() or not rn_path.exists():
            return

        with pyproject.open("rb") as f:
            toml_data = tomllib.load(f)

        toml_version = str(toml_data.get("project", {}).get("version", ""))

        rn_content = yaml.safe_load(rn_path.read_text(encoding="utf-8"))
        if not rn_content or not isinstance(rn_content, list):
            return

        # Get the latest release note version
        latest_rn = rn_content[-1]
        rn_version = str(latest_rn.get("integration_version", ""))

        # Normalize versions by stripping trailing ".0" for comparison
        # e.g. "1.0" matches "1", "2.0" matches "2"
        def _normalize(v: str) -> str:
            v = v.strip()
            while v.endswith(".0"):
                v = v[:-2]
            return v

        if _normalize(toml_version) != _normalize(rn_version):
            msg = f"pyproject.toml version ({toml_version}) doesn't match release_notes.yaml version ({rn_version})"
            raise NonFatalValidationError(msg)
