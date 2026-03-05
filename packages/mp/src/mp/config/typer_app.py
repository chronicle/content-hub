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
from typing import Annotated

import rich
import typer

import mp.core.config

__all__: list[str] = ["config", "config_app"]
config_app: typer.Typer = typer.Typer(name="config", help="Configure the mp CLI tool.")


@config_app.callback(invoke_without_command=True)
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
    gemini_api_key: Annotated[
        str | None,
        typer.Option(
            "--gemini-api-key",
            help="Configure the Gemini API key",
            show_default=False,
        ),
    ] = None,
    gemini_concurrency: Annotated[
        int | None,
        typer.Option(
            "--gemini-concurrency",
            help="Configure the number of concurrent Gemini requests for action description",
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
        gemini_concurrency: the number of concurrent Gemini requests for action description
        root_path: the path to the repository root directory
        processes: the number of processes can be run in parallel
        gemini_api_key: the Gemini API key
        display_config: whether to display the configuration after making the changes

    """
    if root_path is not None:
        _set_marketplace_path(root_path)

    if processes is not None:
        _set_processes_number(processes)

    if gemini_api_key is not None:
        _set_gemini_api_key(gemini_api_key)

    if gemini_concurrency is not None:
        _set_gemini_concurrency(gemini_concurrency)

    if display_config:
        p: pathlib.Path = mp.core.config.get_marketplace_path()
        n: int = mp.core.config.get_processes_number()
        c: int = mp.core.config.get_gemini_concurrency()
        k: str | None = mp.core.config.get_gemini_api_key()
        if k:
            k = f"{k[:4]}{'*' * (len(k) - 4)}"
        rich.print(
            f"Marketplace path: {p}\n"
            f"Number of processes: {n}\n"
            f"Gemini concurrency: {c}\n"
            f"API Key: {k}"
        )


def _set_marketplace_path(marketplace_path: str) -> None:
    mp_path: pathlib.Path = pathlib.Path(marketplace_path).expanduser()
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


def _set_gemini_api_key(api_key: str) -> None:
    mp.core.config.set_gemini_api_key(api_key)


def _set_gemini_concurrency(concurrency: int) -> None:
    if not isinstance(concurrency, int) or concurrency < 1:
        msg: str = "Gemini concurrency must be an integer greater than or equal to 1"
        raise ValueError(msg)

    mp.core.config.set_gemini_concurrency(concurrency)


def _is_processes_in_range(processes: int) -> bool:
    return mp.core.config.PROCESSES_MIN_VALUE <= processes <= mp.core.config.PROCESSES_MAX_VALUE
