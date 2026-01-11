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
from mp.dev_env.commands.playbooks import utils
from mp.dev_env.commands.pull import pull_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

if TYPE_CHECKING:
    from mp.dev_env.api import BackendAPI


@pull_app.command(name="playbook")
@track_command
def pull_playbook(
    playbook: Annotated[str, typer.Argument(help="Playbook to pull and deconstruct.")],
    dest: Annotated[
        Path | None,
        typer.Option(
            "--dest", help="Destination folder. the 'download' directory in content-hub repo."
        ),
    ] = None,
    *,
    include_blocks: Annotated[
        bool,
        typer.Option(help="Pull all playbook dependent blocks."),
    ] = False,
    keep_zip: Annotated[
        bool,
        typer.Option(help="Keep the zip file after pulling."),
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
    if dest is None:
        dest = mp.core.file_utils.common.utils.create_or_get_download_dir()

    try:
        zip_path = _pull_zip_from_soar(playbook, dest)
        _deconstruct_playbook(zip_path, dest, playbook)

        if include_blocks:
            _deconstruct_blocks(zip_path, dest, playbook)

        if not keep_zip:
            zip_path.unlink()

        rich.print(f"[green]✅ Playbook {playbook} pulled successfully.[/green]")

    except Exception as e:
        error_message = f"Download failed for {playbook}: {e}"
        rich.print(f"[red]{error_message}[/red]")
        raise typer.Exit(1) from e


def _pull_zip_from_soar(playbook: str, dest: Path) -> Path:
    config = load_dev_env_config()
    backend_api: BackendAPI = get_backend_api(config)
    installed_playbook: list[dict[str, Any]] = backend_api.get_playbooks_list_from_platform()
    playbook_identifier = utils.find_playbook_identifier(playbook, installed_playbook)
    return backend_api.download_playbook(playbook, playbook_identifier, dest)


def _deconstruct_playbook(zip_path: Path, dest: Path, playbook: str) -> None:
    playbook_file: list[Path] = utils.unzip_playbooks(zip_path, dest, include_playbook=playbook)
    utils.deconstruct_playbook(playbook_file[0])


def _deconstruct_blocks(zip_path: Path, dest: Path, playbook: str) -> None:
    all_built_files: list[Path] = utils.unzip_playbooks(zip_path, dest, "", playbook)
    for built_file in all_built_files:
        utils.deconstruct_playbook(built_file)
