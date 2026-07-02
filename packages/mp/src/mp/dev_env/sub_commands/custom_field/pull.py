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

import logging
from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

import mp.core.file_utils
import mp.dev_env.api
from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.utils import find_entity_identifier, get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


@pull_app.command(name="custom-field")
@track_command
def pull_custom_field(  # noqa: C901
    field_name_or_id: Annotated[
        str | None, typer.Argument(help="The custom field name or identifier to pull.")
    ] = None,
    dst: Annotated[
        Path | None,
        typer.Option(
            "--custom",
            help="Destination file. Defaults to 'content/custom_fields/<name>.yaml'.",
        ),
    ] = None,
    *,
    pull_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Pull all custom fields from the environment.",
        ),
    ] = False,
    list_only: Annotated[
        bool,
        typer.Option(
            "--list",
            help="List all custom fields available in the environment without pulling.",
        ),
    ] = False,
) -> None:
    """Pull custom fields from the SOAR environment.

    Raises:
        typer.Exit: If the pull fails or invalid arguments are provided.

    """
    if field_name_or_id is None and not pull_all and not list_only:
        logger.error("You must specify either a custom field name/identifier, or use the --all or --list flags.")
        raise typer.Exit(1)

    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Fetching installed custom fields...")
    try:
        installed_fields = backend_api.list_custom_fields()
    except Exception as e:
        logger.exception("Failed to fetch installed custom fields")
        raise typer.Exit(1) from e

    if list_only:
        logger.info("Available Custom Fields:")
        for field in installed_fields:
            logger.info("  - Name: '%s' (ID: %s)", field.get("name", "Unknown"), field.get("id", "Unknown"))
        return

    if pull_all:
        logger.info("Pulling all %d custom fields...", len(installed_fields))
        for field in installed_fields:
            field_id = field.get("id")
            field_name = field.get("name") or field_id
            if not field_id:
                continue

            try:
                _download_and_save_custom_field(backend_api, field_id, dst)
            except Exception:
                logger.exception("Skipping custom field '%s' due to an error.", field_name)

        logger.info("Successfully finished pulling all custom fields.")
        return

    # Standard single pull
    if field_name_or_id is None:
        logger.error("field_name_or_id is required if not pulling or listing all")
        raise typer.Exit(1)
    field_id = find_entity_identifier(field_name_or_id, installed_fields, "Custom Field")
    if field_id is None:
        raise typer.Exit(1)
    _download_and_save_custom_field(backend_api, field_id, dst)


def _download_and_save_custom_field(
    backend_api: mp.dev_env.api.BackendAPI, field_id: int | str, dst: Path | None
) -> None:
    logger.info("Downloading custom field (ID: %s)...", field_id)
    try:
        numeric_id = int(field_id)
        field_data = backend_api.download_custom_field(numeric_id)
    except (ValueError, TypeError) as e:
        logger.error("Invalid field ID '%s': Must be a numeric value.", field_id)  # noqa: TRY400
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Failed to download custom field '%s'", field_id)
        raise typer.Exit(1) from e

    # Determine destination path
    raw_name = str(field_data.get("displayName") or field_data.get("name") or field_id)
    safe_name = raw_name.replace("/", "_").replace(" ", "_")
    file_name = f"{safe_name}.yaml"

    if dst is None:
        custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()
        actual_dst = custom_fields_root / file_name
    elif dst.is_dir() or dst.suffix not in {".yaml", ".yml"}:
        dst.mkdir(parents=True, exist_ok=True)
        actual_dst = dst / file_name
    else:
        actual_dst = dst

    logger.info("Saving custom field to %s...", actual_dst)
    try:
        mp.core.file_utils.save_yaml(field_data, actual_dst)
    except Exception as e:
        logger.exception("Failed to save custom field to '%s'", actual_dst)
        raise typer.Exit(1) from e
