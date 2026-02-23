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

import mp.core.code_manipulation
import mp.core.config
import mp.core.file_utils
import mp.core.unix
from mp.telemetry import track_command

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mp.core.config import RuntimeParams

__all__: list[str] = ["format_app", "format_files"]
format_app: typer.Typer = typer.Typer()


@format_app.command(name="format", help="Format '.py' files.")
@track_command
def format_files(
    file_paths: Annotated[
        list[str] | None,
        typer.Argument(
            help="Path of the files or dirs to format",
            show_default=False,
        ),
    ] = None,
    *,
    changed_files: Annotated[
        bool,
        typer.Option(
            help=(
                "Check all changed files based on a diff with the"
                " origin/develop branch instead of --file-paths"
            ),
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            help="Log less on runtime.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            help="Log more on runtime.",
        ),
    ] = False,
) -> None:
    """Run the `mp format` command.

    Args:
        file_paths: the files to format
        changed_files: whether to ignore `file_paths` provided and check only the
            changed files in the last commit
        quiet: quiet log options
        verbose: Verbose log options

    """
    if file_paths is None:
        file_paths = []

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()
    sources: list[str] = _get_source_files(file_paths, changed_file=changed_files)
    if not sources:
        rich.print("No files found to check")
        return

    paths: set[Path] = _get_relevant_source_paths(sources)
    if not paths:
        rich.print("No relevant python files to format")
        return

    _format_python_files(paths)


def _get_source_files(file_paths: list[str], *, changed_file: bool) -> list[str]:
    return mp.core.unix.get_changed_files() if changed_file else file_paths


def _get_relevant_source_paths(sources: list[str]) -> set[Path]:
    return {
        path
        for source in sources
        if mp.core.file_utils.is_python_file(
            path := pathlib.Path(source).resolve().expanduser().absolute(),
        )
        or path.is_dir()
    }


def _format_python_files(paths: Iterable[Path]) -> None:
    rich.print(f"Formatting Python files: {', '.join(p.name for p in paths)}")
    mp.core.code_manipulation.format_python_files(paths)
