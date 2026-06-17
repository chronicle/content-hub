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

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
import yaml

import mp.core.file_utils
from mp.build_project.restructure.views.build import ViewBuilder
from mp.core.data_models.playbooks.overview.metadata import BuiltOverview
from mp.core.utils.common.utils import to_snake_case
from mp.dev_env.sub_commands.push import push_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mp.dev_env.api import BackendAPI



def _denormalize_pushed_view(built_view: BuiltOverview) -> dict[str, Any]:
    """Convert wrapped PascalCase BuiltOverview back into flat camelCase payload expected by SOAR."""
    template = built_view["OverviewTemplate"]

    # 1. Map widgets
    flat_widgets = []
    for w in template.get("Widgets", []):
        config_dict = {}
        if w.get("DataDefinitionJson"):
            try:
                config_dict = json.loads(w["DataDefinitionJson"])
            except json.JSONDecodeError:
                pass

        cg = w.get("ConditionsGroup")
        flat_cg = None
        if cg:
            flat_cg = {
                "logicalOperator": cg.get("LogicalOperator", 1),
                "conditions": cg.get("Conditions", []),
            }

        meta = {
            "title": w.get("Title", ""),
            "description": w.get("Description", ""),
            "identifier": w.get("Identifier", ""),
            "order": w.get("Order", 0),
            "templateIdentifier": w.get("TemplateIdentifier", ""),
            "type": w.get("Type", 0),
            "width": w.get("GridColumns", 1),
            "actionWidgetTemplateIdentifier": w.get("ActionWidgetTemplateIdentifier"),
            "stepIdentifier": w.get("StepIdentifier"),
            "stepIntegration": w.get("StepIntegration"),
            "blockStepIdentifier": w.get("BlockStepIdentifier"),
            "blockStepInstanceName": w.get("BlockStepInstanceName"),
            "presentIfEmpty": w.get("PresentIfEmpty", False),
            "conditionsGroup": flat_cg,
            "integrationName": w.get("IntegrationName"),
        }

        flat_widgets.append({"metadata": meta, "config": config_dict})

    # 2. Map overview template details
    flat_view = {
        "identifier": template.get("Identifier", ""),
        "name": template.get("Name", ""),
        "creator": template.get("Creator"),
        "playbookIdentifier": template.get("PlaybookDefinitionIdentifier", ""),
        "type": template.get("Type", 0),
        "alertRuleType": template.get("AlertRuleType"),
        "widgets": flat_widgets,
        "roles": template.get("Roles", []),
        "roleNames": built_view.get("Roles", []),
    }

    return flat_view


@push_app.command(name="view")
@track_command
def push_view(
    view_name_or_id: Annotated[str, typer.Argument(help="The view name or identifier to build and push.")],
    src: Annotated[
        Path | None,
        typer.Option(help="Source folder containing the view directory."),
    ] = None,
) -> None:
    """Build and push a view template to the SOAR environment."""
    try:
        # 1. Locate source path
        view_src_path = _get_view_path_by_name(view_name_or_id, src)
        logger.info("Found source view path at: %s", view_src_path)

        # 2. Build the view to a temp or output directory
        # We can build it directly into `get_view_out_dir()`
        out_dir = mp.core.file_utils.get_view_out_dir()
        builder = ViewBuilder(view_src_path, out_dir)
        builder.build()

        # The built JSON name is to_snake_case(view_src_path.stem).json
        built_json_name = f"{to_snake_case(view_src_path.stem)}{mp.core.constants.JSON_SUFFIX}"
        built_json_path = out_dir / built_json_name

        if not built_json_path.exists():
            logger.error("Built view file not found at: %s", built_json_path)
            raise typer.Exit(1)

        # 3. Load built JSON data
        logger.info("Loading built view JSON...")
        view_data: dict[str, Any] = json.loads(built_json_path.read_text(encoding="utf-8"))

        # 4. Upload to SOAR
        config = load_dev_env_config()
        backend_api: BackendAPI = get_backend_api(config)

        logger.info("Uploading view to SOAR platform...")
        flat_view_data = _denormalize_pushed_view(view_data) # type: ignore

        # Resolve ID from server to perform UPDATE instead of INSERT
        try:
            installed_views = backend_api.list_views()
            target_uuid = flat_view_data.get("identifier")
            for v in installed_views:
                v_uuid = v.get("identifier") or v.get("Identifier")
                if v_uuid == target_uuid:
                    existing_id = v.get("id") or v.get("Id")
                    if existing_id:
                        logger.info("Resolved existing view ID %s on server.", existing_id)
                        flat_view_data["id"] = existing_id
                        break
        except Exception as ex:
            logger.warning("Failed to resolve existing view ID on server: %s. Proceeding as new view.", ex)

        result = backend_api.upload_view(flat_view_data)
        logger.debug("Upload response: %s", result)

        logger.info("✅ View '%s' pushed successfully.", view_name_or_id)

    except Exception as e:
        logger.exception("Upload failed for view '%s'", view_name_or_id)
        raise typer.Exit(1) from e


def _get_view_path_by_name(view_name_or_id: str, src: Path | None = None) -> Path:
    if src is not None:
        candidate = src / view_name_or_id
        if candidate.exists():
            return candidate
        if src.name == view_name_or_id or (src / mp.core.constants.VIEW_FILE_NAME).exists():
            return src

    views_root = mp.core.file_utils.create_or_get_views_root_dir()
    candidate = views_root / view_name_or_id
    if candidate.exists():
        return candidate

    candidate_snake = views_root / to_snake_case(view_name_or_id)
    if candidate_snake.exists():
        return candidate_snake

    # Try searching for view.yaml name fields inside the views directories
    if views_root.exists():
        for folder in views_root.iterdir():
            if folder.is_dir():
                view_yaml_path = folder / mp.core.constants.VIEW_FILE_NAME
                if view_yaml_path.exists():
                    try:
                        view_meta = yaml.safe_load(view_yaml_path.read_text(encoding="utf-8"))
                        if view_meta.get("name") == view_name_or_id:
                            return folder
                    except Exception:  # pylint: disable=broad-except
                        pass

    logger.error("Could not find source view directory for '%s'", view_name_or_id)
    raise typer.Exit(1)
