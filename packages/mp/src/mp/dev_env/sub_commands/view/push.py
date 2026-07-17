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
import json
import logging
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Any, cast

import requests
import typer

import mp.core.constants
import mp.core.file_utils
from mp.build_project.restructure.views.build import ViewBuilder
from mp.core.utils import to_snake_case
from mp.dev_env.sub_commands.push import push_app
from mp.dev_env.sub_commands.utils import get_backend_api_clean as get_backend_api
from mp.dev_env.utils import load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mp.core.data_models.common.overview.metadata import BuiltOverview
    from mp.dev_env.api import BackendAPI


@push_app.command(name="view")
@track_command
def push_view(
    view_name_or_id: Annotated[
        str | None,
        typer.Argument(help="The view name or identifier to build and push."),
    ] = None,
    *,
    src: Annotated[
        Path | None,
        typer.Option(
            "--custom",
            help="Source folder containing the view directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Force creating a new view if it does not already exist on the platform.",
        ),
    ] = False,
    validate: Annotated[
        bool,
        typer.Option(
            "--validate",
            help="Validate the view locally without uploading it to the server.",
        ),
    ] = False,
    all_views: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Push all views from the local repository.",
        ),
    ] = False,
) -> None:
    """Build and push a view template to the SOAR environment.

    Raises:
        typer.Exit: If the built view file cannot be found or parsed.

    """
    if not all_views and not view_name_or_id:
        logger.error("Error: You must provide a view name or ID, or specify the --all option.")
        raise typer.Exit(1)

    if all_views:
        if view_name_or_id:
            logger.error("Error: View name or ID cannot be specified when using --all option.")
            raise typer.Exit(1)

        views_root = src or mp.core.file_utils.create_or_get_views_root_dir()
        if not views_root.exists() or not views_root.is_dir():
            logger.error("Views directory '%s' not found.", views_root)
            raise typer.Exit(1)

        local_views = [
            folder
            for folder in views_root.iterdir()
            if folder.is_dir() and (folder / mp.core.constants.VIEW_FILE_NAME).exists()
        ]

        if not local_views:
            logger.info("No views found to push.")
            return

        logger.info("Found %d views to push. Pushing all of them...", len(local_views))
        for view_dir in local_views:
            try:
                _push_single_view(view_dir, force=force, validate=validate)
                logger.info("View directory '%s' pushed successfully.", view_dir.name)
            except Exception as e:
                logger.error("Failed to push view directory '%s': %s", view_dir.name, e)  # noqa: TRY400
                raise typer.Exit(1) from None
        return

    # Standard single push
    view_src_path = _get_view_path_by_name(view_name_or_id, src)
    _push_single_view(view_src_path, force=force, validate=validate)


def _push_single_view(view_src_path: Path, *, force: bool = False, validate: bool = False) -> None:
    """Build and push a single view directory.

    Raises:
        typer.Exit: If build, parsing, or upload fails.

    """
    logger.info("Found source view path at: %s", view_src_path)

    # Build the view to a temp or output directory
    out_dir = mp.core.file_utils.get_view_out_dir()
    builder = ViewBuilder(view_src_path, out_dir)
    try:
        builder.build()
    except Exception as e:
        logger.error("Failed to build/validate view: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None

    # The built JSON name is to_snake_case(view_src_path.stem).json
    built_json_name = f"{to_snake_case(view_src_path.stem)}{mp.core.constants.JSON_SUFFIX}"
    built_json_path = out_dir / built_json_name

    if not built_json_path.exists():
        logger.error("Built view file not found at: %s", built_json_path)
        raise typer.Exit(1)

    if not mp.core.file_utils.is_built_view(built_json_path):
        raise typer.Exit(1)

    # Load built JSON data
    logger.info("Loading built view JSON...")
    try:
        view_data: dict[str, Any] = json.loads(built_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to parse built view JSON: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None

    if validate:
        _validate_view(view_data)
        logger.info("✅ View '%s' is valid.", view_src_path.name)
        return

    # Upload to SOAR
    _upload_built_view_data(view_data, view_src_path.name, force=force)


def _validate_view(view_data: dict[str, Any]) -> None:
    """Validate view's custom fields against target environment.

    Raises:
        typer.Exit: If validation fails.

    """
    config = load_dev_env_config()
    backend_api = get_backend_api(config)
    try:
        _denormalize_pushed_view(cast("BuiltOverview", view_data), backend_api)
    except typer.Exit:
        raise
    except Exception as e:
        logger.error("Validation failed with an unexpected error: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None


def _get_local_custom_fields() -> dict[str, Path]:
    """Find all local custom field files and map their displayName to file path.

    Returns:
        A dictionary mapping the display name of local custom fields to their file Path.

    """
    try:
        custom_fields_root = mp.core.file_utils.create_or_get_custom_fields_root_dir()
    except Exception:  # noqa: BLE001
        return {}

    local_fields = {}
    if custom_fields_root.exists() and custom_fields_root.is_dir():
        for f in custom_fields_root.rglob("*.yaml"):
            try:
                data = mp.core.file_utils.load_yaml_file(f)
                if isinstance(data, dict) and "displayName" in data:
                    local_fields[data["displayName"]] = f
            except Exception as ex:  # noqa: BLE001
                logger.debug("Failed to load local custom field file %s: %s", f, ex)
    return local_fields


def _resolve_widget_custom_fields(config_dict: dict[str, Any], name_to_cf_id: dict[str, int]) -> None:
    """Resolve custom field displayNames to IDs, checking local workspace if missing on server.

    Raises:
        typer.Exit: If a custom field is not found on the platform.

    """
    cfs = config_dict.get("customFields")
    if not isinstance(cfs, list):
        return
    for cf_item in cfs:
        if isinstance(cf_item, dict) and "displayName" in cf_item:
            cf_name = cf_item.pop("displayName")
            cf_id = name_to_cf_id.get(cf_name)
            if cf_id is not None:
                cf_item["id"] = cf_id
            else:
                local_cf_files = _get_local_custom_fields()
                local_file = local_cf_files.get(cf_name)
                if local_file:
                    content_root = mp.core.file_utils.create_or_get_content_dir()
                    relative_path = local_file.relative_to(content_root.parent)
                    logger.error("=" * 80)
                    logger.error("[VALIDATION ERROR] Custom Field Not Installed")
                    logger.error(
                        "Custom field '%s' referenced in the view exists locally in your workspace "
                        "at '%s', but it is not installed on the SOAR platform.",
                        cf_name,
                        relative_path,
                    )
                    logger.error(
                        'Please push this custom field first using:\n'
                        '  uv run --project packages/mp mp push custom-field "%s"',
                        cf_name,
                    )
                    logger.error("=" * 80)
                else:
                    logger.error("=" * 80)
                    logger.error("[VALIDATION ERROR] Custom Field Not Found")
                    logger.error(
                        "Custom field '%s' referenced in the view was not found on the SOAR platform, "
                        "and no local file was found under 'content/custom_fields/' directory.",
                        cf_name,
                    )
                    logger.error("=" * 80)
                raise typer.Exit(1)


def _denormalize_pushed_view(built_view: BuiltOverview, backend_api: BackendAPI) -> dict[str, Any]:
    """Convert wrapped PascalCase BuiltOverview back into flat camelCase payload expected by SOAR.

    Args:
        built_view: The BuiltOverview dictionary structure representing the view.
        backend_api: The backend API client to fetch installed entities like Custom Fields.

    Returns:
        The flat camelCase dictionary payload.

    """
    installed_cf = []
    try:
        installed_cf = backend_api.list_custom_fields()
    except Exception as e:
        logger.warning("Failed to fetch installed custom fields during view denormalization: %s", e)

    name_to_cf_id = {cf.get("displayName"): cf.get("id") for cf in installed_cf if cf.get("displayName") and cf.get("id") is not None}

    template = built_view.get("OverviewTemplate") or {}

    # 1. Map widgets
    flat_widgets = []
    for w in template.get("Widgets") or []:
        config_dict = {}
        data_def = w.get("DataDefinitionJson")
        if isinstance(data_def, str):
            with contextlib.suppress(json.JSONDecodeError):
                config_dict = json.loads(data_def)

        # Resolve Custom Fields
        _resolve_widget_custom_fields(config_dict, name_to_cf_id)

        cg = w.get("ConditionsGroup")
        flat_cg = None
        if cg:
            op = cg.get("LogicalOperator")
            flat_conds = [
                {
                    "fieldName": cond.get("FieldName") or "",
                    "value": cond.get("Value"),
                    "matchType": cond.get("MatchType") or 0,
                    "customOperatorName": cond.get("CustomOperatorName"),
                }
                for cond in cg.get("Conditions") or []
                if isinstance(cond, dict)
            ]
            flat_cg = {
                "logicalOperator": op if op is not None else 1,
                "conditions": flat_conds,
            }

        meta = {
            "title": w.get("Title") or "",
            "description": w.get("Description") or "",
            "identifier": w.get("Identifier") or "",
            "order": w.get("Order") or 0,
            "templateIdentifier": w.get("TemplateIdentifier") or "",
            "type": w.get("Type") or 0,
            "width": w.get("GridColumns") or 1,
            "actionWidgetTemplateIdentifier": w.get("ActionWidgetTemplateIdentifier"),
            "stepIdentifier": w.get("StepIdentifier"),
            "stepIntegration": w.get("StepIntegration"),
            "blockStepIdentifier": w.get("BlockStepIdentifier"),
            "blockStepInstanceName": w.get("BlockStepInstanceName"),
            "presentIfEmpty": w.get("PresentIfEmpty") or False,
            "conditionsGroup": flat_cg,
            "integrationName": w.get("IntegrationName"),
        }

        flat_widgets.append({"metadata": meta, "config": config_dict})

    # 2. Map overview template details
    return {
        "identifier": template.get("Identifier") or "",
        "name": template.get("Name") or "",
        "creator": template.get("Creator"),
        "playbookIdentifier": template.get("PlaybookDefinitionIdentifier") or "",
        "type": template.get("Type") or 0,
        "alertRuleType": template.get("AlertRuleType"),
        "widgets": flat_widgets,
        "roles": template.get("Roles") or [],
        "roleNames": built_view.get("Roles") or [],
    }


def _resolve_existing_view(
    backend_api: BackendAPI,
    local_identifier: str | None,
    local_name: str | None,
    local_type: int | None,
) -> tuple[int | None, str | None]:
    """Resolve the integer database ID and server UUID of an existing view on the SOAR server.

    Args:
        backend_api: The backend API client.
        local_identifier: The UUID identifier of the view.
        local_name: The name of the view.
        local_type: The type of the view (integer enum).

    Returns:
        A tuple of (database_id, server_uuid) if resolved, otherwise (None, None).

    """
    if not local_identifier:
        return None, None
    try:
        installed_views = backend_api.list_views()
    except Exception as ex:  # noqa: BLE001
        logger.warning("Failed to resolve existing view on server: %s. Proceeding as new view.", ex)
        return None, None

    # 1. Match by UUID (case-insensitive)
    for v in installed_views or []:
        v_uuid = v.get("identifier") or v.get("Identifier")
        if isinstance(v_uuid, str) and v_uuid.lower() == local_identifier.lower():
            v_id = v.get("id") if v.get("id") is not None else v.get("Id")
            return v_id, v_uuid

    # 2. Fallback: Match by Name and Type (case-insensitive name)
    if local_name and local_type is not None:
        for v in installed_views or []:
            v_name = v.get("name") or v.get("Name")
            v_type_raw = v.get("type") if v.get("type") is not None else v.get("Type")

            v_type = None
            if v_type_raw is not None:
                with contextlib.suppress(ValueError, TypeError):
                    v_type = int(v_type_raw)

            if (
                isinstance(v_name, str)
                and v_name.lower() == local_name.lower()
                and v_type == local_type
            ):
                v_id = v.get("id") if v.get("id") is not None else v.get("Id")
                v_uuid = v.get("identifier") or v.get("Identifier")
                logger.info(
                    "View matched by Name '%s' and Type %s. Target server UUID is '%s'. "
                    "Local UUID will be aligned to server UUID during push.",
                    v_name,
                    local_type,
                    v_uuid,
                )
                return v_id, v_uuid

    return None, None


def _verify_widgets(
    backend_api: BackendAPI,
    view_name_or_id: str,
    existing_identifier: str,
    flat_view_data: dict[str, Any],
    *,
    force: bool,
) -> None:
    """Verify that pushed widgets exist on the server unless force is True.

    Raises:
        typer.Exit: If a widget doesn't exist on the server and force is False.

    """
    existing_view = None
    try:
        existing_view = backend_api.download_view(existing_identifier)
    except Exception as ex:  # noqa: BLE001
        logger.warning("Failed to verify existing widgets on server: %s. Proceeding.", ex)

    if existing_view is not None:
        existing_widget_ids = set()
        for w in existing_view.get("widgets") or []:
            meta = w.get("metadata") or {}
            w_id = meta.get("identifier")
            if w_id:
                existing_widget_ids.add(w_id.lower())

        for w in flat_view_data.get("widgets") or []:
            meta = w.get("metadata") or {}
            w_id = meta.get("identifier")
            if (not w_id or w_id.lower() not in existing_widget_ids) and not force:
                logger.error("=" * 80)
                logger.error("[VALIDATION ERROR] Missing Widget on Platform")
                logger.error(
                    "Widget '%s' (UUID: '%s') does not exist in the view on the platform.",
                    meta.get("title") or "unnamed",
                    w_id or "missing",
                )
                logger.error(
                    "Creation of new widgets is blocked by default. "
                    "Use the --force flag to force creation."
                )
                logger.error("Failed to push view '%s'.", view_name_or_id)
                logger.error("=" * 80)
                raise typer.Exit(1)


def _validate_push_preconditions(
    backend_api: BackendAPI,
    view_name_or_id: str,
    flat_view_data: dict[str, Any],
    *,
    force: bool,
) -> None:
    """Validate push preconditions, resolving view ID and verifying widgets.

    Raises:
        typer.Exit: If the view doesn't exist and force is False, or if a widget check fails.

    """
    local_identifier = flat_view_data.get("identifier")
    local_name = flat_view_data.get("name")
    local_type = flat_view_data.get("type")

    existing_id, server_uuid = _resolve_existing_view(
        backend_api, local_identifier, local_name, local_type
    )

    if existing_id is not None and server_uuid:
        logger.info("Resolved existing view ID %s on server.", existing_id)
        flat_view_data["id"] = existing_id
        if local_identifier and local_identifier.lower() != server_uuid.lower():
            logger.info(
                "Local UUID '%s' differs from server UUID '%s'. "
                "Aligning push payload UUID to server UUID to preserve links "
                "and avoid database corruption.",
                local_identifier,
                server_uuid,
            )
            flat_view_data["identifier"] = server_uuid

        _verify_widgets(
            backend_api,
            view_name_or_id,
            server_uuid,
            flat_view_data,
            force=force,
        )
    elif not force:
        logger.error(
            "View '%s' (UUID: '%s') does not exist on the platform (checked by UUID and Name).",
            view_name_or_id,
            local_identifier,
        )
        logger.error(
            "Creation of new views is blocked by default. "
            "Use the --force flag to force creation."
        )
        logger.error("Failed to push view '%s'.", view_name_or_id)
        raise typer.Exit(1)
    elif not flat_view_data.get("identifier"):
        import uuid
        new_uuid = str(uuid.uuid4())
        logger.info("Generating new UUID '%s' for new view.", new_uuid)
        flat_view_data["identifier"] = new_uuid


def _upload_built_view_data(
    view_data: dict[str, Any],
    view_name_or_id: str,
    *,
    force: bool = False,
) -> str | None:
    """Upload built view template data to the SOAR environment.

    Args:
        view_data: The built view template dictionary structure.
        view_name_or_id: The view name or identifier.
        force: Force creating a new view if it doesn't exist.

    Returns:
        The final identifier of the view template used for upload if successful, otherwise None.

    Raises:
        typer.Exit: If the upload fails.

    """
    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Uploading view to SOAR platform...")
    flat_view_data = _denormalize_pushed_view(cast("BuiltOverview", view_data), backend_api)

    _validate_push_preconditions(
        backend_api,
        view_name_or_id,
        flat_view_data,
        force=force,
    )

    try:
        result = backend_api.upload_view(flat_view_data)
        logger.debug("Upload response: %s", result)
    except requests.exceptions.HTTPError as e:
        try:
            err_data = e.response.json()
            err_msg = err_data.get("errorMessage") or e.response.text
        except Exception:  # noqa: BLE001
            err_msg = e.response.text

        logger.error("=" * 80)  # noqa: TRY400
        logger.error("[SERVER VALIDATION ERROR] View Upload Failed (Status Code %s)", e.response.status_code)  # noqa: TRY400
        logger.error("%s", err_msg)  # noqa: TRY400
        logger.error("=" * 80)  # noqa: TRY400
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error("Upload failed for view '%s': %s", view_name_or_id, e)  # noqa: TRY400
        raise typer.Exit(1) from None

    logger.info("View '%s' pushed successfully.", view_name_or_id)
    return flat_view_data.get("identifier")


def _find_view_dir_in_root(views_root: Path, view_name_or_id: str) -> Path | None:
    """Find a view directory in views root by scanning view.yaml name fields.

    Args:
        views_root: The root views directory.
        view_name_or_id: The view name to search for.

    Returns:
        The matching view directory Path if found, otherwise None.

    """
    if not views_root.is_dir():
        return None

    for folder in views_root.iterdir():
        if not folder.is_dir():
            continue
        view_yaml_path = folder / mp.core.constants.VIEW_FILE_NAME
        if not view_yaml_path.exists():
            continue

        try:
            view_meta = mp.core.file_utils.load_yaml_file(view_yaml_path)
            if isinstance(view_meta, dict) and view_meta.get("name") == view_name_or_id:
                return folder
        except Exception as ex:  # noqa: BLE001
            logger.debug("Failed to read view.yaml in %s: %s", folder, ex)

    return None


def _get_view_path_by_name(view_name_or_id: str, src: Path | None = None) -> Path:
    """Resolve the view directory path by search priority.

    Args:
        view_name_or_id: The view name or identifier.
        src: The custom source directory path if provided.

    Returns:
        The resolved view directory Path.

    Raises:
        typer.Exit: If the view directory is not found.

    """
    views_root = src if src is not None else mp.core.file_utils.create_or_get_views_root_dir()

    # 1. If views_root is already a view directory (contains view.yaml), return it
    if views_root.is_dir() and (views_root / mp.core.constants.VIEW_FILE_NAME).exists():
        return views_root

    # 2. Check candidate directly under views_root
    candidate = views_root / view_name_or_id
    if candidate.is_dir():
        return candidate

    # Check case-insensitively under views_root
    if views_root.is_dir():
        for folder in views_root.iterdir():
            if folder.is_dir() and folder.name.lower() == view_name_or_id.lower():
                return folder

    # 3. Check snake_case candidate under views_root
    candidate_snake = views_root / to_snake_case(view_name_or_id)
    if candidate_snake.is_dir():
        return candidate_snake

    # 4. Try searching for view.yaml name fields inside the views directories
    matched_folder = _find_view_dir_in_root(views_root, view_name_or_id)
    if matched_folder:
        return matched_folder

    logger.error("Could not find source view directory for '%s' inside '%s'", view_name_or_id, views_root)
    raise typer.Exit(1)
