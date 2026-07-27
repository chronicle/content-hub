# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is-distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

from typer.testing import CliRunner

from mp.build_project.flow.integrations.flow import BuildIntegrationsParams
from mp.build_project.typer_app import build_app

if TYPE_CHECKING:
    import pathlib

runner = CliRunner()


def test_build_integration_with_src_cli(tmp_path: pathlib.Path) -> None:
    with mock.patch("mp.build_project.sub_commands.integration.build.build_integrations") as mock_flow:
        src_path = tmp_path / "custom_integrations"
        src_path.mkdir()
        result = runner.invoke(
            build_app,
            [
                "integration",
                "cyber_x",
                "--src",
                str(src_path),
            ],
        )
        assert result.exit_code == 0
        mock_flow.assert_called_once_with(
            BuildIntegrationsParams(
                integrations=["cyber_x"],
                repositories=[],
                src=src_path,
                dst=None,
                deconstruct=False,
                custom_integration=False,
            )
        )
