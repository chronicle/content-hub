"""Package for managing the application's configuration settings.

This package provides a command-line interface to configure various
aspects of the application, such as the path to the marketplace repository
and the number of parallel processes to use. It allows users to set these
configurations via command-line options and displays the current
configuration when requested. The configurations are stored and accessed
through the `core.config` module.
"""

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

import pathlib
from typing import TYPE_CHECKING, Annotated

import rich
import typer

import mp.core.config

if TYPE_CHECKING:
    from pathlib import Path

__all__: list[str] = ["app", "config"]
app: typer.Typer = typer.Typer()


@app.command(name="config", help="Configure script settings")
def config(
    root_path: Annotated[
        str | None,
        typer.Option(
            help="Configure the path to tip-marketplace repository root directory",
            show_default=False,
        ),
    ] = None,
    processes: Annotated[
        int | None,
        typer.Option(
            help="Configure the number of processes can be run in parallel",
            show_default=False,
        ),
    ] = None,
    *,
    display_config: Annotated[
        bool,
        typer.Option(
            help="Show the current configuration.",
        ),
    ] = False,
) -> None:
    """Run the `mp config` command.

    Args:
        root_path: the path to the repository root directory
        processes: the number of processes can be run in parallel
        display_config: whether to display the configuration after making the changes

    """
    if root_path is not None:
        _set_marketplace_path(root_path)

    if processes is not None:
        _set_processes_number(processes)

    if display_config:
        p: Path = mp.core.config.get_marketplace_path()
        n: int = mp.core.config.get_processes_number()
        rich.print(f"Marketplace path: {p}\nNumber of processes: {n}")


def _set_marketplace_path(marketplace_path: str) -> None:
    mp_path: Path = pathlib.Path(marketplace_path).expanduser()
    if not mp_path.exists():
        msg: str = f"Path {mp_path} cannot be found!"
        raise FileNotFoundError(msg)

    if not mp_path.is_dir():
        msg = "The provided marketplace path must be a dir!"
        raise NotADirectoryError(msg)

    mp.core.config.set_marketplace_path(mp_path)


def _set_processes_number(processes: int) -> None:
    if not isinstance(processes, int) or not _is_processes_in_range(processes):
        msg: str = "Processes must be an integer between 1 and 10"
        raise ValueError(msg)

    mp.core.config.set_processes_number(processes)


def _is_processes_in_range(processes: int) -> bool:
    return mp.core.config.PROCESSES_MIN_VALUE <= processes <= mp.core.config.PROCESSES_MAX_VALUE
