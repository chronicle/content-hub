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

from mp.dev_env.commands.playbooks import utils
from mp.dev_env.commands.push import push_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

if TYPE_CHECKING:
    from pathlib import Path

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

    Raises:
        typer.Exit: If the integration is not found.

    """
    config = load_dev_env_config()
    utils.build_playbook(playbook)
    built_playbook: Path = utils.find_built_playbook(playbook, custom=custom)
    zip_path: Path = utils.zip_built_playbook(built_playbook)
    rich.print(f"Zipped built playbook at {zip_path}")

    backend_api: BackendAPI = get_backend_api(config)
    try:
        result = backend_api.upload_playbook(zip_path)
        rich.print(f"Upload result: {result}")
        rich.print("[green]✅ Playbook deployed successfully.[/green]")
    except Exception as e:
        rich.print(f"[red]Upload failed: {e}[/red]")
        raise typer.Exit(1) from e
