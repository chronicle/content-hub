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
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


@push_app.command(name="custom-field")
@track_command
def push_custom_field(  # noqa: C901, PLR0915
    field_file_or_name: Annotated[
        str | None, typer.Argument(help="The custom field YAML file path or name to push.")
    ] = None,
    *,
    push_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Push all custom fields from the local directory to the environment.",
        ),
    ] = False,
    allow_create: Annotated[
        bool,
        typer.Option(
            "--allow-create",
            help="Allow creating new custom fields if they do not exist on the platform.",
        ),
    ] = False,
) -> None:
    """Push custom field(s) to the SOAR environment.

    Raises:
        typer.Exit: If the push fails.

    """
    if field_file_or_name is None and not push_all:
        logger.error("You must specify either a custom field name/file, or use the --all flag.")
        raise typer.Exit(1)

    custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()

    if push_all:
        logger.info("Pushing all custom fields from '%s'...", custom_fields_root)
        if not custom_fields_root.exists() or not custom_fields_root.is_dir():
            logger.error("Custom fields directory not found.")
            raise typer.Exit(1)
        
        yaml_files = list(custom_fields_root.glob("*.yaml")) + list(custom_fields_root.glob("*.yml"))
        if not yaml_files:
            logger.info("No custom field files found to push.")
            return

        for f in yaml_files:
            _push_single_custom_field(f, allow_create)
        
        logger.info("Successfully finished pushing all custom fields.")
        return

    # Standard single push
    files_to_push = []
    field_file = Path(field_file_or_name)
    if field_file.is_file():
        files_to_push.append(field_file)
    else:
        # Try resolving by name in the default custom fields directory
        safe_name = field_file_or_name.replace("/", "_").replace(" ", "_")
        candidate_file = custom_fields_root / f"{safe_name}.yaml"
        if candidate_file.is_file():
            files_to_push.append(candidate_file)
        else:
            # Look for suffix matching (e.g. name_scopes.yaml)
            matching_files = [
                f for f in custom_fields_root.iterdir()
                if f.is_file() and f.suffix in {".yaml", ".yml"} and f.name.startswith(f"{safe_name}_")
            ]
            if matching_files:
                files_to_push.extend(matching_files)
            else:
                logger.error("Custom field file not found at '%s' or '%s'", field_file_or_name, candidate_file)
                raise typer.Exit(1)

    if len(files_to_push) > 1:
        logger.info("Found %d files matching '%s'. Pushing all of them...", len(files_to_push), field_file_or_name)

    for f in files_to_push:
        _push_single_custom_field(f, allow_create)


def _push_single_custom_field(field_file: Path, allow_create: bool) -> None:
    logger.info("Loading custom field YAML from '%s'...", field_file)
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

    field_name = field_data.get("displayName")
    if not field_name:
        logger.error("Custom field data is missing a 'displayName' field.")
        raise typer.Exit(1)

    existing_id = None
    local_scopes = field_data.get("scopes")
    for field in installed_fields:
        if str(field.get("displayName")).lower() == field_name.lower():
            if local_scopes is not None:
                server_scopes = field.get("scopes")

                def normalize_scopes(val) -> set[str]:
                    if not val:
                        return set()
                    if isinstance(val, list):
                        return {str(x).strip().lower() for x in val}
                    return {x.strip().lower() for x in str(val).split(",") if x.strip()}

                if normalize_scopes(local_scopes) != normalize_scopes(server_scopes):
                    continue

            existing_id = field.get("id")
            break

    if existing_id is not None:
        logger.info("Updating existing custom field (ID: %s)...", existing_id)
        try:
            numeric_id = int(existing_id)
            # Align the casing of displayName to match the server's to avoid validation errors (name change is forbidden)
            server_field = next((f for f in installed_fields if f.get("id") == numeric_id), None)
            if server_field and server_field.get("displayName"):
                field_data["displayName"] = server_field["displayName"]

            # Update the payload with the target environment's ID and name
            field_data["id"] = numeric_id
            field_data["name"] = f"projects//locations//instances//customFields/{numeric_id}"
            
            backend_api.update_custom_field(numeric_id, field_data)
        except (ValueError, TypeError) as e:
            logger.error("Invalid existing ID '%s': Must be a numeric value.", existing_id)  # noqa: TRY400
            raise typer.Exit(1) from e
        except Exception as e:
            logger.exception("Failed to update custom field '%s'", field_name)
            raise typer.Exit(1) from e
    else:
        if not allow_create:
            logger.error("Custom field '%s' not found on the platform. Skipping because --allow-create was not specified.", field_name)
            raise typer.Exit(1)
            
        logger.info("Creating new custom field...")
        try:
            backend_api.create_custom_field(field_data)
        except Exception as e:
            logger.exception("Failed to create custom field '%s'", field_name)
            raise typer.Exit(1) from e

    logger.info("Custom field '%s' pushed successfully.", field_name)
