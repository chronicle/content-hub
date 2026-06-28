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

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from sysdig_secure.actions.Ping import (
    Ping,
    SUCCESS_MESSAGE,
)
import sysdig_secure.core.SysdigSecureConstants as Constants

from sysdig_secure.tests.common import CONFIG
from sysdig_secure.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


class TestPing:
    @set_metadata(
        integration_config=CONFIG
    )
    def test_success(
        self,
        sysdig_script_session: ApiSession,
        action_output: MockActionOutput,
    ) -> None:
        Ping(script_name=Constants.PING_SCRIPT_NAME).run()

        assert len(sysdig_script_session.request_history) >= 1
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )
