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
from typing import Annotated

import rich
import typer
from rich.markup import escape

import mp.core.file_utils
from mp.dev_env.commands.integrations import utils
from mp.dev_env.commands.pull import pull_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command


@pull_app.command(name="integration")
@track_command
def pull_integration(
    integration: Annotated[
        str,
        typer.Argument(help="Integration to pull and deconstruct."),
    ],
    dst: Annotated[
        Path | None,
        typer.Option(help="Destination folder, where the content will be pulled to."),
    ] = None,
    *,
    keep_zip: Annotated[
        bool,
        typer.Option("--keep-zip", help="Keep the integration zip file after pulling."),
    ] = False,
) -> None:
    """Pull and deconstruct an integration from the dev environment.

    Args:
        integration: The integration to build and deploy.
        dst: Destination folder.
        keep_zip: Keep the integration zip file after pulling.

    Raises:
        typer.Exit: If the integration pull fails.

    """
    zip_path: Path | None = None
    if dst is None:
        dst = mp.core.file_utils.common.utils.create_or_get_download_dir()
    else:
        dst.mkdir(parents=True, exist_ok=True)

    try:
        zip_path = _pull_integration_zip_from_soar(integration, dst)
        deconstruct_integration: Path = _deconstruct_integration(zip_path, dst)
        rich.print(
            f"[green]✅ Integration {integration} pulled successfully to "
            f"{deconstruct_integration}.[/green]"
        )

    except Exception as e:
        error_message = f"Pull failed for {integration}: {escape(str(e))}"
        rich.print(error_message)
        raise typer.Exit(1) from e

    finally:
        if not keep_zip and zip_path is not None:
            zip_path.unlink()


def _pull_integration_zip_from_soar(integration: str, dst: Path) -> Path:
    config = load_dev_env_config()
    backend_api = get_backend_api(config)
    resp = backend_api.download_integration(integration)
    return utils.save_integration_as_zip(integration, resp, dst)


def _deconstruct_integration(zip_path: Path, dst: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)
        unzipped_integration_path = utils.unzip_integration(zip_path, temp_path)
        return utils.deconstruct_integration(unzipped_integration_path, dst)
