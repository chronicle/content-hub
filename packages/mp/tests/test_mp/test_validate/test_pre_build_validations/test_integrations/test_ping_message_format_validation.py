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

"""Tests for the PingMessageFormatValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from mp.core import constants
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations.ping_message_validation import (
    PingMessageFormatValidation,
)

if TYPE_CHECKING:
    import pathlib

_GOOD_PING_CONTENT = """\
from __future__ import annotations

SCRIPT_NAME = "Ping"


def main() -> None:
    try:
        # attempt connectivity check
        pass
        output = "Successfully connected to the Mock Integration server with the provided connection parameters!"
    except Exception as e:
        output = f"Failed to connect to the Mock Integration server! Error is {e}"
    print(output)


if __name__ == "__main__":
    main()
"""

_MISSING_SUCCESS_PING_CONTENT = """\
from __future__ import annotations

SCRIPT_NAME = "Ping"


def main() -> None:
    try:
        pass
    except Exception as e:
        output = f"Failed to connect to the Mock Integration server! Error is {e}"
        print(output)


if __name__ == "__main__":
    main()
"""

_MISSING_FAILURE_PING_CONTENT = """\
from __future__ import annotations

SCRIPT_NAME = "Ping"


def main() -> None:
    output = "Successfully connected to the Mock Integration server with the provided connection parameters!"
    print(output)


if __name__ == "__main__":
    main()
"""


class TestPingMessageFormatValidation:
    """Test suite for the PingMessageFormatValidation runner."""

    validator_runner = PingMessageFormatValidation()

    def test_success_on_correct_messages_no_ci(self, temp_integration: pathlib.Path) -> None:
        """Test that a ping with correct success and failure messages passes (non-CI)."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_file.write_text(_GOOD_PING_CONTENT, encoding="utf-8")

        # No GITHUB_PR_SHA → always validates
        self.validator_runner.run(temp_integration)

    def test_success_on_correct_messages_ci_ping_changed(self, temp_integration: pathlib.Path) -> None:
        """Test that a correct ping passes when the ping file is changed in CI."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_file.write_text(_GOOD_PING_CONTENT, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[ping_file],
            ),
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_missing_success_message(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the ping file lacks the required success message."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_file.write_text(_MISSING_SUCCESS_PING_CONTENT, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[ping_file],
            ),
        ):
            with pytest.raises(NonFatalValidationError, match="Ping success message must contain"):
                self.validator_runner.run(temp_integration)

    def test_failure_on_missing_failure_message(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the ping file lacks the required failure message."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_file.write_text(_MISSING_FAILURE_PING_CONTENT, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[ping_file],
            ),
        ):
            with pytest.raises(NonFatalValidationError, match="Ping failure message must contain"):
                self.validator_runner.run(temp_integration)

    def test_failure_on_both_messages_missing(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the ping file is missing both required messages."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_file.write_text("def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n", encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[ping_file],
            ),
        ):
            with pytest.raises(NonFatalValidationError):
                self.validator_runner.run(temp_integration)

    def test_ci_ping_not_changed_skips_validation(self, temp_integration: pathlib.Path) -> None:
        """Test that validation is skipped when ping file is not changed in CI."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        # Write bad content that would fail if validated
        ping_file.write_text("def main():\n    pass\n", encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                # Return a changed file that is NOT Ping.py or ping.py
                return_value=[temp_integration / constants.ACTIONS_DIR / "some_other_action.py"],
            ),
        ):
            # Ping not in changed files → _is_ping_changed_in_pr returns False → skip
            self.validator_runner.run(temp_integration)

    def test_excluded_integration_skips_validation(self, temp_integration: pathlib.Path) -> None:
        """Test that an excluded integration is skipped regardless of ping content."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_file.write_text("def main():\n    pass\n", encoding="utf-8")

        with mock.patch(
            "mp.core.exclusions.get_excluded_names_without_ping_message_format",
            return_value={temp_integration.name},
        ):
            # Integration name is excluded — should not raise
            self.validator_runner.run(temp_integration)

    def test_no_actions_directory_skips_validation(self, temp_integration: pathlib.Path) -> None:
        """Test that a missing actions/ directory is handled gracefully."""
        import shutil

        actions_dir = temp_integration / constants.ACTIONS_DIR
        if actions_dir.exists():
            shutil.rmtree(actions_dir)

        # Should not raise
        self.validator_runner.run(temp_integration)

    def test_no_ping_file_skips_validation(self, temp_integration: pathlib.Path) -> None:
        """Test that a missing ping file is skipped gracefully."""
        ping_py = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_upper = temp_integration / constants.ACTIONS_DIR / "Ping.py"
        ping_py.unlink(missing_ok=True)
        ping_upper.unlink(missing_ok=True)

        # No ping file found — should not raise
        self.validator_runner.run(temp_integration)

    def test_failure_on_missing_success_message_no_ci(self, temp_integration: pathlib.Path) -> None:
        """Test that bad ping content fails in a local (non-CI) run too."""
        ping_file = temp_integration / constants.ACTIONS_DIR / "ping.py"
        ping_file.write_text(_MISSING_SUCCESS_PING_CONTENT, encoding="utf-8")

        # No GITHUB_PR_SHA → validator always runs (no CI gate)
        with pytest.raises(NonFatalValidationError, match="Ping success message must contain"):
            self.validator_runner.run(temp_integration)
