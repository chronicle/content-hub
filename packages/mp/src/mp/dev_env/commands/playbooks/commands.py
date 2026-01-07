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

from typing import TYPE_CHECKING, Annotated

import rich
import typer

import mp.core.utils
from mp.dev_env.commands.playbooks import utils
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
    custom: Annotated[
        bool,
        typer.Option(help="Push playbook from the custom repository."),
    ] = False,
    include_blocks: Annotated[
        bool,
        typer.Option(help="Push all playbook dependent blocks."),
    ] = False,
) -> None:
    """Build and deploy playbook to the dev environment.

    Args:
        playbook: The integration to build and deploy.
        custom: Add this option to push playbook from the custom repository.
        include_blocks: Push all playbook-dependent blocks.

    Raises:
        typer.Exit: If the integration is not found.

    """
    config = load_dev_env_config()
    backend_api: BackendAPI = get_backend_api(config)

    contents_to_push = {playbook}
    if include_blocks:
        playbook_path = utils.get_playbook_path_by_name(playbook, custom=custom)
        block_ids = mp.core.utils.get_playbook_dependent_blocks_ids(playbook_path)
        contents_to_push.update(utils.get_blocks_by_id(block_ids, custom=custom))

    for content in contents_to_push:
        utils.build_playbook(content)

    built_paths = [utils.find_built_playbook(p, custom=custom) for p in contents_to_push]
    zip_paths = [utils.zip_built_playbook(p) for p in built_paths]
    rich.print(f"Zipped built playbooks at {zip_paths}")

    errors = []
    for zip_path in zip_paths:
        try:
            result = backend_api.upload_playbook(zip_path)
            rich.print(f"Upload result for {zip_path.stem}: {result}")
            rich.print(f"[green]✅ Playbook {zip_path.stem} deployed successfully.[/green]")

        except Exception as e:  # noqa: BLE001
            error_message = f"Upload failed for {zip_path.stem}: {e}"
            rich.print(f"[red]{error_message}[/red]")
            errors.append(error_message)

    if errors:
        raise typer.Exit(1)
