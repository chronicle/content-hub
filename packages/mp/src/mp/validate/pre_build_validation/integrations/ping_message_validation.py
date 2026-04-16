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
from typing import TYPE_CHECKING

import mp.core.unix
from mp.core import constants, exclusions
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path

# Required substrings in Ping action output messages per the content design guide
_SUCCESS_PATTERN = "Successfully connected to the"
_FAILURE_PATTERN = "Failed to connect to the"


@dataclasses.dataclass(slots=True, frozen=True)
class PingMessageFormatValidation:
    """Validate that Ping action output messages follow the content design guide.

    Only enforced on Ping files that are new or modified in the current PR
    to avoid flagging all existing integrations. Falls back to always-on
    when not running in CI (no GITHUB_PR_SHA).
    """

    name: str = "Ping Message Format Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check that Ping action messages match the required format.

        The content design guide requires:
        - Success: "Successfully connected to the {integration name}..."
        - Failure: "Failed to connect to the {product name}..."

        Only runs when the Ping file is new or modified in the current PR.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If Ping messages don't match the format.

        """
        actions_dir = validation_path / constants.ACTIONS_DIR
        if not actions_dir.is_dir():
            return

        if validation_path.name in exclusions.get_excluded_names_without_ping_message_format():
            return

        # Find Ping action file (case-insensitive)
        ping_file = None
        for name in ("Ping.py", "ping.py"):
            candidate = actions_dir / name
            if candidate.exists():
                ping_file = candidate
                break

        if ping_file is None:
            return

        # Only enforce on files changed in the current PR
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch(
                "main", head_sha, validation_path
            )
            if not any(p.name in {"Ping.py", "ping.py"} for p in changed):
                return

        content = ping_file.read_text(encoding="utf-8")
        issues: list[str] = []

        if _SUCCESS_PATTERN not in content:
            issues.append(f"Ping success message must contain: '{_SUCCESS_PATTERN}'")

        if _FAILURE_PATTERN not in content:
            issues.append(f"Ping failure message must contain: '{_FAILURE_PATTERN}'")

        if issues:
            msg = f"{validation_path.name}: " + "; ".join(issues)
            raise NonFatalValidationError(msg)
