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

import pytest

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from ..actions import Ping
from ..core.ScreenshotMachineManager import (
    SCREENSHOT_MACHINE_URL,
)
from ..tests.common import CONFIG_FILE
from ..tests.core.session import (
    MOCK_ERROR_MSG,
    ScreenshotMachineSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.request import MockRequest
from integration_testing.set_meta import set_metadata


PING_SUCCESS_OUTPUT = ActionOutput(
    output_message="Connected successfully.",
    result_value="true",
    execution_state=ExecutionState.COMPLETED,
    json_output=None,
)


@set_metadata(integration_config_file_path=CONFIG_FILE)
def test_ping_success(
    script_session: ScreenshotMachineSession,
    action_output: MockActionOutput,
) -> None:
    Ping.main()

    assert action_output.results == PING_SUCCESS_OUTPUT
    assert_ping_request(script_session)


@set_metadata(integration_config={"API Key": "raise_error", "Use SSL": "raise_error"})
def test_ping_404_failure(
    script_session: ScreenshotMachineSession,
    action_output: MockActionOutput,
) -> None:
    with pytest.raises(Exception) as e:
        Ping.main()

        assert MOCK_ERROR_MSG in e.value
        assert action_output.results is None
        assert_ping_request(script_session)


def assert_ping_request(script_session: ScreenshotMachineSession) -> None:
    assert len(script_session.request_history) == 1
    req: MockRequest = script_session.request_history[0].request
    sent_request: str = f"{req.url.scheme}://{req.url.netloc}{req.url.path}"
    assert sent_request == SCREENSHOT_MACHINE_URL
