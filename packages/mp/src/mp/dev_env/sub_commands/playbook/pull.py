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

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import rich
import typer

import mp.core.file_utils
from mp.dev_env.sub_commands.playbook import utils
from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

if TYPE_CHECKING:
    from mp.dev_env.api import BackendAPI


@pull_app.command(name="playbook")
@track_command
def pull_playbook(
    playbook: Annotated[str, typer.Argument(help="Playbook to pull and deconstruct.")],
    dst: Annotated[
        Path | None,
        typer.Option(help="Destination folder. the 'download' directory in content-hub repo."),
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
    """Pull and deconstruct a playbook from the SOAR environment.

    Args:
        playbook: The playbook to pull.
        dst: Destination folder.
        include_blocks: Pull all playbook-dependent blocks.
        keep_zip: Keep the zip file after pulling.

    Raises:
        typer.Exit: If the playbook is not found.

    """
    zip_path: Path | None = None
    if dst is None:
        dst = mp.core.file_utils.common.utils.create_or_get_download_dir()
    else:
        dst.mkdir(parents=True, exist_ok=True)

    try:
        zip_path = _pull_playbook_zip_from_soar(playbook, dst)
        _deconstruct_playbook(zip_path, dst, playbook)

        if include_blocks:
            _deconstruct_blocks(zip_path, dst, playbook)

        rich.print(f"[green]✅ Playbook {playbook} pulled successfully.[/green]")

    except Exception as e:
        error_message = f"Download failed for {playbook}: {e}"
        rich.print(f"[red]{error_message}[/red]")
        raise typer.Exit(1) from e

    finally:
        if not keep_zip and zip_path is not None:
            zip_path.unlink()


def _pull_playbook_zip_from_soar(playbook: str, dst: Path) -> Path:
    config = load_dev_env_config()
    backend_api: BackendAPI = get_backend_api(config)
    installed_playbook: list[dict[str, Any]] = backend_api.list_playbooks()
    playbook_identifier = utils.find_playbook_identifier(playbook, installed_playbook)
    data_json: dict[str, Any] = backend_api.download_playbook(playbook_identifier)
    return utils.save_playbook_as_zip(playbook, data_json, dst)


def _deconstruct_playbook(zip_path: Path, dst: Path, playbook: str) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)
        playbook_file: list[Path] = utils.unzip_playbooks(
            zip_path, temp_path, include_playbook=playbook
        )
        utils.deconstruct_playbook(playbook_file[0], dst)


def _deconstruct_blocks(zip_path: Path, dst: Path, playbook: str) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)
        all_built_files: list[Path] = utils.unzip_playbooks(zip_path, temp_path, "", playbook)
        for built_file in all_built_files:
            utils.deconstruct_playbook(built_file, dst)
