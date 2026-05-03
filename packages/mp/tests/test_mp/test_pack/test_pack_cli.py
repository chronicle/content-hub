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

from typing import TYPE_CHECKING
from unittest import mock

from typer.testing import CliRunner

from mp.pack.typer_app import pack_app

if TYPE_CHECKING:
    import pathlib

runner = CliRunner()


def test_pack_integration_cli() -> None:
    with mock.patch("mp.pack.sub_commands.integration.pack.flow_pack_integration") as mock_flow:
        result = runner.invoke(pack_app, ["integration", "cyber_x"])
        assert result.exit_code == 0
        mock_flow.assert_called_once_with(
            integration_name="cyber_x",
            version=None,
            beta_name=None,
            zip_dst=None,
            interactive=True,
        )


def test_pack_integration_options_cli(tmp_path: pathlib.Path) -> None:
    with mock.patch("mp.pack.sub_commands.integration.pack.flow_pack_integration") as mock_flow:
        result = runner.invoke(
            pack_app,
            [
                "integration",
                "cyber_x",
                "--version",
                "5.0",
                "--beta",
                "CyberXBeta",
                "--dst",
                str(tmp_path),
                "--non-interactive",
            ],
        )
        assert result.exit_code == 0
        mock_flow.assert_called_once_with(
            integration_name="cyber_x",
            version="5.0",
            beta_name="CyberXBeta",
            zip_dst=tmp_path,
            interactive=False,
        )
