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

import rich
import typer

from mp.telemetry import track_command

from .sub_commands.integration.push import push_integration
from .sub_commands.login import login_app
from .sub_commands.pull import pull_app
from .sub_commands.push import push_app

dev_env_app: typer.Typer = typer.Typer(
    name="dev-env",
    help="Commands for interacting with the SecOps environment.",
)

dev_env_app.add_typer(login_app)
dev_env_app.add_typer(push_app)
dev_env_app.add_typer(pull_app)


@dev_env_app.command(
    deprecated=True,
    help="Deprecated. Please use 'dev-env push integration' instead.",
)
@track_command
def deploy(
    integration: str = typer.Argument(help="Integration to build and deploy."),
    *,
    is_staging: bool = False,
) -> None:
    """Deprecated."""  # noqa: D401
    rich.print("[yellow]Note: 'deploy' is deprecated. Use 'push integration' instead.[/yellow]")
    push_integration(integration, is_staging=is_staging)
