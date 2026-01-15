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
import multiprocessing
import pathlib
import warnings
from typing import TYPE_CHECKING, Annotated

import typer

import mp.core.config
import mp.core.constants
import mp.core.file_utils
import mp.core.unix
from mp.core.code_manipulation import TestWarning
from mp.core.custom_types import Products, RepositoryType
from mp.core.utils import ensure_valid_list, is_windows
from mp.telemetry import track_command

from .display import display_test_reports
from .process_test_output import IntegrationTestResults, TestIssue, process_pytest_json_report

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mp.core.config import RuntimeParams

WINDOWS_SCRIPT_NAME: str = "run_pre_build_tests.bat"
UNIX_SCRIPT_NAME: str = "run_pre_build_tests.sh"
SUCCESS_STATUS_CODES: set[int] = {0, 2}

__all__: list[str] = ["Products", "TestIssue", "TestWarning", "app", "run_pre_build_tests"]
app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class TestParams:
    repository: Iterable[RepositoryType]
    integrations: Iterable[str]

    def validate(self) -> None:
        """Validate the parameters.

        Validates input parameters to ensure that only one parameter among
        `--repository`,
         or `--integration` is used during execution.

        Raises appropriate error messages if none or more than one of these
        parameters is specified.

        Raises:
            typer.BadParameter: If none of `--repository`, or
                `--integration` is provided or more than one of them is used.

        """
        params: list[Iterable[str] | Iterable[RepositoryType]] = self._as_list()
        msg: str
        if not any(params):
            msg = "At least one of --repository, or --integration must be used."
            raise typer.BadParameter(msg)

        if sum(map(bool, params)) != 1:
            msg = "Only one of --repository, or --integration shall be used."
            raise typer.BadParameter(msg)

    def _as_list(self) -> list[Iterable[RepositoryType] | Iterable[str]]:
        return [self.repository, self.integrations]


@app.command(name="test", help="Run integration pre_build tests")
@track_command
def run_pre_build_tests(
    repository: Annotated[
        list[RepositoryType],
        typer.Option(
            help="Build all integrations in specified integration repositories",
            default_factory=list,
        ),
    ],
    integration: Annotated[
        list[str],
        typer.Option(
            help="Build a specified integration",
            default_factory=list,
        ),
    ],
    *,
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
    """Run the `mp test` command.

    Args:
        repository: the repository to build
        integration: the integrations to build
        raise_error_on_violations: whether to raise error if any violations are found
        quiet: quiet log options
        verbose: Verbose log options

    Raises:
        typer.Exit: If one or more tests are failed.

    """
    if raise_error_on_violations:
        warnings.filterwarnings("error")

    repository = ensure_valid_list(repository)
    integration = ensure_valid_list(integration)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: TestParams = TestParams(repository, integration)
    params.validate()

    commercial_paths: Iterable[Path] = mp.core.file_utils.get_integration_base_folders_paths(
        mp.core.constants.COMMERCIAL_REPO_NAME
    )
    community_paths: Iterable[Path] = mp.core.file_utils.get_integration_base_folders_paths(
        mp.core.constants.THIRD_PARTY_REPO_NAME
    )

    all_integration_results: list[IntegrationTestResults] = []

    if integration:
        commercial_integrations: set[Path] = _get_mp_paths_from_names(
            names=integration,
            marketplace_paths=commercial_paths,
        )
        all_integration_results.extend(_test_integrations(commercial_integrations))

        community_integrations: set[Path] = _get_mp_paths_from_names(
            names=integration,
            marketplace_paths=community_paths,
        )
        all_integration_results.extend(_test_integrations(community_integrations))

    elif repository:
        repos: set[RepositoryType] = set(repository)
        if RepositoryType.COMMERCIAL in repos:
            all_integration_results.extend(_test_repository(commercial_paths))

        if RepositoryType.THIRD_PARTY in repos:
            all_integration_results.extend(_test_repository(community_paths))

    display_test_reports(all_integration_results)
    if all_integration_results:
        raise typer.Exit(code=1)


def _test_repository(repo_paths: Iterable[Path]) -> list[IntegrationTestResults]:
    integrations: set[Path] = mp.core.file_utils.get_integrations_from_paths(*repo_paths)
    all_integration_results: list[IntegrationTestResults] = []
    if integrations:
        all_integration_results.extend(_test_integrations(integrations))

    return all_integration_results


def _test_integrations(integrations: Iterable[Path]) -> list[IntegrationTestResults]:
    if integrations:
        return _run_script_on_paths(
            script_path=_get_tests_script_paths(),
            paths=integrations,
        )
    return []


def _get_tests_script_paths() -> Path:
    file_name: str = WINDOWS_SCRIPT_NAME if is_windows() else UNIX_SCRIPT_NAME
    return pathlib.Path(__file__).parent / file_name


def _run_script_on_paths(script_path: Path, paths: Iterable[Path]) -> list[IntegrationTestResults]:
    paths = [p for p in paths if p.is_dir()]
    all_integration_results: list[IntegrationTestResults] = []

    processes: int = mp.core.config.get_processes_number()
    tasks_arguments = [(script_path, p) for p in paths]
    with multiprocessing.Pool(processes=processes) as pool:
        results_iterator = pool.starmap(_run_tests_for_single_integration, tasks_arguments)

        for result in results_iterator:
            if result is not None:
                all_integration_results.append(result)  # noqa: PERF401

    return all_integration_results


def _run_tests_for_single_integration(
    script_path: Path,
    integration_path: Path,
) -> IntegrationTestResults | None:
    status_code: int = mp.core.unix.run_script_on_paths(script_path, integration_path)

    json_report_path = integration_path / ".report.json"
    if status_code in SUCCESS_STATUS_CODES:
        json_report_path.unlink(missing_ok=True)
        return None

    return process_pytest_json_report(integration_path.name, json_report_path)


def _get_mp_paths_from_names(
    names: Iterable[str | Path],
    marketplace_paths: Iterable[Path],
) -> set[Path]:
    results: set[Path] = set()

    for path in marketplace_paths:
        for name in names:
            if isinstance(name, str) and (p := path / name).exists():
                results.add(p)

            elif isinstance(name, pathlib.Path) and name.exists():
                results.add(name)

    return results
