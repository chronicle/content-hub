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

import base64
import binascii
from collections import namedtuple
from pathlib import Path
from . import constants
from .datamodels import IntegrationParameters
from . import exceptions

import paramiko
from paramiko.ssh_exception import NoValidConnectionsError, SSHException


CommandResult = namedtuple("CommandResult", ["output", "error", "exit_code"])


class CredentialProviderManager:
    """Manages interactions with CyberArk Credential Provider via SSH."""

    def __init__(
        self,
        integration_parameters: IntegrationParameters,
    ) -> None:
        self.sdk_path: Path = integration_parameters.sdk_path
        self.username: str = integration_parameters.username
        self.docker_gateway_ip: str = integration_parameters.docker_gateway_ip
        self.rsa_public_key_data: str = integration_parameters.rsa_public_key_data
        self.ssh_private_key_path: Path | None = (
            integration_parameters.ssh_private_key_path
        )
        self.password: str = integration_parameters.password

    def create_ssh_client_connection(self) -> paramiko.SSHClient:
        """Set up the ssh connection with the target server.

        Returns:
            paramiko.SSHClient: An SSH client connected to the server.

        Raises:
            CyberArkCredentialProviderNoValidConnectionsError: When no policy is set
            or general SSH connection error.
        """
        if not self.ssh_private_key_path and not self.password:
            raise exceptions.CyberArkCredentialProviderNoValidConnectionsError(
                "No valid authentication method provided. "
                "Please provide either an SSH private key or a password."
            )

        try:
            decoded_key = base64.b64decode(self.rsa_public_key_data)

        except binascii.Error as err:
            raise exceptions.CyberArkCredentialProviderValidationError(
                "Invalid RSA Public Key: not a valid base64 string."
            ) from err

        try:
            ssh_client: paramiko.SSHClient = paramiko.SSHClient()
            trusted_key = paramiko.RSAKey(data=decoded_key)
            ssh_client.get_host_keys().add(
                hostname=self.docker_gateway_ip,
                keytype=trusted_key.get_name(),
                key=trusted_key,
            )

            if self.ssh_private_key_path:
                private_key = paramiko.RSAKey(filename=self.ssh_private_key_path)
                ssh_client.connect(
                    self.docker_gateway_ip,
                    username=self.username,
                    pkey=private_key,
                )
                return ssh_client

            ssh_client.connect(
                self.docker_gateway_ip,
                username=self.username,
                password=self.password,
            )
            return ssh_client

        except (
            NoValidConnectionsError,
            paramiko.BadHostKeyException,
            SSHException,
        ) as err:
            raise exceptions.CyberArkCredentialProviderNoValidConnectionsError(
                f"Unable to connect - {err}"
            ) from err

    def execute_command_on_server(self, command: str) -> CommandResult:
        """Executes a command on the SSH Server.

        Args:
            command(str): The command to execute on the server.

        Returns:
            CommandResult: A namedtuple with the following fields:
            output, error, exit_code.
        """
        ssh_client: paramiko.SSHClient = self.create_ssh_client_connection()
        _, stdout, stderr = ssh_client.exec_command(command)
        output: str = stdout.read().decode("utf-8")
        error: str = stderr.read().decode("utf-8")
        exit_code: int = stdout.channel.recv_exit_status()
        ssh_client.close()

        return CommandResult(output=output, error=error, exit_code=exit_code)

    def test_connectivity(self) -> CommandResult:
        test_command: str = f"{self.sdk_path} {constants.TEST_COMMAND}"
        result: CommandResult = self.execute_command_on_server(command=test_command)

        return result

    def get_application_password(
        self,
        application_id: str = None,
        safe_name: str = None,
        folder_name: str = None,
        object_name: str = None,
        output_field: str = constants.PASSWORD_OUTPUT_FIELD,
    ) -> CommandResult:
        """Retrieves the password for a specified application id from
        CyberArk Credential Provider.

        Args:
            application_id(str): The ID of the application.
            safe_name(str): The safe name of the vault.
            folder_name(str): The folder name of the vault.
            object_name(str): The object name of the vault.
            output_field(str): The output field. Defaults to "Password".

        Returns:
            CommandResult: A namedtuple with the following fields:
            output, error, exit_code.
        """
        query_parts: list[str] = [f"Safe={safe_name}", f"Object={object_name}"]

        if folder_name:
            query_parts.insert(1, f"Folder={folder_name}")

        query: str = ";".join(query_parts)

        command: str = (
            f"{self.sdk_path} GetPassword "
            f"-p AppDescs.AppID={application_id} "
            f'-p Query="{query}" '
            f"-o {output_field}"
        )

        return self.execute_command_on_server(command=command)

    def execute_custom_sdk_command(self, command: str) -> CommandResult:
        command: str = f"{self.sdk_path} {command}"

        return self.execute_command_on_server(command=command)
