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


def _normalize_scopes(val: str | list | set | None) -> set[str]:
    if not val:
        return set()
    if isinstance(val, (list, set)):
        return {str(x).strip().lower() for x in val}
    return {x.strip().lower() for x in val.split(",") if x.strip()}


def matches_scope_filter(
    scope_filter: str | set[str] | list[str] | None,
    entity_scopes: str | list | set | None,
) -> bool:
    """Check if entity_scopes matches the scope_filter.

    Rules:
    - If scope_filter is None or empty, returns True.
    - If scope_filter contains comma-separated values or a set/list of values,
      it acts as an OR filter across specified scope items.
    - Item 'shared' requires entity_scopes to contain BOTH 'alert' AND 'case'.
    - Items 'alert', 'case', etc. check if that item is in entity_scopes.

    Args:
        scope_filter: The target scope filter string or set/list of scope items.
        entity_scopes: The entity's scope(s).

    Returns:
        True if entity_scopes satisfies the scope_filter, False otherwise.

    """
    if not scope_filter:
        return True

    normalized_entity_scopes = _normalize_scopes(entity_scopes)

    if isinstance(scope_filter, str):
        scope_items = [x.strip().lower() for x in scope_filter.split(",") if x.strip()]
    else:
        scope_items = [str(x).strip().lower() for x in scope_filter]

    for item in scope_items:
        if item == "shared":
            if {"alert", "case"}.issubset(normalized_entity_scopes):
                return True
        elif item in normalized_entity_scopes:
            return True

    return False


def resolve_name_and_scopes(field_name_or_id: str) -> tuple[str, set[str] | None]:
    """Resolve field name and scopes from a given field name or identifier string.

    Args:
        field_name_or_id: The custom field name or identifier.

    Returns:
        A tuple of (resolved_name, scopes_set_or_none).

    """
    scopes = None
    name = field_name_or_id
    if name.lower().endswith("_alert"):
        scopes = {"alert"}
        name = name[:-6]
    elif name.lower().endswith("_case"):
        scopes = {"case"}
        name = name[:-5]
    elif name.lower().endswith("_alert_case") or name.lower().endswith("_case_alert"):
        scopes = {"shared"}
        name = name[:-11]
    elif name.lower().endswith("_shared"):
        scopes = {"shared"}
        name = name[:-7]
    return name, scopes


def normalize_name(n: str) -> str:
    """Normalize custom field display name for comparison.

    Args:
        n: Name string.

    Returns:
        Normalized name string.

    """
    return n.lower().replace(" ", "_").replace("/", "_")


def _find_local_custom_field_file_by_name(name_or_path: str) -> Path | None:
    path = Path(name_or_path)
    if path.is_file():
        return path

    try:
        custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()
    except Exception:  # ruff:ignore[blind-except]
        return None
    if not custom_fields_root.exists() or not custom_fields_root.is_dir():
        return None

    safe_name = name_or_path
    if safe_name.endswith((".yaml", ".yml")):
        safe_name = Path(safe_name).stem

    for f in custom_fields_root.rglob("*.yaml"):
        if f.stem.lower() == safe_name.lower():
            return f
    for f in custom_fields_root.rglob("*.yml"):
        if f.stem.lower() == safe_name.lower():
            return f

    return None


@pull_app.command(name="custom-field")
@track_command
def pull_custom_field(  # ruff:ignore[complex-structure, too-many-branches, too-many-locals, too-many-statements]
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
    scope: Annotated[
        str | None,
        typer.Option(
            "--scope",
            help="Filter custom fields by scope (e.g., 'alert' or 'case').",
        ),
    ] = None,
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
    except Exception as e:  # ruff:ignore[blind-except]
        logger.error("Failed to fetch installed custom fields: %s", e)  # ruff:ignore[error-instead-of-exception]
        raise typer.Exit(1) from None

    if list_only:
        logger.info("Available Custom Fields:")
        for field in installed_fields:
            if scope and not matches_scope_filter(scope, field.get("scopes")):
                continue
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
        filtered_fields = []
        for field in installed_fields:
            if scope and not matches_scope_filter(scope, field.get("scopes")):
                continue
            filtered_fields.append(field)

        logger.info("Pulling %d custom fields...", len(filtered_fields))
        pulled_count = 0
        for field in filtered_fields:
            field_id = field.get("id")
            field_name = field.get("name") or field_id
            if not field_id:
                continue

            try:
                _download_and_save_custom_field(backend_api, field_id, dst)
                pulled_count += 1
            except Exception as e:  # ruff:ignore[blind-except]
                logger.error("Skipping custom field '%s' due to an error: %s", field_name, e)  # ruff:ignore[error-instead-of-exception]

        logger.info("Successfully finished pulling all %d custom fields.", pulled_count)
        return

    # Standard single pull
    if field_name_or_id is None:
        logger.error("field_name_or_id is required if not pulling or listing all")
        raise typer.Exit(1)

    target_name = field_name_or_id
    target_scopes = None

    # Check if the input corresponds to a local file path or filename
    local_file_path = _find_local_custom_field_file_by_name(field_name_or_id)
    if local_file_path:
        try:
            local_data = mp.core.file_utils.load_yaml_file(local_file_path)
        except Exception:  # ruff:ignore[blind-except]
            logger.warning("Failed to load local file '%s' to extract displayName.", local_file_path)
        else:
            if isinstance(local_data, dict):
                target_name = local_data.get("displayName") or target_name
                target_scopes = local_data.get("scopes")
                if not dst:
                    dst = local_file_path
    else:
        # Resolve trailing scope suffixes (e.g. Free_Text_[Serhii_2]_alert)
        parsed_name, parsed_scopes = resolve_name_and_scopes(field_name_or_id)
        target_name = parsed_name
        if parsed_scopes:
            target_scopes = parsed_scopes

    # Explicitly passed scope option takes precedence
    if scope:
        target_scopes = scope

    matching_fields = []
    try:
        numeric_id = int(field_name_or_id)
        for field in installed_fields:
            if field.get("id") == numeric_id:
                matching_fields.append(field)
                break
    except ValueError:
        for field in installed_fields:
            server_name = field.get("displayName") or field.get("name") or ""
            if normalize_name(server_name) == normalize_name(target_name):
                if target_scopes is not None:
                    server_scopes = field.get("scopes")
                    if not matches_scope_filter(target_scopes, server_scopes):
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

    logger.info("Successfully pulled %d custom field(s).", len(matching_fields))


def _find_local_custom_field_file(display_name: str, scopes: set[str]) -> Path | None:
    try:
        custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()
    except Exception:  # ruff:ignore[blind-except]
        return None
    if not custom_fields_root.exists() or not custom_fields_root.is_dir():
        return None

    for f in custom_fields_root.rglob("*.yaml"):
        try:
            data = mp.core.file_utils.load_yaml_file(f)
        except Exception:  # ruff:ignore[blind-except, try-except-continue]
            continue
        if isinstance(data, dict):
            local_name = data.get("displayName")
            local_scopes = data.get("scopes")
            if (
                local_name
                and str(local_name).lower() == display_name.lower()
                and _normalize_scopes(local_scopes) == _normalize_scopes(scopes)
            ):
                return f
    return None


def _download_and_save_custom_field(  # ruff:ignore[complex-structure, too-many-branches, too-many-statements]
    backend_api: mp.dev_env.api.BackendAPI, field_id: int | str, dst: Path | None
) -> None:
    logger.info("Downloading custom field (ID: %s)...", field_id)
    try:
        numeric_id = int(field_id)
        field_data = backend_api.download_custom_field(numeric_id)
    except (ValueError, TypeError):
        logger.error("Invalid field ID '%s': Must be a numeric value.", field_id)  # ruff:ignore[error-instead-of-exception]
        raise typer.Exit(1) from None
    except Exception as e:  # ruff:ignore[blind-except]
        logger.error("Failed to download custom field '%s': %s", field_id, e)  # ruff:ignore[error-instead-of-exception]
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
                parts = [x.strip().lower() for x in val.split(",") if x.strip()]
            return "_".join(sorted(parts))

        scopes_suffix = normalize_scopes_for_filename(scopes_val)
        file_name = f"{safe_name}_{scopes_suffix}.yaml"
    else:
        file_name = f"{safe_name}.yaml"

    if dst is None:
        scopes = _normalize_scopes(scopes_val)
        existing_file = _find_local_custom_field_file(raw_name, scopes)
        if existing_file:
            logger.info("Found matching local custom field file at '%s'. Overwriting it.", existing_file)
            actual_dst = existing_file
        else:
            custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()

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
    except Exception as e:  # ruff:ignore[blind-except]
        logger.error("Failed to save custom field to '%s': %s", actual_dst, e)  # ruff:ignore[error-instead-of-exception]
        raise typer.Exit(1) from None
