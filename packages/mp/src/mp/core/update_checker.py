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

import dataclasses
import importlib.metadata
import threading
import tomllib
from contextlib import suppress
from typing import Any

import requests
import rich
import typer
from packaging.version import InvalidVersion
from packaging.version import parse as parse_version

PYPROJECT_URL: str = (
    "https://raw.githubusercontent.com/chronicle/content-hub/main/packages/mp/pyproject.toml"
)
TIMEOUT_SECONDS: float = 2.0


class UpdateChecker:
    __slots__ = ("_check_thread", "_new_version")

    def __init__(self) -> None:
        self._new_version: str | None = None
        self._check_thread: threading.Thread | None = None

    def start_background_check(self, current_version: str) -> None:
        """Start a background thread to check for updates."""
        if current_version == "unknown":
            return

        self._check_thread = threading.Thread(
            target=self._check_update_worker,
            args=(current_version,),
        )
        self._check_thread.daemon = True
        self._check_thread.start()

    def print_warning_if_needed(self) -> None:
        """Print a warning if a newer version is available."""
        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=0.5)

        if self._new_version:
            _print_version_warning(self._new_version)

    def _check_update_worker(self, current_version: str) -> None:
        with suppress(
            requests.RequestException,
            requests.HTTPError,
            tomllib.TOMLDecodeError,
            KeyError,
            InvalidVersion,
        ):
            response: requests.Response = requests.get(PYPROJECT_URL, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            data: dict[str, Any] = tomllib.loads(response.text)
            remote_version: str | None = data.get("project", {}).get("version")

            if remote_version and parse_version(remote_version) > parse_version(current_version):
                self._new_version = remote_version


def _print_version_warning(remote_version: str) -> None:
    current_version: str = get_mp_version()
    message: str = (
        f"\n[bold yellow]WARNING:[/bold yellow] A newer version of mp "
        f"({current_version} -> {remote_version}) is available.\n"
        f"Run 'mp self update' to update.\n"
    )
    rich.print(message)


def print_mp_version(*, value: bool) -> None:
    """Print the current version of the mp tool.

    Raises:
        typer.Exit: If the version is printed.

    """
    if value:
        version: str = get_mp_version()
        rich.print(f"mp {version}")
        raise typer.Exit


def get_mp_version() -> str:
    """Get the current version of mp.

    Returns:
        str: The current version of mp.

    """
    try:
        return importlib.metadata.version("mp")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


@dataclasses.dataclass(frozen=True, slots=True)
class AppState:
    update_checker: UpdateChecker = dataclasses.field(default_factory=UpdateChecker)
