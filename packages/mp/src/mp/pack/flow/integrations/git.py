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

import contextlib
import logging
import pathlib
import shutil
import subprocess  # noqa: S404

import typer

from mp.core import constants

GIT_PATH: str = shutil.which("git") or "git"
logger: logging.Logger = logging.getLogger(__name__)


def get_git_repo_root(path: pathlib.Path) -> pathlib.Path:
    """Get the Git repository root.

    Args:
        path: The path to check.

    Returns:
        pathlib.Path: The Git repository root path.

    Raises:
        RuntimeError: If the Git command fails.

    """
    try:
        output: str = (
            subprocess  # noqa: S603
            .check_output(
                [GIT_PATH, "rev-parse", "--show-toplevel"],
                cwd=path,
                stderr=subprocess.STDOUT,
            )
            .decode()
            .strip()
        )
        return pathlib.Path(output)
    except subprocess.CalledProcessError as e:
        msg: str = f"Failed to find Git repo root: {e.output.decode()}"
        raise RuntimeError(msg) from e


def find_commit_sha(src_path: pathlib.Path, version: str) -> str:
    """Find the Git commit SHA for a specific version.

    Args:
        src_path: The source path of the integration.
        version: The version to find.

    Returns:
        str: The commit SHA.

    Raises:
        typer.BadParameter: If the version commit cannot be found.

    """
    rel_notes_path: pathlib.Path = src_path / constants.RELEASE_NOTES_FILE
    commit_sha: str | None = None

    if rel_notes_path.exists():
        cmd: list[str] = [
            GIT_PATH,
            "log",
            "-S",
            f"integration_version: {version}",
            "--all",
            "--format=%H",
            "-n",
            "1",
            "--",
            rel_notes_path.name,
        ]
        with contextlib.suppress(subprocess.CalledProcessError):
            output: str = (
                subprocess  # noqa: S603
                .check_output(
                    cmd,
                    cwd=src_path,
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
            )
            if output:
                commit_sha = output

    # Try pyproject.toml if not found
    if not commit_sha:
        pyproject_path: pathlib.Path = src_path / constants.PROJECT_FILE
        if pyproject_path.exists():
            cmd: list[str] = [
                GIT_PATH,
                "log",
                "-S",
                f'version = "{version}"',
                "--all",
                "--format=%H",
                "-n",
                "1",
                "--",
                pyproject_path.name,
            ]
            with contextlib.suppress(subprocess.CalledProcessError):
                output: str = (
                    subprocess  # noqa: S603
                    .check_output(
                        cmd,
                        cwd=src_path,
                        stderr=subprocess.STDOUT,
                    )
                    .decode()
                    .strip()
                )
                if output:
                    commit_sha = output

    if not commit_sha:
        msg: str = f"Could not find Git commit for version {version} of integration '{src_path.name}'."
        raise typer.BadParameter(msg)

    return commit_sha


def create_git_worktree(src_path: pathlib.Path, version: str, temp_dir: pathlib.Path) -> None:
    """Create a temporary Git worktree for a specific version.

    Args:
        src_path: The source path of the integration.
        version: The version to check out.
        temp_dir: The path to the temporary worktree.

    Raises:
        RuntimeError: If the Git command fails.

    """
    repo_root: pathlib.Path = get_git_repo_root(src_path)
    commit_sha: str = find_commit_sha(src_path, version)
    try:
        subprocess.run(  # noqa: S603
            [GIT_PATH, "worktree", "add", str(temp_dir), commit_sha],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        msg: str = f"Failed to create Git worktree: {e.stderr.decode()}"
        raise RuntimeError(msg) from e


def remove_git_worktree(temp_dir: pathlib.Path, repo_root: pathlib.Path) -> None:
    """Remove a temporary Git worktree.

    Args:
        temp_dir: The path to the temporary worktree.
        repo_root: The Git repository root path.

    """
    git_path: str = shutil.which("git") or "git"
    try:
        subprocess.run(  # noqa: S603
            [git_path, "worktree", "remove", "--force", str(temp_dir)],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        logger.exception("Failed to remove Git worktree %s", temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
