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

import pytest
from typer.testing import CliRunner

from mp.describe.typer_app import app

if TYPE_CHECKING:
    from collections.abc import Generator

runner = CliRunner()


@pytest.fixture
def mock_describe_action() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("mp.describe.action.typer_app.DescribeAction") as mock_class:
        mock_class.return_value.describe_actions = mock.AsyncMock()
        yield mock_class


@pytest.fixture
def mock_describe_connector() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("mp.describe.connector.typer_app.DescribeConnector") as mock_class:
        mock_class.return_value.describe = mock.AsyncMock()
        yield mock_class


@pytest.fixture
def mock_describe_job() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("mp.describe.job.typer_app.DescribeJob") as mock_class:
        mock_class.return_value.describe = mock.AsyncMock()
        yield mock_class


@pytest.fixture
def mock_describe_integration() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("mp.describe.integration.typer_app.DescribeIntegration") as mock_class:
        mock_class.return_value.describe = mock.AsyncMock()
        yield mock_class


@pytest.fixture
def mock_describe_all_integrations() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("mp.describe.integration.typer_app.describe_all_integrations") as mock_func:
        mock_func.return_value = mock.AsyncMock()
        yield mock_func


def test_describe_action_cli(mock_describe_action: mock.MagicMock) -> None:
    # mp describe action [ACTIONS]... -i INTEGRATION
    result = runner.invoke(app, ["action", "ping", "get_logs", "-i", "aws_ec2"])
    assert result.exit_code == 0
    mock_describe_action.assert_called_once()
    args, _ = mock_describe_action.call_args
    assert args[0] == "aws_ec2"
    assert args[1] == {"ping", "get_logs"}


def test_describe_connector_cli(mock_describe_connector: mock.MagicMock) -> None:
    # mp describe connector [CONNECTORS]... -i INTEGRATION
    result = runner.invoke(app, ["connector", "my_conn", "-i", "my_int"])
    assert result.exit_code == 0
    mock_describe_connector.assert_called_once()
    args, _ = mock_describe_connector.call_args
    assert args[0] == "my_int"
    assert args[1] == {"my_conn"}


def test_describe_job_cli(mock_describe_job: mock.MagicMock) -> None:
    # mp describe job [JOBS]... -i INTEGRATION
    result = runner.invoke(app, ["job", "my_job", "-i", "my_int"])
    assert result.exit_code == 0
    mock_describe_job.assert_called_once()
    args, _ = mock_describe_job.call_args
    assert args[0] == "my_int"
    assert args[1] == {"my_job"}


def test_describe_integration_cli(mock_describe_all_integrations: mock.MagicMock) -> None:
    # mp describe integration [INTEGRATIONS]...
    result = runner.invoke(app, ["integration", "int1", "int2"])
    assert result.exit_code == 0
    mock_describe_all_integrations.assert_called_once_with(
        src=None, dst=None, override=False, integrations=["int1", "int2"]
    )


def test_describe_integration_all_cli(mock_describe_all_integrations: mock.MagicMock) -> None:
    # mp describe integration --all
    result = runner.invoke(app, ["integration", "--all"])
    assert result.exit_code == 0
    mock_describe_all_integrations.assert_called_once_with(src=None, dst=None, override=False)


def test_all_content_cli() -> None:
    with mock.patch("mp.describe.typer_app.describe_all_content") as mock_all:
        result = runner.invoke(app, ["all-content", "my_int"])
        assert result.exit_code == 0
        mock_all.assert_called_once_with(src=None, dst=None, override=False, integrations=["my_int"])


def test_all_content_all_cli() -> None:
    with mock.patch("mp.describe.typer_app.describe_all_content") as mock_all:
        result = runner.invoke(app, ["all-content", "--all"])
        assert result.exit_code == 0
        mock_all.assert_called_once_with(src=None, dst=None, override=False)
