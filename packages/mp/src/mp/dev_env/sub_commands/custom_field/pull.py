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
from pathlib import Path
from typing import Annotated

import typer

import mp.core.file_utils
import mp.dev_env.api
from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.sub_commands.utils import get_backend_api_clean as get_backend_api
from mp.dev_env.utils import load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


def _normalize_scopes(val: str | list | None) -> set[str]:
    if not val:
        return set()
    if isinstance(val, list):
        return {str(x).strip().lower() for x in val}
    return {x.strip().lower() for x in str(val).split(",") if x.strip()}


@pull_app.command(name="custom-field")
@track_command
def pull_custom_field(  # noqa: C901, PLR0912, PLR0914, PLR0915
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
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to fetch installed custom fields: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None

    if list_only:
        logger.info("Available Custom Fields:")
        for field in installed_fields:
            display_name = field.get("displayName") or field.get("name", "Unknown")
            scopes_val = field.get("scopes")
            if isinstance(scopes_val, list):
                scopes_str = ", ".join(str(x) for x in scopes_val)
            elif scopes_val:
                scopes_str = str(scopes_val)
            else:
                scopes_str = "None"
            logger.info("  - DisplayName: '%s' (Scopes: %s)", display_name, scopes_str)
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
            except Exception as e:  # noqa: BLE001
                logger.error("Skipping custom field '%s' due to an error: %s", field_name, e)  # noqa: TRY400

        logger.info("Successfully finished pulling all custom fields.")
        return

    # Standard single pull
    if field_name_or_id is None:
        logger.error("field_name_or_id is required if not pulling or listing all")
        raise typer.Exit(1)

    target_name = field_name_or_id
    target_scopes = None

    # Check if the input is a local file path
    input_path = Path(field_name_or_id)
    if input_path.is_file():
        try:
            local_data = mp.core.file_utils.load_yaml_file(input_path)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load local file '%s' to extract displayName.", field_name_or_id)
        else:
            if isinstance(local_data, dict):
                target_name = local_data.get("displayName") or target_name
                target_scopes = local_data.get("scopes")
                if not dst:
                    dst = input_path

    matching_fields = []
    try:
        numeric_id = int(field_name_or_id)
        for field in installed_fields:
            if field.get("id") == numeric_id:
                matching_fields.append(field)
                break
    except ValueError:
        for field in installed_fields:
            if str(field.get("displayName")).lower() == target_name.lower():
                if target_scopes is not None:
                    server_scopes = field.get("scopes")

                    if _normalize_scopes(target_scopes) != _normalize_scopes(server_scopes):
                        continue
                matching_fields.append(field)

    if not matching_fields:
        logger.error("Custom Field '%s' not found in installed entities in SOAR platform.", field_name_or_id)
        raise typer.Exit(1)

    if len(matching_fields) > 1:
        if dst is not None and dst.suffix in {".yaml", ".yml"}:
            logger.error(
                "Multiple custom fields found matching '%s', but a single destination file was specified. "
                "Please specify a directory path for --custom, or pull by ID.",
                field_name_or_id,
            )
            raise typer.Exit(1)
        logger.info(
            "Found %d custom fields matching '%s'. Pulling all of them...", len(matching_fields), field_name_or_id
        )

    for field in matching_fields:
        field_id = field.get("id")
        if field_id is not None:
            _download_and_save_custom_field(backend_api, field_id, dst)


def _download_and_save_custom_field(  # noqa: C901, PLR0912, PLR0915
    backend_api: mp.dev_env.api.BackendAPI, field_id: int | str, dst: Path | None
) -> None:
    logger.info("Downloading custom field (ID: %s)...", field_id)
    try:
        numeric_id = int(field_id)
        field_data = backend_api.download_custom_field(numeric_id)
    except (ValueError, TypeError):
        logger.error("Invalid field ID '%s': Must be a numeric value.", field_id)  # noqa: TRY400
        raise typer.Exit(1) from None
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to download custom field '%s': %s", field_id, e)  # noqa: TRY400
        raise typer.Exit(1) from None

    # Determine destination path
    raw_name = str(field_data.get("displayName") or field_data.get("name") or field_id)
    safe_name = raw_name.replace("/", "_").replace(" ", "_")
    scopes_val = field_data.get("scopes")
    if scopes_val:
        def normalize_scopes_for_filename(val: str | list) -> str:
            if isinstance(val, list):
                parts = [str(x).strip().lower() for x in val]
            else:
                parts = [x.strip().lower() for x in str(val).split(",") if x.strip()]
            return "_".join(sorted(parts))

        scopes_suffix = normalize_scopes_for_filename(scopes_val)
        file_name = f"{safe_name}_{scopes_suffix}.yaml"
    else:
        file_name = f"{safe_name}.yaml"

    if dst is None:
        custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()

        scopes = _normalize_scopes(scopes_val)
        if len(scopes) > 1:
            subdir = "shared"
        elif len(scopes) == 1:
            if "case" in scopes:
                subdir = "case"
            elif "alert" in scopes:
                subdir = "alert"
            else:
                subdir = "shared"
        else:
            subdir = "shared"

        actual_dst = custom_fields_root / subdir / file_name
    elif dst.is_dir() or dst.suffix not in {".yaml", ".yml"}:
        dst.mkdir(parents=True, exist_ok=True)
        actual_dst = dst / file_name
    else:
        actual_dst = dst

    logger.info("Saving custom field to %s...", actual_dst)
    # Clean up environment-specific fields to keep the files environment-agnostic
    field_data.pop("id", None)
    field_data.pop("name", None)
    try:
        actual_dst.parent.mkdir(parents=True, exist_ok=True)
        mp.core.file_utils.save_yaml(field_data, actual_dst)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to save custom field to '%s': %s", actual_dst, e)  # noqa: TRY400
        raise typer.Exit(1) from None
