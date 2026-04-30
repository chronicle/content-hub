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


def _find_ping_file(actions_dir: Path) -> Path | None:
    """Find the Ping action file in the actions directory.

    Args:
        actions_dir: Path to the integration's actions directory.

    Returns:
        Path to the Ping file, or None if not found.

    """
    for name in ("Ping.py", "ping.py"):
        candidate = actions_dir / name
        if candidate.exists():
            return candidate
    return None


def _is_ping_changed_in_pr(path: Path) -> bool:
    """Check if the Ping file was modified in the current PR.

    Args:
        path: The path of the integration to validate.

    Returns:
        True if Ping was changed or if not running in CI.

    """
    head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
    if not head_sha:
        return True
    changed = mp.core.unix.get_files_unmerged_to_main_branch("main", head_sha, path)
    return any(p.name in {"Ping.py", "ping.py"} for p in changed)


@dataclasses.dataclass(slots=True, frozen=True)
class PingMessageFormatValidation:
    """Validate that Ping action output messages follow the content design guide.

    Only enforced on Ping files that are new or modified in the current PR
    to avoid flagging all existing integrations. Falls back to always-on
    when not running in CI (no GITHUB_PR_SHA).
    """

    name: str = "Ping Message Format Validation"

    @staticmethod
    def run(path: Path) -> None:
        """Check that Ping action messages match the required format.

        Args:
            path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If Ping messages don't match the format.

        """
        actions_dir = path / constants.ACTIONS_DIR
        if not actions_dir.is_dir():
            return

        if path.name in exclusions.get_excluded_names_without_ping_message_format():
            return

        ping_file = _find_ping_file(actions_dir)
        if ping_file is None or not _is_ping_changed_in_pr(path):
            return

        content = ping_file.read_text(encoding="utf-8")
        issues: list[str] = []

        if _SUCCESS_PATTERN not in content:
            issues.append(f"Ping success message must contain: '{_SUCCESS_PATTERN}'")

        if _FAILURE_PATTERN not in content:
            issues.append(f"Ping failure message must contain: '{_FAILURE_PATTERN}'")

        if issues:
            msg = f"{path.name}: " + "; ".join(issues)
            raise NonFatalValidationError(msg)
