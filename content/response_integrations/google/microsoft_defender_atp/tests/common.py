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

import pathlib
import re
from typing import TYPE_CHECKING

from integration_testing.common import get_def_file_content

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NoReturn

    import pytest
    from TIPCommon.types import SingleJson

INTEGRATION_PATH = pathlib.Path(__file__).parent.parent

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG = get_def_file_content(CONFIG_PATH)

MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

MACHINE_DATA: SingleJson = MOCK_DATA["machine_data"]

SUMMARY_LINE_PATTERN: re.Pattern[str] = re.compile(
    r"ACTION_RESULT_SUMMARY v=1 outcome=(SUCCESS|PARTIAL_SUCCESS|FAILURE) error_type=[A-Z_]+ "
    r"execution_state=(COMPLETED|FAILED|TIMEDOUT|IN_PROGRESS) targets=\d+ failed=\d+ skipped=\d+ "
    r"exc_type=\w+ http_status=(\d+|NONE)",
)


def get_summary_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Return the ACTION_RESULT_SUMMARY lines an action logged and check their format and level."""
    records = [record for record in caplog.records if record.getMessage().startswith("ACTION_RESULT_SUMMARY")]
    lines = [record.getMessage().strip() for record in records]
    assert all(SUMMARY_LINE_PATTERN.fullmatch(line) for line in lines)
    assert all(record.levelname == "INFO" for record in records)
    return lines


def expected_summary(
    outcome: str,
    error_type: str,
    execution_state: str,
    targets: int,
    failed: int,
    skipped: int = 0,
    exc_type: str = "NONE",
    http_status: str = "NONE",
) -> str:
    """Build the expected ACTION_RESULT_SUMMARY line for an assertion."""
    return (
        f"ACTION_RESULT_SUMMARY v=1 outcome={outcome} error_type={error_type} execution_state={execution_state} "
        f"targets={targets} failed={failed} skipped={skipped} exc_type={exc_type} http_status={http_status}"
    )


def raise_error(error: BaseException) -> Callable[..., NoReturn]:
    """Return a stub callable that always raises the given exception."""

    def _raiser(*_: object, **__: object) -> NoReturn:
        raise error

    return _raiser


def logged_levels(caplog: pytest.LogCaptureFixture, message: str) -> list[str]:
    """Return the levels of log records whose message matches message."""
    return [record.levelname for record in caplog.records if record.getMessage().strip() == message]
