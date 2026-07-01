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
from dataclasses import dataclass
import shlex
import subprocess

from TIPCommon.types import ChronicleSOAR
from ..core import constants
from ..core import exceptions
from ..core.NmapParser import NmapParser


@dataclass(slots=True)
class NmapScanResult:
    command_result: subprocess.CompletedProcess
    parsed_result: NmapParser


class NmapManager:
    """Manages Nmap scan operations.

    This class provides methods to test connectivity to an Nmap installation
    and to run Nmap scans against specified targets with given options.
    It ensures that Nmap operations are only performed when the integration
    is configured to run on a remote agent.
    """
    def __init__(self, soar_action: ChronicleSOAR) -> None:
        if not soar_action.is_remote:
            raise exceptions.NmapManagerError(
                "Nmap integration should be configured on remote agent only."
            )

    def test_connectivity(self) -> subprocess.CompletedProcess:
        """Tests the connectivity to the Nmap instance by running a version check.

        Returns:
            result (subprocess.CompletedProcess): The result of the Nmap command
            execution. It contains information about the command's return code,
            standard output, and standard error.
        """
        result: subprocess.CompletedProcess = subprocess.run(
            constants.TEST_COMMAND,
            text=True,
            capture_output=True,
            check=False,
        )

        return result

    def run_nmap_scan(
        self,
        target: str,
        options: str,
    ) -> NmapScanResult:
        """Runs an Nmap scan on a specified target with given options.

        Args:
            target (str): The target IP address or hostname to scan.
            options (str): The Nmap options to use for the scan (e.g., "-sV -p 1-1000").

        Returns:
            NmapScanResult: The result of the Nmap scan.
        """
        command: list[str] = ["nmap"] + shlex.split(options) + ["-oX", "-"] + [target]
        result: subprocess.CompletedProcess = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != constants.SUCCESS_RETURN_CODE:
            raise exceptions.NmapScanError(result.stderr.strip())

        parser = NmapParser(xml_string=result.stdout.strip())

        return NmapScanResult(command_result=result, parsed_result=parser)
