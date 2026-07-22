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
from mp.dev_env.sub_commands.push import push_app
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


@push_app.command(name="custom-field")
@track_command
def push_custom_field(  # ruff:ignore[complex-structure, too-many-branches, too-many-locals, too-many-statements]
    field_file_or_name: Annotated[
        str | None, typer.Argument(help="The custom field YAML file path or name to push.")
    ] = None,
    *,
    scope: Annotated[
        str | None,
        typer.Option(
            "--scope",
            help="Filter custom fields by scope (e.g., 'alert', 'case', 'alert,case', or 'shared').",
        ),
    ] = None,
    push_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Push all custom fields from the local directory to the environment.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Force creating new custom fields if they do not exist on the platform.",
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

        yaml_files = list(custom_fields_root.rglob("*.yaml")) + list(custom_fields_root.rglob("*.yml"))
        if not yaml_files:
            logger.info("No custom field files found to push.")
            return

        pushed_keys = set()
        pushed_count = 0
        for f in yaml_files:
            try:
                field_data = mp.core.file_utils.load_yaml_file(f)
            except Exception:  # ruff:ignore[blind-except]
                field_data = None

            if isinstance(field_data, dict):
                # Filter by scope if provided
                if scope and not matches_scope_filter(scope, field_data.get("scopes")):
                    continue

                display_name = field_data.get("displayName")
                scopes_val = field_data.get("scopes")
                if display_name:
                    scopes_key = tuple(sorted(_normalize_scopes(scopes_val)))
                    key = (display_name.lower(), scopes_key)
                    if key in pushed_keys:
                        logger.info(
                            "Custom field '%s' with scopes %s already pushed, skipping duplicate file '%s'",
                            display_name,
                            scopes_key,
                            f,
                        )
                        continue
                    pushed_keys.add(key)

            _push_single_custom_field(f, force)
            pushed_count += 1

        logger.info("Successfully finished pushing all %d custom fields.", pushed_count)
        return

    # Standard single push
    assert field_file_or_name is not None  # ruff:ignore[assert]

    target_scopes = scope or None

    parsed_name = field_file_or_name
    # Try resolving scope from trailing suffix in string argument
    if field_file_or_name:
        p_name, p_scopes = resolve_name_and_scopes(field_file_or_name)
        parsed_name = p_name
        if p_scopes and not scope:
            target_scopes = p_scopes

    files_to_push = []
    field_file = Path(field_file_or_name)
    if field_file.is_file():
        files_to_push.append(field_file)
    else:
        # Try resolving by name in the custom fields directory and subdirectories
        safe_name = parsed_name.replace("/", "_").replace(" ", "_")
        candidate_files = list(custom_fields_root.rglob(f"{safe_name}.yaml")) + list(
            custom_fields_root.rglob(f"{safe_name}.yml")
        )
        # Also resolve suffix matching (e.g. name_scopes.yaml)
        matching_files = [
            f
            for f in custom_fields_root.rglob("*")
            if f.is_file()
            and f.suffix in {".yaml", ".yml"}
            and (f.name.startswith(f"{safe_name}_") or f.stem == safe_name)
        ]

        # Combine candidate and matching files
        all_candidates = list(dict.fromkeys(candidate_files + matching_files))  # deduplicate keeping order

        # Filter by target_scopes if specified
        for f in all_candidates:
            try:
                f_data = mp.core.file_utils.load_yaml_file(f)
            except Exception:  # ruff:ignore[blind-except, try-except-continue]
                continue
            if isinstance(f_data, dict) and target_scopes:
                f_scopes = f_data.get("scopes")
                if not matches_scope_filter(target_scopes, f_scopes):
                    continue
            files_to_push.append(f)

        if not files_to_push:
            logger.error("Custom field file not found for '%s'", field_file_or_name)
            raise typer.Exit(1)

    if len(files_to_push) > 1:
        logger.info("Found %d files matching '%s'. Pushing all of them...", len(files_to_push), field_file_or_name)

    for f in files_to_push:
        _push_single_custom_field(f, force)

    logger.info("Successfully pushed %d custom field(s).", len(files_to_push))


def _push_single_custom_field(field_file: Path, force: bool) -> None:  # ruff:ignore[complex-structure, boolean-type-hint-positional-argument, too-many-branches, too-many-statements]
    logger.info("Loading custom field YAML from '%s'...", field_file)
    try:
        field_data = mp.core.file_utils.load_yaml_file(field_file)
    except Exception as e:  # ruff:ignore[blind-except]
        logger.error("Failed to parse custom field YAML: %s", e)  # ruff:ignore[error-instead-of-exception]
        raise typer.Exit(1) from None

    if not isinstance(field_data, dict):
        logger.error("Custom field data must be a dictionary.")
        raise typer.Exit(1)

    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Checking if custom field exists on server...")
    try:
        installed_fields = backend_api.list_custom_fields()
    except Exception as e:  # ruff:ignore[blind-except]
        logger.error("Failed to fetch installed custom fields: %s", e)  # ruff:ignore[error-instead-of-exception]
        raise typer.Exit(1) from None

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

                def normalize_scopes(val: str | list | None) -> set[str]:
                    if not val:
                        return set()
                    if isinstance(val, list):
                        return {str(x).strip().lower() for x in val}
                    return {x.strip().lower() for x in val.split(",") if x.strip()}

                if normalize_scopes(local_scopes) != normalize_scopes(server_scopes):
                    continue

            existing_id = field.get("id")
            break

    if existing_id is not None:
        logger.info("Updating existing custom field (ID: %s)...", existing_id)
        try:
            numeric_id = int(existing_id)
        except (ValueError, TypeError) as e:
            logger.error("Invalid existing ID '%s': Must be a numeric value.", existing_id)  # ruff:ignore[error-instead-of-exception]
            raise typer.Exit(1) from e
        else:
            # Align casing of displayName to match server to avoid validation errors
            server_field = next((f for f in installed_fields if f.get("id") == numeric_id), None)
            if server_field and server_field.get("displayName"):
                field_data["displayName"] = server_field["displayName"]

            # Update the payload with the target environment's ID and name
            field_data["id"] = numeric_id
            field_data["name"] = f"projects//locations//instances//customFields/{numeric_id}"

            try:
                backend_api.update_custom_field(numeric_id, field_data)
            except Exception as e:  # ruff:ignore[blind-except]
                logger.error("Failed to update custom field '%s': %s", field_name, e)  # ruff:ignore[error-instead-of-exception]
                raise typer.Exit(1) from None
    else:
        if not force:
            logger.error("=" * 80)
            logger.error("[VALIDATION ERROR] Custom Field Not Installed")
            logger.error("Custom field '%s' not found on the platform.", field_name)
            logger.error(
                "Creation of new custom fields is blocked by default. Use the --force flag to force creation."
            )
            logger.error("=" * 80)
            raise typer.Exit(1)

        logger.info("Creating new custom field...")
        try:
            backend_api.create_custom_field(field_data)
        except Exception as e:  # ruff:ignore[blind-except]
            logger.error("Failed to create custom field '%s': %s", field_name, e)  # ruff:ignore[error-instead-of-exception]
            raise typer.Exit(1) from None

    logger.info("Custom field '%s' pushed successfully.", field_name)
