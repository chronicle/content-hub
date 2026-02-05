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
import warnings
from typing import TYPE_CHECKING, Annotated, NamedTuple

import rich
import typer

import mp.core.code_manipulation
import mp.core.config
import mp.core.custom_types
import mp.core.file_utils
import mp.core.unix

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.config import RuntimeParams
    from mp.core.custom_types import RuffParams

__all__: list[str] = ["check", "check_app"]
check_app: typer.Typer = typer.Typer()


class CheckParams(NamedTuple):
    file_paths: list[str] | None
    ruff_params: RuffParams
    changed_files: bool
    static_type_check: bool
    raise_error_on_violations: bool

    def validate(self) -> None:
        """Validate the parameters.

        Validates input options
        and ensures compatibility between provided arguments.

        This method performs a series of checks
        to validate the state of the program's input arguments.
        It ensures that options provided by the user are in a valid,
        coherent state before further processing can occur.
        If invalid options are detected,
        the method raises appropriate errors
        to indicate the incompatibility or missing information.

        Raises:
            typer.BadParameter: If any of the following conditions are met:
                - `--unsafe-fixes` is used without the `--fix` option.
                - Neither `file_paths` nor `--changed-files` is provided.
                - Both `file_paths`and `--changed-files` are provided simultaneously.

        """
        msg: str
        if self.ruff_params.unsafe_fixes and not self.ruff_params.fix:
            msg = "To use --unsafe-fixes the --fix option must be passed as well"
            raise typer.BadParameter(msg)

        if self.file_paths is None and not self.changed_files:
            msg = "At least one path or --changed-files must be provided"
            raise typer.BadParameter(msg)

        if self.file_paths is not None and self.changed_files:
            msg = "Either provide paths or use --changed-files."
            raise typer.BadParameter(msg)


@check_app.command(name="check", help="Check and lint python")
def check(  # noqa: PLR0913
    file_paths: Annotated[
        list[str] | None,
        typer.Argument(
            help="Path of the files or dirs to check",
            show_default=False,
        ),
    ] = None,
    output_format: Annotated[
        mp.core.custom_types.CheckOutputFormat,
        typer.Option(
            help="Output serialization format for violations.",
        ),
    ] = mp.core.custom_types.CheckOutputFormat.FULL,
    *,
    fix: Annotated[
        bool,
        typer.Option(
            help="Fix minor issues in the code that require no action from the user",
        ),
    ] = False,
    unsafe_fixes: Annotated[
        bool,
        typer.Option(
            help="Fix issues in the code that needs to be reviewed by the user.",
        ),
    ] = False,
    changed_files: Annotated[
        bool,
        typer.Option(
            help=(
                "Check all changed files based on a diff with the head"
                " commit instead of --file-paths"
            ),
        ),
    ] = False,
    static_type_check: Annotated[
        bool,
        typer.Option(
            help="Perform static type checking on the provided files",
        ),
    ] = False,
    raise_error_on_violations: Annotated[
        bool,
        typer.Option(
            help="Whether to raise error on lint and type check violations",
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
    """Run the `mp check` command.

    Args:
        file_paths: file paths to check/lint
        output_format: Output serialization format for violations
        fix: whether to fix found issues
        unsafe_fixes: whether to fix all fixable issues, even if unsafe
        changed_files: whether to ignore `file_paths` provided and check only the
            changed files in the last commit
        static_type_check: whether to perform static type analysis on the code
        raise_error_on_violations: whether to raise error if any violations are found
        quiet: quiet log options
        verbose: Verbose log options

    """
    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()
    params: CheckParams = CheckParams(
        file_paths=file_paths,
        ruff_params=mp.core.custom_types.RuffParams(
            output_format=output_format,
            fix=fix,
            unsafe_fixes=unsafe_fixes,
        ),
        changed_files=changed_files,
        static_type_check=static_type_check,
        raise_error_on_violations=raise_error_on_violations,
    )
    params.validate()
    _check_paths(params)


def _check_paths(check_params: CheckParams) -> None:
    file_paths: list[str] | None = check_params.file_paths
    if file_paths is None:
        file_paths = []

    sources: list[str] = _get_source_files(
        file_paths,
        changed_files=check_params.changed_files,
    )
    if not sources:
        rich.print("No files found to check")
        return

    paths: set[Path] = _get_relevant_source_paths(sources)
    if not paths:
        rich.print("No relevant python files to check")
        return

    if check_params.raise_error_on_violations:
        warnings.filterwarnings("error")

    names: str = "\n".join(p.name for p in paths)
    rich.print(f"Checking {names}")
    mp.core.code_manipulation.lint_python_files(
        paths,
        params=check_params.ruff_params,
    )
    if check_params.static_type_check:
        rich.print("Performing static type checking on files")
        mp.core.code_manipulation.static_type_check_python_files(paths)


def _get_source_files(file_paths: list[str], *, changed_files: bool) -> list[str]:
    return mp.core.unix.get_changed_files() if changed_files else file_paths


def _get_relevant_source_paths(sources: list[str]) -> set[Path]:
    return {
        path
        for source in sources
        if mp.core.file_utils.is_python_file(
            path := pathlib.Path(source).resolve().expanduser().absolute(),
        )
        or path.is_dir()
    }
