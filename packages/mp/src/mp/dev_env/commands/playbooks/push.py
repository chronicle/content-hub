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
from typing import TYPE_CHECKING, Annotated

import rich
import typer

import mp.core.utils
from mp.dev_env.commands.playbooks import utils
from mp.dev_env.commands.push import push_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

if TYPE_CHECKING:
    from typing import Any

    from mp.dev_env.api import BackendAPI


@push_app.command(name="playbook")
@track_command
def push_playbook(
    playbook: Annotated[
        str,
        typer.Argument(help="Playbook to build and push."),
    ],
    src: Annotated[
        Path | None,
        typer.Option(help="Source folder, where the content will be pushed from."),
    ] = None,
    *,
    include_blocks: Annotated[
        bool,
        typer.Option(help="Push all playbook dependent blocks."),
    ] = False,
    keep_zip: Annotated[
        bool,
        typer.Option("--keep-zip", help="Keep the integration zip file after pulling."),
    ] = False,
) -> None:
    """Build and push playbook to the SOAR environment.

    Args:
        playbook: The playbook to build and push.
        src: Source folder, where the content will be pushed from.
        include_blocks: Push all playbook-dependent blocks.
        keep_zip: Keep the integration zip file after pulling.

    Raises:
        typer.Exit: If the upload fails.


    """
    contents_to_push: set[str] = {playbook}
    if include_blocks:
        contents_to_push.update(_get_dependent_blocks_names(playbook, src=src))

    utils.build_playbook(contents_to_push, src=src)

    zip_path: Path = _zip_playbooks(playbook, contents_to_push)

    try:
        result = _push_playbook_zip_to_soar(zip_path)
        rich.print(f"Upload result for {zip_path.stem}: {result}")
        rich.print(f"[green]✅ Playbook {zip_path.stem} pushed successfully.[/green]")

    except Exception as e:
        error_message = f"Upload failed for {zip_path.stem}: {e}"
        rich.print(f"[red]{error_message}[/red]")
        raise typer.Exit(1) from e

    finally:
        if not keep_zip:
            zip_path.unlink()


def _get_dependent_blocks_names(playbook: str, src: Path | None = None) -> set[str]:
    playbook_path: Path = utils.get_playbook_path_by_name(playbook, src=src)
    block_ids: set[str] = mp.core.utils.get_playbook_dependent_blocks_ids(playbook_path)
    return utils.get_block_names_by_ids(block_ids, src=src)


def _zip_playbooks(main_playbook: str, content_names: set[str]) -> Path:
    built_paths: list[Path] = [utils.get_built_playbook_path(p) for p in content_names]
    zip_path: Path = utils.zip_built_playbook(main_playbook, built_paths)
    rich.print(f"Zipped built playbooks at {zip_path}")
    return zip_path


def _push_playbook_zip_to_soar(zip_path: Path) -> dict[str, Any]:
    config = load_dev_env_config()
    backend_api: BackendAPI = get_backend_api(config)
    return backend_api.upload_playbook(zip_path)
