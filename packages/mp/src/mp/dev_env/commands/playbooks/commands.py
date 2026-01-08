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

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Any

import rich
import typer

import mp.core.file_utils
import mp.core.utils
from mp.dev_env.commands.playbooks import utils
from mp.dev_env.commands.pull import pull_app
from mp.dev_env.commands.push import push_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

if TYPE_CHECKING:
    from mp.dev_env.api import BackendAPI


@push_app.command(name="playbook")
@track_command
def push_playbook(
    playbook: str = typer.Argument(help="Playbook to build and push."),
    *,
    include_blocks: Annotated[
        bool,
        typer.Option(help="Push all playbook dependent blocks."),
    ] = False,
) -> None:
    """Build and deploy playbook to the SOAR environment.

    Args:
        playbook: The playbook to build and push.
        include_blocks: Push all playbook-dependent blocks.

    Raises:
        typer.Exit: If the playbook is not found.

    """
    config = load_dev_env_config()
    backend_api: BackendAPI = get_backend_api(config)

    contents_to_push: set[str] = {playbook}
    if include_blocks:
        playbook_path: Path = utils.get_playbook_path_by_name(playbook)
        block_ids: set[str] = mp.core.utils.get_playbook_dependent_blocks_ids(playbook_path)
        contents_to_push.update(utils.get_block_names_by_ids(block_ids))

    utils.build_playbook(contents_to_push)

    built_paths: list[Path] = [utils.get_built_playbook_path(p) for p in contents_to_push]
    zip_path: Path = utils.zip_built_playbook(playbook, built_paths)
    rich.print(f"Zipped built playbooks at {zip_path}")

    try:
        result = backend_api.upload_playbook(zip_path)
        zip_path.unlink()
        rich.print(f"Upload result for {zip_path.stem}: {result}")
        rich.print(f"[green]✅ Playbook {zip_path.stem} deployed successfully.[/green]")

    except Exception as e:
        error_message = f"Upload failed for {zip_path.stem}: {e}"
        rich.print(f"[red]{error_message}[/red]")
        raise typer.Exit(1) from e


@pull_app.command(name="playbook")
@track_command
def pull_playbook(
    playbook: str = typer.Argument(help="Playbook to pull."),
    dest: Annotated[
        Path | None,
        typer.Option("--dest", help="Destination folder. Defaults to your desktop path."),
    ] = None,
    *,
    include_blocks: Annotated[
        bool,
        typer.Option(help="Push all playbook dependent blocks."),
    ] = False,
    keep_zip: Annotated[
        bool,
        typer.Option(help="keep the zip file after pulling."),
    ] = False,
) -> None:
    """Pull a playbook from the SOAR environment.

    Args:
        playbook: The playbook to pull.
        dest: Destination folder.
        include_blocks: Pull all playbook-dependent blocks.
        keep_zip: Keep the zip file after pulling.

    Raises:
        typer.Exit: If the playbook is not found.

    """
    config = load_dev_env_config()
    backend_api: BackendAPI = get_backend_api(config)

    if not dest:
        dest = mp.core.file_utils.common.utils.create_or_get_download_dir()

    installed_playbook: list[dict[str, Any]] = backend_api.get_playbooks_list_from_platform()
    playbook_identifier = utils.find_playbook_identifier(playbook, installed_playbook)
    try:
        zip_path = backend_api.download_playbook(playbook, playbook_identifier, dest)
        built_playbook: list[Path] = utils.unzip_playbooks(zip_path, dest, playbook)
        utils.deconstruct_playbook(built_playbook[0])

        if include_blocks:
            built_blocks: list[Path] = utils.unzip_playbooks(zip_path, dest, "", playbook)
            for block in built_blocks:
                utils.deconstruct_playbook(block)

        if not keep_zip:
            zip_path.unlink()

        rich.print(f"[green]✅ Playbook {playbook} pulled successfully.[/green]")

    except Exception as e:
        error_message = f"Download failed for {playbook}: {e}"
        rich.print(f"[red]{error_message}[/red]")
        raise typer.Exit(1) from e
