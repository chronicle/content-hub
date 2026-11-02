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
import shlex
from . import constants
from .datamodels import ConfigurationParameters
from . import exceptions

import paramiko
from paramiko.ssh_exception import NoValidConnectionsError, SSHException


CommandResult = namedtuple("CommandResult", ["output", "error", "exit_code"])


class CredentialProviderManager:
    """Manages interactions with CyberArk Credential Provider via SSH."""

    def __init__(
        self,
        configuration_parameters: ConfigurationParameters,
    ) -> None:
        self.sdk_path: Path = configuration_parameters.sdk_path
        self.username: str = configuration_parameters.username
        self.docker_gateway_ip: str = configuration_parameters.docker_gateway_ip
        self.host_public_key_data: str = configuration_parameters.host_public_key_data
        self.ssh_private_key_path: Path | None = (
            configuration_parameters.ssh_private_key_path
        )
        self.password: str = configuration_parameters.password

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
            decoded_key = base64.b64decode(self.host_public_key_data)
        except binascii.Error as err:
            raise exceptions.CyberArkCredentialProviderValidationError(
                "Invalid Host Public Key: not a valid base64 string."
            ) from err

        ssh_client: paramiko.SSHClient = paramiko.SSHClient()
        try:
            msg = paramiko.Message(decoded_key)
            key_type = msg.get_text()
            key_class = constants.KEY_CLASSES.get(key_type)
            if key_class is None:
                raise exceptions.CyberArkCredentialProviderValidationError(
                    f"Unsupported host public key type: {key_type}"
                )
            trusted_key = key_class(data=decoded_key)
        except exceptions.CyberArkCredentialProviderValidationError:
            raise
        except Exception as err:
            raise exceptions.CyberArkCredentialProviderValidationError(
                "Invalid Host Public Key format: failed to parse host public key data."
            ) from err

        try:
            ssh_client.get_host_keys().add(
                hostname=self.docker_gateway_ip,
                keytype=trusted_key.get_name(),
                key=trusted_key,
            )

            if self.ssh_private_key_path:
                ssh_client.connect(
                    self.docker_gateway_ip,
                    username=self.username,
                    key_filename=str(self.ssh_private_key_path),
                    timeout=30.0,
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
        query_parts: list[str] = [
            f"Safe={safe_name}",
            f"Object={object_name}",
        ]

        if folder_name:
            query_parts.insert(1, f"Folder={folder_name}")

        query: str = ";".join(query_parts)

        command: str = (
            f"{shlex.quote(str(self.sdk_path))} GetPassword "
            f"-p AppDescs.AppID={shlex.quote(application_id)} "
            f"-p Query={shlex.quote(query)} "
            f"-o {shlex.quote(output_field)}"
        )

        return self.execute_command_on_server(command=command)

    def get_password_from_location(
        self,
        secret_location: str,
        output_field: str = constants.PASSWORD_OUTPUT_FIELD,
    ) -> CommandResult:
        """Retrieves a password from CyberArk based on a location string.

        Args:
            secret_location (str): A string in the format
            "AppDescs.AppID=<...>;Safe=<...>;Object=<...>[;Folder=<...>]"
            output_field (str): The output field. Defaults to "Password".

        Returns:
            CommandResult: A namedtuple with the following fields:
            output, error, exit_code.

        Raises:
            CyberArkCredentialProviderValidationError: if the location string is
            invalid or missing required parts.
        """
        try:
            location_parts: dict[str, str] = dict(
                item.split("=", 1) for item in secret_location.split(";") if item
            )
        except ValueError as e:
            raise exceptions.CyberArkCredentialProviderValidationError(
                f"Invalid secret location format: {secret_location}. "
                "Expected 'key=value' pairs separated by ';'."
            ) from e

        app_id: str | None = location_parts.get("AppDescs.AppID")
        safe: str | None = location_parts.get("Safe")
        object_name: str | None = location_parts.get("Object")
        folder_name: str | None = location_parts.get("Folder")

        if not all([app_id, safe, object_name]):
            raise exceptions.CyberArkCredentialProviderValidationError(
                f"Invalid secret location: {secret_location}. "
                "It must contain 'AppDescs.AppID', 'Safe', and 'Object'."
            )

        query_parts: list[str] = [
            f"Safe={safe}",
            f"Object={object_name}",
        ]

        if folder_name:
            query_parts.append(f"Folder={folder_name}")

        query: str = ";".join(query_parts)

        command: str = (
            f"GetPassword -p AppDescs.AppID={shlex.quote(app_id)} "
            f"-p Query={shlex.quote(query)} -o {shlex.quote(output_field)}"
        )

        return self.execute_custom_sdk_command(command=command)

    def execute_custom_sdk_command(self, command: str) -> CommandResult:
        command: str = f"{shlex.quote(str(self.sdk_path))} {command}"

        return self.execute_command_on_server(command=command)
