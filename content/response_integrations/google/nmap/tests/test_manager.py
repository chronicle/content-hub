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

import pathlib
import subprocess
import pytest

from nmap.core.NmapManager import NmapManager, NmapScanResult
from nmap.core import constants
from nmap.core.NmapParser import NmapParser


def test_connectivity_success(manager, mocker):
    """Test that test_connectivity successfully calls subprocess.run and returns
    the expected CompletedProcess object.
    """
    mock_subprocess_run = mocker.patch(
        "nmap.core.NmapManager.subprocess.run"
    )

    mock_completed_process = subprocess.CompletedProcess(
        args=constants.TEST_COMMAND,
        returncode=0,
        stdout="Nmap version 7.92 ( https://nmap.org )",
        stderr="",
    )
    mock_subprocess_run.return_value = mock_completed_process

    result = manager.test_connectivity()

    mock_subprocess_run.assert_called_once_with(
        constants.TEST_COMMAND, text=True, capture_output=True, check=False
    )
    assert result == mock_completed_process
    assert result.stdout == "Nmap version 7.92 ( https://nmap.org )"


def test_run_nmap_scan_success(manager, mocker):
    """Test that run_nmap_scan successfully executes an Nmap scan.

    This test verifies that subprocess.run is called with the correct command,
    NmapParser is instantiated with the XML output, and an NmapScanResult
    object containing the command result and parsed data is returned.
    """
    mock_subprocess_run = mocker.patch(
        "nmap.core.NmapManager.subprocess.run"
    )
    mock_nmap_parser_class = mocker.patch(
        "nmap.core.NmapManager.NmapParser"
    )

    target = "192.168.1.1"
    options = "-sV -p 80,443"
    expected_command = ["nmap", "-sV", "-p", "80,443", "-oX", "-", target]
    mock_xml_output = "<nmaprun><host></host></nmaprun>"

    mock_completed_process = subprocess.CompletedProcess(
        args=expected_command,
        returncode=constants.SUCCESS_RETURN_CODE,
        stdout=mock_xml_output,
        stderr="",
    )
    mock_subprocess_run.return_value = mock_completed_process

    mock_parser_instance = mocker.MagicMock(spec=NmapParser)
    mock_nmap_parser_class.return_value = mock_parser_instance

    scan_result = manager.run_nmap_scan(target=target, options=options)

    mock_subprocess_run.assert_called_once_with(
        expected_command, text=True, capture_output=True, check=False
    )
    mock_nmap_parser_class.assert_called_once_with(xml_string=mock_xml_output.strip())
    assert isinstance(scan_result, NmapScanResult)
    assert scan_result.command_result == mock_completed_process
    assert scan_result.parsed_result == mock_parser_instance


def test_run_nmap_scan_failure_non_zero_return(manager, mocker):
    """Test that run_nmap_scan raises an NmapScanError when the Nmap command returns
    a non-zero exit code.

    This test ensures that if the subprocess.run call indicates a failure
    (non-zero return code), an NmapScanError is raised with the stderr output,
    and the NmapParser is not called.
    """
    mock_subprocess_run = mocker.patch(
        "nmap.core.NmapManager.subprocess.run"
    )
    mock_nmap_parser_class = mocker.patch(
        "nmap.core.NmapManager.NmapParser"
    )

    target = "invalid_target"
    options = "-T4"
    expected_command = ["nmap", "-T4", "-oX", "-", target]
    error_output = "Failed to resolve 'invalid_target'"

    mock_completed_process = subprocess.CompletedProcess(
        args=expected_command,
        returncode=1,
        stdout="",
        stderr=error_output,
    )
    mock_subprocess_run.return_value = mock_completed_process

    with pytest.raises(Exception, match=error_output.strip()):
        manager.run_nmap_scan(target=target, options=options)

    mock_subprocess_run.assert_called_once_with(
        expected_command, text=True, capture_output=True, check=False
    )
    mock_nmap_parser_class.assert_not_called()


def test_nmap_manager_init_raises_error_if_not_remote(mocker):
    """Test that the NmapManager constructor raises an NmapManagerError
    if the provided soar_action.is_remote is False.

    This ensures that the NmapManager can only be initialized when configured
    to run on a remote agent.
    """
    mock_soar_action_local = mocker.MagicMock()
    mock_soar_action_local.is_remote = False
    expected_message = "Nmap integration should be configured on remote agent only."

    with pytest.raises(Exception, match=expected_message):
        NmapManager(soar_action=mock_soar_action_local)
