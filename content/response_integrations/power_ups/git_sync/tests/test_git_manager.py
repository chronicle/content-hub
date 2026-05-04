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

from unittest.mock import Mock, patch, sentinel

from ..core import GitManager


def test_run_command_logs_successful_connection_at_info_level() -> None:
    """Successful SSH connections should emit an info log, not an error log."""
    logger = Mock()
    client = Mock()
    channel = Mock()
    transport = Mock()
    transport.open_session.return_value = channel
    client.get_transport.return_value = transport

    vendor = GitManager.SiemplifyParamikoSSHVendor(
        siemplify_logger=logger,
        git_server_fingerprint="SHA256:test-fingerprint",
    )

    with (
        patch.object(GitManager.paramiko, "SSHClient", return_value=client),
        patch.object(GitManager, "_ParamikoWrapper", return_value=sentinel.wrapper),
    ):
        result = vendor.run_command(
            host="example.com",
            command="git-upload-pack '/repo.git'",
            protocol_version=2,
        )

    assert result is sentinel.wrapper
    client.connect.assert_called_once_with(hostname="example.com")
    channel.set_environment_variable.assert_called_once_with(
        name="GIT_PROTOCOL",
        value="version=2",
    )
    channel.exec_command.assert_called_once_with("git-upload-pack '/repo.git'")
    logger.info.assert_any_call("Successfully connected to example.com")
    logger.error.assert_not_called()