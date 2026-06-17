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

import mp.core.file_utils
from mp.build_project.restructure.views.deconstruct import ViewDeconstructor
from mp.core.data_models.playbooks.overview.metadata import BuiltOverview, Overview
from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mp.dev_env.api import BackendAPI


def _normalize_downloaded_view(flat_view: dict[str, Any]) -> BuiltOverview:
    """Normalize flat camelCase view payload from SOAR REST API into BuiltOverview."""
    built_widgets = []
    for w in flat_view.get("widgets", []):
        meta = w.get("metadata", {})
        config = w.get("config", {})

        # If data is HTML, we must include the htmlContent in config
        # Actually in widgets list, htmlContent was inside DataDefinitionJson
        # Serialize the config back into DataDefinitionJson
        data_definition_json = json.dumps(config)

        cg = meta.get("conditionsGroup")
        if cg is None:
            cg = {"LogicalOperator": 1, "Conditions": []}
        else:
            cg = {
                "LogicalOperator": cg.get("logicalOperator") or cg.get("LogicalOperator") or 1,
                "Conditions": cg.get("conditions") or cg.get("Conditions") or [],
            }

        built_widget: dict[str, Any] = {
            "Title": meta.get("title") or "",
            "Description": meta.get("description") or "",
            "Identifier": meta.get("identifier") or "",
            "Order": meta.get("order") or 0,
            "TemplateIdentifier": meta.get("templateIdentifier") or "",
            "Type": meta.get("type") or 0,
            "DataDefinitionJson": data_definition_json,
            "GridColumns": meta.get("width", 1),
            "ActionWidgetTemplateIdentifier": meta.get("actionWidgetTemplateIdentifier"),
            "StepIdentifier": meta.get("stepIdentifier"),
            "StepIntegration": meta.get("stepIntegration"),
            "BlockStepIdentifier": meta.get("blockStepIdentifier"),
            "BlockStepInstanceName": meta.get("blockStepInstanceName"),
            "PresentIfEmpty": meta.get("presentIfEmpty", False),
            "ConditionsGroup": cg,
            "IntegrationName": meta.get("integrationName"),
        }
        built_widgets.append(built_widget)

    overview_template: dict[str, Any] = {
        "Identifier": flat_view.get("identifier") or "",
        "Name": flat_view.get("name") or "",
        "Creator": flat_view.get("creator"),
        "PlaybookDefinitionIdentifier": flat_view.get("playbookIdentifier") or "",
        "Type": flat_view.get("type", 0),
        "AlertRuleType": flat_view.get("alertRuleType"),
        "Widgets": built_widgets,
        "Roles": flat_view.get("roles", []),
    }

    return {
        "OverviewTemplate": overview_template, # type: ignore
        "Roles": flat_view.get("roleNames", []),
    }


@pull_app.command(name="view")
@track_command
def pull_view(
    view_name_or_id: Annotated[str, typer.Argument(help="The view name or identifier to pull.")],
    dst: Annotated[
        Path | None,
        typer.Option(help="Destination folder. Defaults to 'content/views/<view_identifier>'."),
    ] = None,
) -> None:
    """Pull and deconstruct a view template from the SOAR environment."""
    try:
        config = load_dev_env_config()
        backend_api: BackendAPI = get_backend_api(config)

        logger.info("Fetching installed views...")
        installed_views: list[dict[str, Any]] = backend_api.list_views()

        view_identifier = _find_view_identifier(view_name_or_id, installed_views)
        logger.info("Downloading view '%s' (ID: %s)...", view_name_or_id, view_identifier)

        # Download built view template JSON payload
        built_view_data: dict[str, Any] = backend_api.download_view(view_identifier)

        # Determine destination path
        if dst is None:
            views_root = mp.core.file_utils.create_or_get_views_root_dir()
            dst = views_root / view_identifier
        else:
            dst = dst / view_identifier

        # Parse built payload into Overview model
        normalized_view_data = _normalize_downloaded_view(built_view_data)
        overview = Overview.from_built(normalized_view_data)

        # Deconstruct view into destination folder
        logger.info("Deconstructing view to %s...", dst)
        deconstructor = ViewDeconstructor(overview, dst)
        deconstructor.deconstruct()

        logger.info("✅ View '%s' pulled and deconstructed successfully to %s", view_name_or_id, dst)

    except Exception as e:
        logger.exception("Pull failed for view '%s'", view_name_or_id)
        raise typer.Exit(1) from e


def _find_view_identifier(view_name_or_id: str, installed_views: list[dict[str, Any]]) -> str:
    for view in installed_views:
        identifier = view.get("Identifier") or view.get("identifier")
        name = view.get("Name") or view.get("name")

        if view_name_or_id in (identifier, name):
            return identifier

    logger.error("View '%s' not found in installed views in SOAR platform.", view_name_or_id)
    raise typer.Exit(1)
