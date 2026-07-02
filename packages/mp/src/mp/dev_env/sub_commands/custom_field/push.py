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

import contextlib
import logging
from pathlib import Path
from typing import Annotated

import typer

import mp.core.file_utils
from mp.dev_env.sub_commands.push import push_app
from mp.dev_env.utils import find_entity_identifier, get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


@push_app.command(name="custom-field")
@track_command
def push_custom_field(  # noqa: C901, PLR0915
    field_file_or_name: Annotated[str, typer.Argument(help="The custom field YAML file path or name to push.")],
) -> None:
    """Push a custom field to the SOAR environment.

    Raises:
        typer.Exit: If the push fails.

    """
    field_file = Path(field_file_or_name)
    if not field_file.is_file():
        # Try resolving by name in the default custom fields directory
        custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()
        safe_name = field_file_or_name.replace("/", "_").replace(" ", "_")
        candidate_file = custom_fields_root / f"{safe_name}.yaml"
        if candidate_file.is_file():
            field_file = candidate_file
        else:
            logger.error("Custom field file not found at '%s' or '%s'", field_file_or_name, candidate_file)
            raise typer.Exit(1)

    logger.info("Loading custom field YAML...")
    try:
        field_data = mp.core.file_utils.load_yaml_file(field_file)
    except Exception as e:
        logger.exception("Failed to parse custom field YAML")
        raise typer.Exit(1) from e

    if not isinstance(field_data, dict):
        logger.error("Custom field data must be a dictionary.")
        raise typer.Exit(1)

    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Checking if custom field exists on server...")
    try:
        installed_fields = backend_api.list_custom_fields()
    except Exception as e:
        logger.exception("Failed to fetch installed custom fields")
        raise typer.Exit(1) from e

    field_name = field_data.get("name")
    if not field_name:
        logger.error("Custom field data is missing a 'name' field.")
        raise typer.Exit(1)

    existing_id = None
    with contextlib.suppress(typer.Exit):
        existing_id = find_entity_identifier(field_name, installed_fields, "Custom Field")

    if existing_id is not None:
        logger.info("Updating existing custom field (ID: %s)...", existing_id)
        # Avoid trying to mutate id in the patch payload unless strictly required,
        # but passing it doesn't usually hurt.
        try:
            numeric_id = int(existing_id)
            backend_api.update_custom_field(numeric_id, field_data)
        except (ValueError, TypeError) as e:
            logger.error("Invalid existing ID '%s': Must be a numeric value.", existing_id)  # noqa: TRY400
            raise typer.Exit(1) from e
        except Exception as e:
            logger.exception("Failed to update custom field '%s'", field_name)
            raise typer.Exit(1) from e
    else:
        logger.info("Creating new custom field...")
        try:
            backend_api.create_custom_field(field_data)
        except Exception as e:
            logger.exception("Failed to create custom field '%s'", field_name)
            raise typer.Exit(1) from e

    logger.info("Custom field '%s' pushed successfully.", field_name)
