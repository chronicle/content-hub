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

import io
import json

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import (
    ActionJsonOutput,
    ActionOutput,
    ConnectorJsonOutput,
    ConnectorOutput,
)

from integration_testing.platform.script_output import (
    MockActionOutput,
    MockConnectorOutput,
)


class TestActionScriptOutput:
    def test_initialization(self) -> None:
        action_output: MockActionOutput = MockActionOutput()

        assert action_output is not None

    def test_get_out_io_returns_string_io(
        self,
        action_output: MockActionOutput,
    ) -> None:
        out_io: io.StringIO = action_output.get_out_io()

        assert isinstance(out_io, io.StringIO)

    def test_get_err_io_returns_string_io(
        self,
        action_output: MockActionOutput,
    ) -> None:
        err_io: io.StringIO = action_output.get_err_io()

        assert isinstance(err_io, io.StringIO)

    def test_no_results_return_none(self, action_output: MockActionOutput) -> None:
        assert action_output.report is None

    def test_flush_flushes_both_outputs(self, action_output: MockActionOutput) -> None:
        out_io: io.StringIO = action_output.get_out_io()
        err_io: io.StringIO = action_output.get_err_io()
        out_io.write("OUT!")
        err_io.write("ERR!")

        action_output.flush()

        assert not out_io.getvalue()
        assert not err_io.getvalue()

    def test_results_return_action_output_when_output_contains_action_output(
        self,
        action_output: MockActionOutput,
    ) -> None:
        out_io: io.StringIO = action_output.get_out_io()
        output: ActionOutput = ActionOutput(
            output_message="Success!",
            execution_state=ExecutionState.COMPLETED,
            result_value=True,
            json_output=ActionJsonOutput(json_result={"json": "result"}),
        )

        out_io.write(json.dumps(output.to_json()))
        results: ActionOutput = action_output.report

        assert results == output


class TestConnectorScriptOutput:
    def test_initialization(self) -> None:
        connector_output: MockConnectorOutput = MockConnectorOutput()

        assert connector_output is not None

    def test_get_out_io_returns_string_io(
        self,
        connector_output: MockConnectorOutput,
    ) -> None:
        out_io: io.StringIO = connector_output.get_out_io()

        assert isinstance(out_io, io.StringIO)

    def test_get_err_io_returns_string_io(
        self,
        connector_output: MockConnectorOutput,
    ) -> None:
        err_io: io.StringIO = connector_output.get_err_io()

        assert isinstance(err_io, io.StringIO)

    def test_no_results_return_none(
        self,
        connector_output: MockConnectorOutput,
    ) -> None:
        assert connector_output.report is None

    def test_flush_flushes_both_outputs(
        self,
        connector_output: MockConnectorOutput,
    ) -> None:
        out_io: io.StringIO = connector_output.get_out_io()
        err_io: io.StringIO = connector_output.get_err_io()
        out_io.write("OUT!")
        err_io.write("ERR!")

        connector_output.flush()

        assert not out_io.getvalue()
        assert not err_io.getvalue()

    def test_results_return_connector_output_when_output_contains_connector_output(
        self,
        connector_output: MockConnectorOutput,
    ) -> None:
        out_io: io.StringIO = connector_output.get_out_io()
        alert1: AlertInfo = AlertInfo()
        alert2: AlertInfo = AlertInfo()
        output: ConnectorOutput = ConnectorOutput(
            json_output=ConnectorJsonOutput(alerts=[alert1, alert2]),
        )

        out_io.write(json.dumps(output.to_json()))
        results: ConnectorOutput = connector_output.report

        assert isinstance(results, ConnectorOutput)
        assert results.json_output.to_json() == output.json_output.to_json()
