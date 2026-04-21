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

from paramiko.ssh_exception import SSHException
import pytest
from pytest_mock import MockerFixture

from credential_provider_manager import (
    CommandResult,
)
from cyber_ark_credential_provider.core.constants import TEST_COMMAND


class TestCredentialProviderManager:
    """Test class for CredentialProviderManager."""

    def test_create_ssh_client_with_private_key(
        self,
        manager,
        ssh_components_mock,
    ):
        """Test SSH client creation with private key authentication."""
        mock_ssh_client, mock_client_instance, mock_key = ssh_components_mock

        manager.create_ssh_client_connection()

        mock_ssh_client.assert_called_once()
        mock_client_instance.connect.assert_called_once_with(
            manager.docker_gateway_ip,
            username=manager.username,
            pkey=mock_key,
        )

    def test_create_ssh_client_with_password(
        self,
        manager,
        ssh_components_mock,
    ):
        """Test SSH client creation with password authentication."""
        mock_ssh_client, mock_client_instance, _ = ssh_components_mock

        manager.ssh_private_key_path = None
        manager.create_ssh_client_connection()

        mock_ssh_client.assert_called_once()
        mock_client_instance.connect.assert_called_once_with(
            manager.docker_gateway_ip,
            username=manager.username,
            password=manager.password,
        )

    def test_execute_command_success(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test successful command execution."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        command = "test command"
        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = b"command output"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.execute_command_on_server(command)

        assert isinstance(result, CommandResult)
        assert result.output == "command output"
        assert result.error == ""
        assert result.exit_code == 0
        mock_client_instance.exec_command.assert_called_once_with(command)

    def test_execute_command_failure(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test command execution with errors."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        command = "invalid command"
        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"command not found"
        mock_stdout.channel.recv_exit_status.return_value = 1

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.execute_command_on_server(command)

        assert isinstance(result, CommandResult)
        assert result.output == ""
        assert result.error == "command not found"
        assert result.exit_code == 1
        mock_client_instance.exec_command.assert_called_once_with(command)

    def test_execute_command_ssh_error(
        self,
        manager,
        ssh_components_mock,
    ):
        """Test command execution with SSH connection error."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        command = "test command"
        mock_client_instance.exec_command.side_effect = SSHException("Connection lost")

        with pytest.raises(SSHException) as exc_info:
            manager.execute_command_on_server(command)

        assert "Connection lost" in str(exc_info.value)

    def test_test_connectivity_success(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test successful connectivity check with CyberArk server."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock

        expected_output = "SDK Version: 1.2.3"
        expected_error = ""
        expected_exit_code = 0

        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = expected_output.encode("utf-8")
        mock_stderr.read.return_value = expected_error.encode("utf-8")
        mock_stdout.channel.recv_exit_status.return_value = expected_exit_code

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.test_connectivity()

        assert isinstance(result, CommandResult)
        assert result.output == expected_output
        assert result.error == expected_error
        assert result.exit_code == expected_exit_code

        expected_command = f"{manager.sdk_path} {TEST_COMMAND}"
        mock_client_instance.exec_command.assert_called_once_with(expected_command)
        mock_client_instance.close.assert_called_once()

    def test_test_connectivity_failure(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test failed connectivity check with CyberArk server."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        expected_output = ""
        expected_error = "SDK not found"
        expected_exit_code = 1

        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = expected_output.encode("utf-8")
        mock_stderr.read.return_value = expected_error.encode("utf-8")
        mock_stdout.channel.recv_exit_status.return_value = expected_exit_code

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.test_connectivity()

        assert isinstance(result, CommandResult)
        assert result.output == expected_output
        assert result.error == expected_error
        assert result.exit_code == expected_exit_code

        expected_command = f"{manager.sdk_path} {TEST_COMMAND}"
        mock_client_instance.exec_command.assert_called_once_with(expected_command)
        mock_client_instance.close.assert_called_once()

    def test_test_connectivity_connection_error(
        self,
        manager,
        ssh_components_mock,
    ):
        """Test connectivity check with SSH connection error."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        mock_client_instance.exec_command.side_effect = SSHException(
            "Connection failed"
        )

        with pytest.raises(SSHException) as exc_info:
            manager.test_connectivity()

        assert "Connection failed" in str(exc_info.value)
        mock_client_instance.close.assert_not_called()

    def test_get_application_password_success(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test successful password retrieval with basic parameters."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        app_id = "test_app"
        safe_name = "test_safe"
        object_name = "test_object"
        expected_output = "secret_password"
        expected_error = ""
        expected_exit_code = 0

        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = expected_output.encode("utf-8")
        mock_stderr.read.return_value = expected_error.encode("utf-8")
        mock_stdout.channel.recv_exit_status.return_value = expected_exit_code

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.get_application_password(
            application_id=app_id,
            safe_name=safe_name,
            object_name=object_name,
        )

        assert isinstance(result, CommandResult)
        assert result.output == expected_output
        assert result.error == expected_error
        assert result.exit_code == expected_exit_code

        expected_command = (
            f"{manager.sdk_path} GetPassword "
            f"-p AppDescs.AppID={app_id} "
            f'-p Query="Safe={safe_name};Object={object_name}" '
            f"-o Password"
        )
        mock_client_instance.exec_command.assert_called_once_with(expected_command)
        mock_client_instance.close.assert_called_once()

    def test_get_application_password_with_folder(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test password retrieval with folder parameter."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        app_id = "test_app"
        safe_name = "test_safe"
        folder_name = "test_folder"
        object_name = "test_object"
        expected_output = "secret_password"

        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = expected_output.encode("utf-8")
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        manager.get_application_password(
            application_id=app_id,
            safe_name=safe_name,
            folder_name=folder_name,
            object_name=object_name,
        )

        expected_command = (
            f"{manager.sdk_path} GetPassword "
            f"-p AppDescs.AppID={app_id} "
            f'-p Query="Safe={safe_name};'
            f"Folder={folder_name};"
            f'Object={object_name}" '
            f"-o Password"
        )
        mock_client_instance.exec_command.assert_called_once_with(expected_command)

    def test_get_application_password_failure(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test password retrieval with error response."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        app_id = "invalid_app"
        safe_name = "test_safe"
        object_name = "test_object"
        expected_error = "APPAP012E Password object was not found"

        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = expected_error.encode("utf-8")
        mock_stdout.channel.recv_exit_status.return_value = 1

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.get_application_password(
            application_id=app_id,
            safe_name=safe_name,
            object_name=object_name,
        )

        assert result.error == expected_error
        assert result.exit_code == 1
        mock_client_instance.close.assert_called_once()

    def test_execute_custom_sdk_command_success(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test successful execution of a custom SDK command."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        custom_command = "GetVersion"
        expected_output = "CLI Password SDK v1.2.3"

        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = expected_output.encode("utf-8")
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.execute_custom_sdk_command(custom_command)

        assert isinstance(result, CommandResult)
        assert result.output == expected_output
        assert result.error == ""
        assert result.exit_code == 0

        expected_full_command = f"{manager.sdk_path} {custom_command}"
        mock_client_instance.exec_command.assert_called_once_with(expected_full_command)
        mock_client_instance.close.assert_called_once()

    def test_execute_custom_sdk_command_failure(
        self,
        manager,
        ssh_components_mock,
        mocker: MockerFixture,
    ):
        """Test custom SDK command with error response."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        custom_command = "InvalidCommand"
        expected_error = "APPAP001E CLI Password SDK failed to execute"

        mock_stdin = mocker.MagicMock()
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = expected_error.encode("utf-8")
        mock_stdout.channel.recv_exit_status.return_value = 1

        mock_client_instance.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        result = manager.execute_custom_sdk_command(custom_command)

        assert result.error == expected_error
        assert result.exit_code == 1
        expected_full_command = f"{manager.sdk_path} {custom_command}"
        mock_client_instance.exec_command.assert_called_once_with(expected_full_command)
        mock_client_instance.close.assert_called_once()

    def test_execute_custom_sdk_command_ssh_error(
        self,
        manager,
        ssh_components_mock,
    ):
        """Test custom SDK command with SSH connection error."""
        _mock_ssh_client, mock_client_instance, _ = ssh_components_mock
        custom_command = "GetVersion"
        mock_client_instance.exec_command.side_effect = SSHException("Connection lost")

        with pytest.raises(SSHException) as exc_info:
            manager.execute_custom_sdk_command(custom_command)

        assert "Connection lost" in str(exc_info.value)
        expected_full_command = f"{manager.sdk_path} {custom_command}"
        mock_client_instance.exec_command.assert_called_once_with(expected_full_command)
        mock_client_instance.close.assert_not_called()
