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

import threading
import tomllib
from contextlib import suppress
from typing import Any

import requests
import typer
from packaging.version import parse as parse_version

PYPROJECT_URL = (
    "https://raw.githubusercontent.com/chronicle/content-hub/main/packages/mp/pyproject.toml"
)
TIMEOUT_SECONDS = 2.0

# Store the result of the check
_NEW_VERSION: str | None = None
_CHECK_THREAD: threading.Thread | None = None


def check_for_updates_background(current_version: str) -> None:
    """Start checking for updates in a background thread."""
    global _CHECK_THREAD  # noqa: PLW0603
    _CHECK_THREAD = threading.Thread(target=_check_update_worker, args=(current_version,))
    _CHECK_THREAD.daemon = True
    _CHECK_THREAD.start()


def print_update_warning_if_needed() -> None:
    """Print a warning if a new version was found during the background check."""
    if _CHECK_THREAD and _CHECK_THREAD.is_alive():
        _CHECK_THREAD.join(timeout=1.0)

    if _NEW_VERSION:
        _print_warning(_NEW_VERSION)


def _check_update_worker(current_version: str) -> None:
    global _NEW_VERSION  # noqa: PLW0603
    if current_version == "unknown":
        return

    with suppress(Exception, requests.RequestException):
        response = requests.get(PYPROJECT_URL, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data: dict[str, dict[str, Any]] = tomllib.loads(response.text)
        remote_version: str = data.get("project", {}).get("version")

        if not remote_version:
            return

        if parse_version(remote_version) > parse_version(current_version):
            _NEW_VERSION = remote_version


def _print_warning(remote_version: str) -> None:
    message: str = (
        f"\nWARNING: A newer version of mp ({remote_version}) is available.\n"
        "Run 'mp self update' to update.\n"
    )
    typer.secho(message, fg=typer.colors.YELLOW, err=True)
