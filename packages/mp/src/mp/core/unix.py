"""Module for interacting with the operating system and executing shell commands."""

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
import re
import subprocess as sp  # noqa: S404
import sys
from typing import IO, TYPE_CHECKING

import rich

from mp.core.exceptions import FatalValidationError, NonFatalValidationError
from mp.core.utils import is_windows

from . import config, constants, file_utils

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

COMMAND_ERR_MSG: str = "Error happened while executing a command: {0}"
PACKAGE_PATTERN: str = r"([^=<>~]+)==(.*)"
PY3_WHEEL_FILE_SUFFIX: str = "-py3-none-any.whl"
MIN_RELEVANT_TIP_COMMON_VERSION: int = 2


class FatalCommandError(FatalValidationError):
    """Fatal error that happens during commands."""


class NonFatalCommandError(NonFatalValidationError):
    """Non-fatal error that happens during shell commands."""


def compile_core_integration_dependencies(project_path: Path, requirements_path: Path) -> None:
    """Compile/Export all project dependencies into a requirements' file.

    Args:
        project_path: the path to the project folder - one that contains a
            `pyproject.toml` file
        requirements_path: the path to the requirements' file to write the contents into

    Raises:
        FatalCommandError: if a project is already initialized

    """
    python_version: str = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    command: list[str] = [
        sys.executable,
        "-m",
        "uv",
        "export",
        "--project",
        str(project_path),
        "--output-file",
        str(requirements_path),
        "--no-hashes",
        "--no-dev",
        "--python",
        python_version,
    ]
    runtime_config: list[str] = _get_runtime_config()
    command.extend(runtime_config)

    try:
        sp.run(command, cwd=project_path, check=True, text=True)  # noqa: S603
    except sp.CalledProcessError as e:
        raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e


def _get_safe_to_ignore_packages(e: sp.CalledProcessError, /) -> list[str]:
    full_msg: str = f"{e.stdout or ''}\n{e.stderr or ''}"
    ignored_packages: list[str] = [
        pkg for pkg in constants.SAFE_TO_IGNORE_PACKAGES if pkg in full_msg
    ]
    ignored_messages: list[bool] = [
        msg in full_msg for msg in constants.SAFE_TO_IGNORE_ERROR_MESSAGES
    ]
    if ignored_messages and ignored_packages:
        return ignored_packages
    return []


def run_pip_command(command: list[str], cwd: Path) -> None:
    """Run a pip command and ignore safe-to-ignore errors.

    Raises:
        FatalCommandError: if a pip command fails.

    """
    try:
        sp.run(command, cwd=cwd, capture_output=True, text=True, check=True)  # noqa: S603
    except sp.CalledProcessError as e:
        # Check if this is a safe-to-ignore error / marker issue
        if ignored_packages := _get_safe_to_ignore_packages(e):
            message = (
                f"[INFO] Ignored safe-to-ignore packages due to Python version "
                f"incompatibility: {', '.join(ignored_packages)}\n"
            )
            rich.print(message)
            return
        raise FatalCommandError from e


def download_wheels_from_requirements(
    project_path: Path,
    requirements_path: Path,
    dst_path: Path,
) -> None:
    """Download `.whl` files from a requirements' file.

    Args:
        project_path: the path of the project repository
        requirements_path: the path of the 'requirements.txt' file
        dst_path: the path to install the `.whl` files into

    Raises:
        FatalCommandError: if a project is already initialized

    """
    python_version: str = _get_python_version()
    command: list[str] = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "-r",
        str(requirements_path),
        "-d",
        str(dst_path),
        "--only-binary=:all:",
        "--python-version",
        python_version,
        "--implementation",
        "cp",
        "--platform",
        "none-any",
    ]
    runtime_config: list[str] = _get_runtime_config()
    command.extend(runtime_config)

    try:
        if is_windows():
            command.extend(["--platform", "win_amd64"])
        else:
            command.extend([
                "--platform",
                "manylinux1_x86_64",
                "--platform",
                "manylinux_2_17_x86_64",
            ])
        run_pip_command(command, cwd=project_path)
    except sp.CalledProcessError as e:
        raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e


def _get_base_dev_dependencies() -> list[str]:
    """Return a list of base development dependencies.

    Returns:
        A list of dependency specifiers for `uv add`.

    """
    return [
        "pytest",
        "pytest-json-report",
    ]


def _get_base_dev_vcs_dependencies() -> list[str]:
    return ["git+https://github.com/chronicle/soar-sdk.git"]


def _resolve_dependencies(requirements_path: Path) -> tuple[list[str], list[str]]:
    """Resolve dependencies from a requirements file, handling local packages.

    Args:
        requirements_path: The path to the requirements.txt file.

    Returns:
        A list of dependency specifiers for `uv add`.

    Raises:
        FileNotFoundError: If a local dependency's directory or wheel is not found.

    """
    local_packages_base_path: Path = config.get_local_packages_path()
    deps_to_add: list[str] = []
    dev_deps_to_add: list[str] = []

    with requirements_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped_line: str = line.strip()
            if not stripped_line or stripped_line.startswith("#"):
                continue

            match = re.match(PACKAGE_PATTERN, stripped_line)
            if not match:
                deps_to_add.append(stripped_line)
                continue

            name, version = match.groups()
            if name in constants.LOCAL_PACKAGES_CONFIG:
                version_dir: Path = local_packages_base_path / _resolve_version_dir(name, version)
                if not version_dir.is_dir():
                    msg: str = f"Could not find local dependency directory: {version_dir}"
                    raise FileNotFoundError(msg)

                try:
                    wheel_file: Path = next(version_dir.glob("*.whl"))
                    deps_to_add.append(str(wheel_file))
                    if _should_add_integration_testing(name, version, requirements_path):
                        integration_testing_wheel_file_name: str = (
                            f"{_resolve_version_dir('integration-testing', version)}"
                            f"{PY3_WHEEL_FILE_SUFFIX}"
                        )
                        integration_testing_wheel = (
                            local_packages_base_path / integration_testing_wheel_file_name
                        )
                        dev_deps_to_add.append(str(integration_testing_wheel))
                except StopIteration:
                    msg: str = f"No wheel file found in {version_dir}"
                    raise FileNotFoundError(msg) from None
            else:
                deps_to_add.append(stripped_line)

    return deps_to_add, dev_deps_to_add


def _should_add_integration_testing(name: str, version: str, requirements_path: Path) -> bool:
    is_relevant_tip_common_version: bool = (
        name == "tipcommon" and int(version[0]) >= MIN_RELEVANT_TIP_COMMON_VERSION
    )
    testing_dir: Path = requirements_path.parent / constants.TESTING_DIR
    return is_relevant_tip_common_version and testing_dir.is_dir()


def _resolve_version_dir(name: str, version: str) -> str:
    package_config: dict[str, str] = constants.LOCAL_PACKAGES_CONFIG[name]
    package_wheel_prefix: str = package_config["wheel_prefix"]
    package_dir_name: str = package_config["dir_name"]
    version_dir_name: str = f"{package_wheel_prefix}-{version}"
    return f"{package_dir_name}/{version_dir_name}"


def _add_dev_dependencies_to_toml(
    base_command: list[str], project_path: Path, dev_deps_to_add: list[str]
) -> None:
    vcs_deps_to_add = _get_base_dev_vcs_dependencies()
    dev_base_command = base_command.copy()
    dev_base_command.extend(["--group", "dev"])

    if vcs_deps_to_add:
        vcs_command = dev_base_command.copy()
        vcs_command.extend(vcs_deps_to_add)
        try:
            sp.run(vcs_command, cwd=project_path, check=True, text=True, capture_output=True)  # noqa: S603
        except sp.CalledProcessError as e:
            raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e

    base_dependencies_command = dev_base_command.copy()
    base_dependencies_command.extend(_get_base_dev_dependencies())
    if dev_deps_to_add:
        base_dependencies_command.extend(dev_deps_to_add)
    try:
        sp.run(  # noqa: S603
            base_dependencies_command, cwd=project_path, check=True, text=True, capture_output=True
        )
    except sp.CalledProcessError as e:
        raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e


def add_dependencies_to_toml(project_path: Path, requirements_path: Path) -> None:
    """Add dependencies from requirements to a python project's TOML file.

    This function distinguishes between remote dependencies (fetched from PyPI)
    and local dependencies (found in the path specified in the config).

    Args:
        project_path: the path to the project
        requirements_path: the path to the requirements to add

    Raises:
        FatalCommandError: if uv add fails.

    """
    python_version: str = _get_python_version()
    base_command: list[str] = [
        sys.executable,
        "-m",
        "uv",
        "add",
        "--python",
        python_version,
    ]
    runtime_config: list[str] = _get_runtime_config()
    base_command.extend(runtime_config)
    deps_to_add, dev_deps_to_add = _resolve_dependencies(requirements_path)
    if deps_to_add:
        deps_command: list[str] = base_command.copy()
        deps_command.extend(deps_to_add)
        deps_command.extend([
            "--default-index",
            "https://pypi.org/simple",
        ])
        try:
            sp.run(deps_command, cwd=project_path, check=True, text=True)  # noqa: S603

        except sp.CalledProcessError as e:
            raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e

    _add_dev_dependencies_to_toml(base_command, project_path, dev_deps_to_add)


def init_python_project_if_not_exists(project_path: Path) -> None:
    """Initialize a python project in a folder.

    If a project is already initialized in there, nothing will happen.

    Args:
        project_path: the path to initialize the project

    """
    pyproject: Path = project_path / constants.PROJECT_FILE
    if pyproject.exists():
        return

    initials: set[Path] = set(project_path.iterdir())
    keep: set[Path] = {
        project_path / constants.PROJECT_FILE,
        project_path / constants.LOCK_FILE,
    }

    init_python_project(project_path)

    paths: set[Path] = set(project_path.iterdir())
    paths_to_remove: set[Path] = paths.difference(initials).difference(keep)
    file_utils.remove_paths_if_exists(*paths_to_remove)


def init_python_project(project_path: Path) -> None:
    """Initialize a python project in a folder.

    Args:
        project_path: the path to initialize the project

    Raises:
        FatalCommandError: if a project is already initialized

    """
    python_version: str = _get_python_version()
    command: list[str] = [
        sys.executable,
        "-m",
        "uv",
        "init",
        "--no-readme",
        "--no-workspace",
        "--python",
        python_version,
    ]

    runtime_config: list[str] = _get_runtime_config()
    command.extend(runtime_config)

    try:
        sp.run(command, cwd=project_path, check=True, text=True)  # noqa: S603
    except sp.CalledProcessError as e:
        raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e


def ruff_check(paths: Iterable[Path], /, **flags: bool | str) -> int:
    """Run `ruff check` on the provided paths.

    Returns:
        The status code

    """
    command: list[str] = [sys.executable, "-m", "ruff", "check"]
    return execute_command_and_get_output(command, paths, **flags)


def ruff_format(paths: Iterable[Path], /, **flags: bool | str) -> int:
    """Run `ruff format` on the provided paths.

    Returns:
        The status code

    """
    command: list[str] = [sys.executable, "-m", "ruff", "format"]
    return execute_command_and_get_output(command, paths, **flags)


def ty_check(paths: Iterable[Path], /, **flags: bool | str) -> int:
    """Run `ty check` on the provided paths.

    Returns:
        The status code

    """
    command: list[str] = [sys.executable, "-m", "ty", "check"]
    return execute_command_and_get_output(command, paths, **flags)


def run_script_on_paths(script_path: Path, *test_paths: Path) -> int:
    """Run a custom script on the provided paths.

    Returns:
        The status code of the output

    """
    script_full_path: str = f"{script_path.resolve().absolute()}"

    if not sys.platform.startswith("win"):
        chmod_command: list[str] = ["chmod", "+x", script_full_path]
        sp.run(chmod_command, check=True)  # noqa: S603

    command: list[str] = [script_full_path] + [str(p) for p in test_paths]

    result = sp.run(  # noqa: S603
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode


def execute_command_and_get_output(
    command: list[str], paths: Iterable[Path], **flags: bool | str
) -> int:
    """Execute a command and capture its output and status code.

    Args:
        command: the command values to execute
        paths: path values for the command
        **flags: any command flags as keyword arguments

    Returns:
        The status code of the process

    Raises:
        FatalCommandError: if a project is already initialized

    """
    command.extend(str(path) for path in paths)

    flags_: list[str] = get_flags_to_command(**flags)
    command.extend(flags_)

    runtime_config: list[str] = _get_runtime_config()
    command.extend(runtime_config)

    try:
        process: sp.Popen[bytes] = sp.Popen(command)  # noqa: S603
        for line in _stream_process_output(process):
            rich.print(str(line))
        return process.wait()

    except sp.CalledProcessError as e:
        raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e


def _stream_process_output(process: sp.Popen[bytes]) -> Iterator[bytes]:
    buffer: IO[bytes] | None = process.stdout
    if process.stdout is None:
        buffer = process.stderr

    if buffer is None:
        return

    line: bytes = buffer.readline()
    while line:
        yield line
        line = buffer.readline()


def get_changed_files() -> list[str]:
    """Get a list of file names that were changed since the last commit.

    Returns:
        A list of file names that were changed since the last commit.

    Raises:
        FatalCommandError: The command failed to be executed

    """
    command: list[str] = [
        "git",
        "diff",
        "HEAD^",
        "HEAD",
        "--name-only",
        "--diff-filter=ACMRTUXB",
    ]
    try:
        result: sp.CompletedProcess[str] = sp.run(  # noqa: S603
            command,
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.split()

    except sp.CalledProcessError as e:
        raise FatalCommandError(COMMAND_ERR_MSG.format(e)) from e


def _get_runtime_config() -> list[str]:
    result: list[str] = []
    if config.is_quiet():
        result.append("--quiet")

    if config.is_verbose():
        result.append("--verbose")

    return result


def get_flags_to_command(**flags: bool | str | list[str]) -> list[str]:
    """Get all the kwarg flags as a string with the appropriate `-` or `--`.

    Examples:
        >>> get_flags_to_command(f=True, name="TIPCommon", files=["1", "2"])
        >>> "-f --name TIPCommon --files 1 2"

    Keyword Args:
        **flags: The flags to parse

    Returns:
        A string containing the flags for a command.

    """
    if not flags:
        return []

    all_flags: list[str] = []
    for flag, value in flags.items():
        f: str = flag.replace("_", "-")
        f = f"-{f}" if len(f) == 1 else f"--{f}"
        all_flags.append(f)
        if isinstance(value, bool):
            if value is False:
                all_flags.pop()

        elif isinstance(value, list):
            all_flags.extend(value)

        else:
            all_flags.append(value)

    return all_flags


def check_lock_file(project_path: Path) -> None:
    """Check if the 'uv.lock' file is consistent with 'pyproject.toml' file.

    Args:
        project_path: The integration path to the project directory
                      that contains 'pyproject.toml' and 'uv.lock' files.

    Raises:
        NonFatalCommandError: If the 'uv lock --check' command indicates that the
                      'uv.lock' file is out of sync or if another error
                      occurs during the check.

    """
    python_version: str = _get_python_version()

    command: list[str] = [
        sys.executable,
        "-m",
        "uv",
        "lock",
        "--check",
        "--project",
        str(project_path),
        "--python",
        python_version,
    ]

    runtime_config: list[str] = _get_runtime_config()
    command.extend(runtime_config)

    try:
        sp.run(  # noqa: S603
            command, cwd=project_path, check=True, text=True, capture_output=True
        )

    except sp.CalledProcessError as e:
        error_output = e.stderr.strip()
        error_output = f"{COMMAND_ERR_MSG.format('uv lock --check')}: {error_output}"
        raise NonFatalCommandError(error_output) from e


def get_files_unmerged_to_main_branch(
    base: str,
    head_sha: str,
    integration_path: Path,
) -> list[Path]:
    """Return a list of file names changed in a pull request compared to the main branch.

    Args:
        base: The base branch of the PR.
        head_sha: The head commit SHA of the PR.
        integration_path: The path to the integration directory.

    Returns:
        A list of changed file paths.

    Raises:
        NonFatalCommandError: If the git command fails.

    """
    command: list[str] = [
        "git",
        "diff",
        f"origin/{base}...{head_sha}",
        "--name-only",
        "--diff-filter=ACMRTUXB",
        str(integration_path),
    ]
    try:
        results: sp.CompletedProcess[str] = sp.run(  # noqa: S603
            command, check=True, text=True, capture_output=True
        )
        return [
            p
            for path in results.stdout.strip().splitlines()
            if path and (p := pathlib.Path(path)).exists()
        ]

    except sp.CalledProcessError as error:
        error_output: str = f"{COMMAND_ERR_MSG.format('git diff')}: {error.stderr.strip()}"
        raise NonFatalCommandError(error_output) from error


def get_file_content_from_main_branch(file_path: Path) -> str:
    """Return the content of a specific file from the 'main' branch.

    Args:
        file_path: The path to the file.

    Returns:
        The content of the file as a string.

    Raises:
        NonFatalCommandError: If the git command fails (e.g., file not found on main).

    """
    git_path_arg: str = f"origin/main:{file_path.as_posix()}"
    command: list[str] = ["git", "show", git_path_arg]

    try:
        results: sp.CompletedProcess[str] = sp.run(  # noqa: S603
            command, check=True, text=True, capture_output=True
        )

    except sp.CalledProcessError as error:
        error_output: str = (
            f"Failed to get content of '{file_path}' from main branch: {error.stderr.strip()}"
        )
        raise NonFatalCommandError(error_output) from error

    else:
        return results.stdout


def _get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
