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

from mp.core.update_checker import PYPROJECT_URL, TIMEOUT_SECONDS, UpdateChecker


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.rich.print")
def test_check_for_updates_newer_version(mock_rich_print: MagicMock, mock_get: MagicMock) -> None:
    """Test that a warning is printed when a newer version is available."""
    # 1. Instantiate the class directly (no singletons needed)
    checker = UpdateChecker()

    # 2. Setup mock response
    mock_response = MagicMock()
    mock_response.text = '[project]\nversion = "2.0.0"\n'
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    # 3. Call start_background_check
    checker.start_background_check("1.0.0")

    # 4. Wait for completion (calls join internally)
    checker.print_warning_if_needed()

    # 5. Assertions
    # Note: Use TIMEOUT_SECONDS constant to match the implementation
    mock_get.assert_called_once_with(PYPROJECT_URL, timeout=TIMEOUT_SECONDS)

    mock_rich_print.assert_called_once()
    # Check that the print contained the correct version
    printed_message = mock_rich_print.call_args[0][0]
    assert "2.0.0" in printed_message
    assert "WARNING" in printed_message


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.rich.print")
def test_check_for_updates_same_version(mock_rich_print: MagicMock, mock_get: MagicMock) -> None:
    """Test that NO warning is printed when versions are the same."""
    checker = UpdateChecker()

    mock_response = MagicMock()
    mock_response.text = '[project]\nversion = "1.0.0"\n'
    mock_get.return_value = mock_response

    checker.start_background_check("1.0.0")
    checker.print_warning_if_needed()

    mock_rich_print.assert_not_called()


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.rich.print")
def test_check_for_updates_older_remote(mock_rich_print: MagicMock, mock_get: MagicMock) -> None:
    """Test that NO warning is printed when a remote version is older."""
    checker = UpdateChecker()

    mock_response = MagicMock()
    mock_response.text = '[project]\nversion = "0.9.0"\n'
    mock_get.return_value = mock_response

    checker.start_background_check("1.0.0")
    checker.print_warning_if_needed()

    mock_rich_print.assert_not_called()


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.rich.print")
def test_check_for_updates_network_error(mock_rich_print: MagicMock, mock_get: MagicMock) -> None:
    """Test that the function fails silently on network error."""
    checker = UpdateChecker()

    mock_get.side_effect = RequestException("Connection lost")

    checker.start_background_check("1.0.0")
    checker.print_warning_if_needed()

    mock_rich_print.assert_not_called()


@patch("mp.core.update_checker.requests.get")
@patch("mp.core.update_checker.rich.print")
def test_check_for_updates_invalid_toml(mock_rich_print: MagicMock, mock_get: MagicMock) -> None:
    """Test that the function fails silently on invalid TOML."""
    checker = UpdateChecker()

    mock_response = MagicMock()
    mock_response.text = "INVALID TOML"
    mock_get.return_value = mock_response

    checker.start_background_check("1.0.0")
    checker.print_warning_if_needed()

    mock_rich_print.assert_not_called()
