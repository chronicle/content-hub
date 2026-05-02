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

import datetime
import json
import pathlib
import re
import shutil
import subprocess  # noqa: S404
import sys
import tempfile
import zipfile
from typing import Any

import questionary
import typer
from questionary import Choice

from mp.build_project.flow.integrations.flow import build_integrations
from mp.core import constants
from mp.core.file_utils import (
    create_or_get_out_dir,
    get_marketplace_integration_path,
)
from mp.core.utils import str_to_snake_case


def _find_integration_src_path(integration_name: str) -> tuple[pathlib.Path, str]:
    """Find the source path of the integration, trying snake_case if needed.

    Args:
        integration_name: The name of the integration.

    Returns:
        tuple[pathlib.Path, str]: The source path and the resolved integration name.

    Raises:
        typer.BadParameter: If the integration is not found.

    """
    src_path = get_marketplace_integration_path(integration_name)
    resolved_name = integration_name

    if not src_path:
        # Try snake_case version
        snake_name = str_to_snake_case(integration_name)
        src_path = get_marketplace_integration_path(snake_name)
        if src_path:
            resolved_name = snake_name

    if not src_path:
        msg = f"Integration '{integration_name}' not found."
        raise typer.BadParameter(msg)

    return src_path, resolved_name


def _set_is_custom(def_path: pathlib.Path) -> None:
    """Set IsCustom=True in the integration definition file.

    Args:
        def_path: The path to the integration definition file.

    """
    try:
        with def_path.open("r+", encoding="utf-8") as f:
            def_data = json.load(f)
            def_data["IsCustom"] = True
            f.seek(0)
            json.dump(def_data, f, indent=4)
            f.truncate()
    except (OSError, json.JSONDecodeError) as e:
        typer.echo(f"Warning: Failed to set IsCustom in {def_path}: {e}", err=True)


def pack_integration(

    integration_name: str,
    *,
    version: float | None = None,
    beta_name: str | None = None,
    zip_dir: pathlib.Path | None = None,
    interactive: bool = True,
) -> None:
    """Flow for packing an integration into a SOAR supported ZIP.

    Args:
        integration_name: The name of the integration to pack.
        version: Old version to fetch from the repo and create the ZIP.
        beta_name: Name of the custom beta integration.
        zip_dir: Directory to save the ZIP file.
        interactive: Enable or disable interactive component selection.

    Raises:
        RuntimeError: If Git operations or build process fails.

    """
    # 1. Find integration source path
    src_path, integration_name = _find_integration_src_path(integration_name)
    repo_root = _get_git_repo_root(src_path)

    # 2. Handle Git Checkout if version provided
    temp_worktree: pathlib.Path | None = None
    build_src = src_path
    if version is not None:
        typer.echo(f"Fetching version {version} via Git...")
        temp_worktree = _create_git_worktree(src_path, version)
        rel_path = src_path.relative_to(repo_root)
        build_src = temp_worktree / rel_path
        typer.echo(f"Checked out version {version} to temporary worktree.")

    try:
        # 3. Build integration
        typer.echo(f"Building integration '{integration_name}'...")
        with tempfile.TemporaryDirectory(prefix=f"mp_pack_{integration_name}_") as temp_build_dir:
            temp_build_path = pathlib.Path(temp_build_dir)

            if version is not None:
                # Build from worktree
                build_integrations(
                    integrations=[integration_name],
                    repositories=[],
                    src=build_src.parent,
                    dst=temp_build_path,
                    custom_integration=True,
                )
            else:
                # Build current version
                build_integrations(
                    integrations=[integration_name],
                    repositories=[],
                    dst=temp_build_path,
                )

            # Find the built integration directory
            def_files = list(temp_build_path.rglob("Integration-*.def"))
            if not def_files:
                msg = f"Build failed: No Integration-*.def found in {temp_build_path}"
                raise RuntimeError(msg)

            built_dir = def_files[0].parent
            identifier = built_dir.name

            # Set IsCustom = True (required for importing via SOAR UI)
            _set_is_custom(def_files[0])

            # 4. Apply Beta / Custom Identifier modifications

            if beta_name:
                typer.echo(f"Applying custom beta identifier '{beta_name}'...")
                _apply_beta_modifications(built_dir, identifier, beta_name, version)
                identifier = beta_name

            # 5. Interactive Component Selection
            if interactive and _is_tty():
                _interactive_component_selection(built_dir)
            elif interactive:
                typer.echo("Non-TTY environment detected. Skipping interactive component selection (including all).")

            # 6. ZIP the output
            if zip_dir is None:
                zip_dir = create_or_get_out_dir() / "pack"
                zip_dir.mkdir(parents=True, exist_ok=True)
            else:
                zip_dir = pathlib.Path(zip_dir)
                zip_dir.mkdir(parents=True, exist_ok=True)

            zip_path = _create_zip(built_dir, identifier, zip_dir)
            typer.echo(f"Successfully created integration zip: {zip_path}")

    finally:
        # 7. Clean up Git Worktree
        if temp_worktree:
            typer.echo("Cleaning up temporary Git worktree...")
            _remove_git_worktree(temp_worktree, repo_root)


def _get_git_repo_root(path: pathlib.Path) -> pathlib.Path:
    """Get the Git repository root.

    Args:
        path: The path to check.

    Returns:
        pathlib.Path: The Git repository root path.

    Raises:
        RuntimeError: If the Git command fails.

    """
    git_path = shutil.which("git") or "git"
    try:
        output = (
            subprocess  # noqa: S603
            .check_output(
                [git_path, "rev-parse", "--show-toplevel"],
                cwd=path,
                stderr=subprocess.STDOUT,
            )
            .decode()
            .strip()
        )
        return pathlib.Path(output)
    except subprocess.CalledProcessError as e:
        msg = f"Failed to find Git repo root: {e.output.decode()}"
        raise RuntimeError(msg) from e


def _find_commit_sha(src_path: pathlib.Path, version: float) -> str:
    """Find the Git commit SHA for a specific version.

    Args:
        src_path: The source path of the integration.
        version: The version to find.

    Returns:
        str: The commit SHA.

    Raises:
        typer.BadParameter: If the version commit cannot be found.

    """
    rel_notes_path = src_path / constants.RELEASE_NOTES_FILE
    commit_sha = None
    git_path = shutil.which("git") or "git"

    if rel_notes_path.exists():
        cmd = [
            git_path,
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
        try:
            output = (
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
        except subprocess.CalledProcessError:
            pass

    # Try pyproject.toml if not found
    if not commit_sha:
        pyproject_path = src_path / constants.PROJECT_FILE
        if pyproject_path.exists():
            cmd = [
                git_path,
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
            try:
                output = (
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
            except subprocess.CalledProcessError:
                pass

    if not commit_sha:
        msg = f"Could not find Git commit for version {version} of integration '{src_path.name}'."
        raise typer.BadParameter(msg)

    return commit_sha


def _create_git_worktree(src_path: pathlib.Path, version: float) -> pathlib.Path:
    """Create a temporary Git worktree for a specific version.

    Args:
        src_path: The source path of the integration.
        version: The version to checkout.

    Returns:
        pathlib.Path: The path to the temporary worktree.

    Raises:
        RuntimeError: If the Git command fails.

    """
    repo_root = _get_git_repo_root(src_path)
    git_path = shutil.which("git") or "git"

    commit_sha = _find_commit_sha(src_path, version)

    # Create temp worktree
    temp_dir = pathlib.Path(tempfile.mkdtemp(prefix=f"mp_worktree_{src_path.name}_{version}_"))
    try:
        subprocess.run(  # noqa: S603
            [git_path, "worktree", "add", str(temp_dir), commit_sha],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        msg = f"Failed to create Git worktree: {e.stderr.decode()}"
        raise RuntimeError(msg) from e
    else:
        return temp_dir


def _remove_git_worktree(temp_dir: pathlib.Path, repo_root: pathlib.Path) -> None:
    """Remove a temporary Git worktree.

    Args:
        temp_dir: The path to the temporary worktree.
        repo_root: The Git repository root path.

    """
    git_path = shutil.which("git") or "git"
    try:
        subprocess.run(  # noqa: S603
            [git_path, "worktree", "remove", "--force", str(temp_dir)],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        typer.echo(f"Warning: Failed to remove Git worktree {temp_dir}: {e.stderr.decode()}", err=True)
        # Try manual cleanup if git fails
        shutil.rmtree(temp_dir, ignore_errors=True)


def _apply_beta_modifications(built_dir: pathlib.Path, old_id: str, beta_name: str, version: float | None) -> None:
    """Modify built integration files for a custom beta identifier.

    Args:
        built_dir: The built integration directory.
        old_id: The original identifier.
        beta_name: The new beta identifier.
        version: The version number.

    """
    new_id = beta_name

    # 1. Rename and update main .def file
    old_def_path = built_dir / constants.INTEGRATION_DEF_FILE.format(old_id)
    new_def_path = built_dir / constants.INTEGRATION_DEF_FILE.format(new_id)

    if old_def_path.exists():
        shutil.move(old_def_path, new_def_path)

        with new_def_path.open("r+", encoding="utf-8") as f:
            def_data = json.load(f)
            def_data["Identifier"] = new_id

            # Update Display Name
            ver_str = str(def_data.get("Version", version or ""))
            def_data["DisplayName"] = f"{_split_camel_case(new_id)} {ver_str}".strip()
            def_data["IsCustom"] = True

            # Update IntegrationProperties
            for prop in def_data.get("IntegrationProperties", []):
                prop["IntegrationIdentifier"] = new_id

            f.seek(0)
            json.dump(def_data, f, indent=4)
            f.truncate()

    # 2. Update component definitions
    component_dirs = [
        (constants.OUT_ACTIONS_META_DIR, False),
        (constants.OUT_CONNECTORS_META_DIR, True),  # Is Connector
        (constants.OUT_JOBS_META_DIR, False),
        (constants.OUT_WIDGETS_META_DIR, False),
    ]

    for dir_name, is_connector in component_dirs:
        meta_dir = built_dir / dir_name
        if meta_dir.exists():
            for file_path in meta_dir.glob("*"):
                if file_path.is_file():
                    _update_component_def(file_path, new_id, is_connector=is_connector)


def _update_component_def(file_path: pathlib.Path, new_id: str, *, is_connector: bool) -> None:
    """Update a single component definition file with the new identifier.

    Args:
        file_path: The path to the component definition file.
        new_id: The new identifier.
        is_connector: True if the component is a connector.

    """
    try:
        with file_path.open("r+", encoding="utf-8") as f:
            data = json.load(f)

            if "Integration" in data:
                data["Integration"] = new_id
            if "IntegrationIdentifier" in data:
                data["IntegrationIdentifier"] = new_id

            if is_connector and "Name" in data and not data["Name"].startswith(f"{new_id}-"):
                data["Name"] = f"{new_id}-{data['Name']}"

            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
    except (OSError, json.JSONDecodeError) as e:
        typer.echo(f"Warning: Failed to update component def {file_path}: {e}", err=True)


def _discover_components(
    built_dir: pathlib.Path,
) -> tuple[
    list[Choice],

    list[tuple[str, pathlib.Path, pathlib.Path | None]],
    list[tuple[str, pathlib.Path, pathlib.Path | None]],
]:
    """Discover components in the built directory.

    Args:
        built_dir: The built integration directory.

    Returns:
        tuple: (choices, ping_components, other_components)

    """
    components_map = {
        "Action": (constants.OUT_ACTIONS_META_DIR, constants.OUT_ACTION_SCRIPTS_DIR),
        "Connector": (constants.OUT_CONNECTORS_META_DIR, constants.OUT_CONNECTOR_SCRIPTS_DIR),
        "Job": (constants.OUT_JOBS_META_DIR, constants.OUT_JOB_SCRIPTS_DIR),
        "Widget": (constants.OUT_WIDGETS_META_DIR, constants.OUT_WIDGET_SCRIPTS_DIR),
    }

    choices: list[dict[str, Any]] = []
    ping_components: list[tuple[str, pathlib.Path, pathlib.Path | None]] = []
    other_components: list[tuple[str, pathlib.Path, pathlib.Path | None]] = []

    for comp_type, (meta_dir_name, script_dir_name) in components_map.items():
        meta_dir = built_dir / meta_dir_name
        script_dir = built_dir / script_dir_name

        if not meta_dir.exists():
            continue

        for meta_file in meta_dir.glob("*"):
            if not meta_file.is_file():
                continue

            name = meta_file.stem
            script_file = None
            if script_dir.exists():
                scripts = list(script_dir.glob(f"{name}.*"))
                if scripts:
                    script_file = scripts[0]

            if "Ping" in name:
                ping_components.append((comp_type, meta_file, script_file))
            else:
                other_components.append((comp_type, meta_file, script_file))
                choices.append(Choice(title=f"[{comp_type}] {name}", value=(meta_file, script_file), checked=True))

    return choices, ping_components, other_components


def _delete_unselected_components(
    selected_files: set[pathlib.Path],
    other_components: list[tuple[str, pathlib.Path, pathlib.Path | None]],
) -> None:
    """Delete unselected component files.

    Args:
        selected_files: Set of files to keep.
        other_components: List of all other components.

    """
    for _comp_type, meta, script in other_components:
        if meta not in selected_files:
            meta.unlink(missing_ok=True)
            if script and script.exists():
                script.unlink(missing_ok=True)
            typer.echo(f"Removed unselected component: {meta.stem}")


def _interactive_component_selection(built_dir: pathlib.Path) -> None:
    """Prompt user to select components to include in the ZIP.

    Args:
        built_dir: The built integration directory.

    """
    choices, ping_components, other_components = _discover_components(built_dir)

    if not choices and not ping_components:
        return

    if not choices:
        return

    selected_values = questionary.checkbox(
        "Select Actions/Connectors/Jobs/Widgets to include (Hit <Enter> to select all):",
        choices=choices,
    ).ask()

    if selected_values is None or len(selected_values) == 0:
        typer.echo("No components selected or cancelled. Including all components.")
        return

    selected_files = set()
    for meta, script in selected_values:
        selected_files.add(meta)
        if script:
            selected_files.add(script)

    for _comp_type, meta, script in ping_components:
        selected_files.add(meta)
        if script:
            selected_files.add(script)

    _delete_unselected_components(selected_files, other_components)


def _create_zip(built_dir: pathlib.Path, identifier: str, zip_dir: pathlib.Path) -> pathlib.Path:
    """Create a ZIP archive of the built integration.

    Args:
        built_dir: The built integration directory.
        identifier: The integration identifier.
        zip_dir: The directory to save the ZIP file.

    Returns:
        pathlib.Path: The path to the created ZIP file.

    """
    date = datetime.datetime.now(datetime.UTC).strftime("%-d%b%y")
    zip_name = f"{identifier}{date}.zip"
    zip_path = zip_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in built_dir.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, arcname=file_path.relative_to(built_dir))

    return zip_path


def _split_camel_case(text: str) -> str:
    """Split CamelCase string with spaces.

    Args:
        text: The string to split.

    Returns:
        str: The split string.

    """
    return re.sub(r"(?<!^)(?=[A-Z])", " ", text)


def _is_tty() -> bool:
    """Check if the current process is running in a TTY.

    Returns:
        bool: True if running in a TTY, False otherwise.

    """
    return sys.stdout.isatty()
