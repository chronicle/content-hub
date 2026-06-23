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

import typer
import yaml

import mp.core.constants
import mp.core.file_utils
from mp.build_project.restructure.views.build import ViewBuilder
from mp.core.utils import to_snake_case
from mp.dev_env.sub_commands.push import push_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mp.core.data_models.playbooks.overview.metadata import BuiltOverview
    from mp.dev_env.api import BackendAPI


def _denormalize_pushed_view(built_view: BuiltOverview) -> dict[str, Any]:
    """Convert wrapped PascalCase BuiltOverview back into flat camelCase payload expected by SOAR.

    Args:
        built_view: The BuiltOverview dictionary structure representing the view.

    Returns:
        The flat camelCase dictionary payload.

    """
    template = built_view.get("OverviewTemplate") or {}

    # 1. Map widgets
    flat_widgets = []
    for w in template.get("Widgets") or []:
        config_dict = {}
        data_def = w.get("DataDefinitionJson")
        if isinstance(data_def, str):
            with contextlib.suppress(json.JSONDecodeError):
                config_dict = json.loads(data_def)

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


@push_app.command(name="view")
@track_command
def push_view(
    view_name_or_id: Annotated[str, typer.Argument(help="The view name or identifier to build and push.")],
    src: Annotated[
        Path | None,
        typer.Option(help="Source folder containing the view directory."),
    ] = None,
    allow_create: Annotated[
        bool,
        typer.Option(
            "--allow-create",
            help="Allow creating a new view if it does not already exist on the platform.",
        ),
    ] = False,
) -> None:
    """Build and push a view template to the SOAR environment.

    Raises:
        typer.Exit: If the built view file cannot be found or parsed.

    """
    # 1. Locate source path
    view_src_path = _get_view_path_by_name(view_name_or_id, src)
    logger.info("Found source view path at: %s", view_src_path)

    # 2. Build the view to a temp or output directory
    out_dir = mp.core.file_utils.get_view_out_dir()
    builder = ViewBuilder(view_src_path, out_dir)
    builder.build()

    # The built JSON name is to_snake_case(view_src_path.stem).json
    built_json_name = f"{to_snake_case(view_src_path.stem)}{mp.core.constants.JSON_SUFFIX}"
    built_json_path = out_dir / built_json_name

    if not built_json_path.exists():
        logger.error("Built view file not found at: %s", built_json_path)
        raise typer.Exit(1)

    if not mp.core.file_utils.is_built_view(built_json_path):
        raise typer.Exit(1)

    # 3. Load built JSON data
    logger.info("Loading built view JSON...")
    try:
        view_data: dict[str, Any] = json.loads(built_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.exception("Failed to parse built view JSON")
        raise typer.Exit(1) from e

    # 4. Upload to SOAR
    _upload_built_view_data(view_data, view_name_or_id, allow_create)


def _resolve_existing_view_id(backend_api: BackendAPI, identifier: str | None) -> int | None:
    """Resolve the integer database ID of an existing view on the SOAR server.

    Args:
        backend_api: The backend API client.
        identifier: The UUID identifier of the view.

    Returns:
        The integer database ID of the view if resolved, otherwise None.

    """
    if not identifier:
        return None
    try:
        installed_views = backend_api.list_views()
        for v in installed_views or []:
            v_uuid = v.get("identifier") or v.get("Identifier")
            if isinstance(v_uuid, str) and v_uuid.lower() == identifier.lower():
                return v.get("id") or v.get("Id")
    except Exception as ex:  # noqa: BLE001
        logger.warning("Failed to resolve existing view ID on server: %s. Proceeding as new view.", ex)
    return None


def _upload_built_view_data(view_data: dict[str, Any], view_name_or_id: str, allow_create: bool = False) -> None:
    """Upload built view template data to the SOAR environment.

    Args:
        view_data: The built view template dictionary structure.
        view_name_or_id: The view name or identifier.
        allow_create: Allow creating a new view if it doesn't exist.

    Raises:
        typer.Exit: If the upload fails.

    """
    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Uploading view to SOAR platform...")
    flat_view_data = _denormalize_pushed_view(cast("BuiltOverview", view_data))

    # Resolve ID from server to perform UPDATE instead of INSERT
    existing_id = _resolve_existing_view_id(backend_api, flat_view_data.get("identifier"))
    if existing_id is not None:
        logger.info("Resolved existing view ID %s on server.", existing_id)
        flat_view_data["id"] = existing_id
    elif not allow_create:
        logger.error("View '%s' (UUID: '%s') does not exist on the platform.", view_name_or_id, flat_view_data.get("identifier"))
        logger.error("Creation of new views is blocked by default. Use the --allow-create flag to force creation.")
        raise typer.Exit(1)

    try:
        result = backend_api.upload_view(flat_view_data)
        logger.debug("Upload response: %s", result)
    except Exception as e:
        logger.exception("Upload failed for view '%s'", view_name_or_id)
        raise typer.Exit(1) from e

    logger.info("✅ View '%s' pushed successfully.", view_name_or_id)


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
            view_meta = yaml.safe_load(view_yaml_path.read_text(encoding="utf-8"))
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
