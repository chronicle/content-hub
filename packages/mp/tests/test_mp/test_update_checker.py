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

from unittest.mock import MagicMock, patch

from requests import RequestException

from mp.core.update_checker import PYPROJECT_URL, check_for_updates_background


@patch("filters.requests.get")
@patch("filters.typer.secho")
def test_check_for_updates_newer_version(mock_secho: MagicMock, mock_get: MagicMock) -> None:
    """Test that a warning is printed when a newer version is available."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.text = '[project]\nversion = "2.0.0"\n'
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    # Call function
    check_for_updates_background("1.0.0")

    # Assertions
    mock_get.assert_called_once_with(PYPROJECT_URL, timeout=2.0)
    mock_secho.assert_called_once()
    assert (
        "WARNING: You are using mp version 1.0.0; however, version 2.0.0 is available."
        in mock_secho.call_args[0][0]
    )


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.typer.secho")
def test_check_for_updates_same_version(mock_secho: MagicMock, mock_get: MagicMock) -> None:
    """Test that NO warning is printed when versions are the same."""
    mock_response = MagicMock()
    mock_response.text = '[project]\nversion = "1.0.0"\n'
    mock_get.return_value = mock_response

    check_for_updates_background("1.0.0")

    mock_secho.assert_not_called()


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.typer.secho")
def test_check_for_updates_older_remote(mock_secho: MagicMock, mock_get: MagicMock) -> None:
    """Test that NO warning is printed when a remote version is older."""
    mock_response = MagicMock()
    mock_response.text = '[project]\nversion = "0.9.0"\n'
    mock_get.return_value = mock_response

    check_for_updates_background("1.0.0")

    mock_secho.assert_not_called()


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.typer.secho")
def test_check_for_updates_network_error(mock_secho: MagicMock, mock_get: MagicMock) -> None:
    """Test that the function fails silently on network error."""
    mock_get.side_effect = RequestException("Connection lost")

    check_for_updates_background("1.0.0")

    mock_secho.assert_not_called()


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.typer.secho")
def test_check_for_updates_invalid_toml(mock_secho: MagicMock, mock_get: MagicMock) -> None:
    """Test that the function fails silently on invalid TOML."""
    mock_response = MagicMock()
    mock_response.text = "INVALID TOML"
    mock_get.return_value = mock_response

    check_for_updates_background("1.0.0")

    mock_secho.assert_not_called()
