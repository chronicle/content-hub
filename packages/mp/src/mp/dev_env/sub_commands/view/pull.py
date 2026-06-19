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
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Any, cast

import typer

import mp.core.file_utils
from mp.build_project.restructure.views.deconstruct import ViewDeconstructor
from mp.core.data_models.playbooks.overview.metadata import Overview
from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mp.core.data_models.playbooks.overview.metadata import BuiltOverview, BuiltOverviewDetails


def _normalize_downloaded_view(flat_view: dict[str, Any]) -> BuiltOverview:
    """Normalize flat camelCase view payload from SOAR REST API into BuiltOverview.

    Args:
        flat_view: The flat camelCase dictionary representing the view downloaded from SOAR.

    Returns:
        The normalized BuiltOverview structure.

    """
    built_widgets = []
    for w in flat_view.get("widgets") or []:
        meta = w.get("metadata") or {}
        config = w.get("config") or {}

        # If data is HTML, we must include the htmlContent in config
        # Actually in widgets list, htmlContent was inside DataDefinitionJson
        # Serialize the config back into DataDefinitionJson
        data_definition_json = json.dumps(config)

        cg_data = meta.get("conditionsGroup")
        if not isinstance(cg_data, dict):
            cg = {"LogicalOperator": 1, "Conditions": []}
        else:
            op = cg_data.get("logicalOperator")
            if op is None:
                op = cg_data.get("LogicalOperator", 1)
            conds = cg_data.get("conditions")
            if conds is None:
                conds = cg_data.get("Conditions", [])

            normalized_conds = [
                {
                    "FieldName": cond.get("fieldName") or cond.get("FieldName") or "",
                    "Value": cond.get("value") or cond.get("Value"),
                    "MatchType": cond.get("matchType") or cond.get("MatchType") or 0,
                    "CustomOperatorName": cond.get("customOperatorName") or cond.get("CustomOperatorName"),
                }
                for cond in conds
                if isinstance(cond, dict)
            ]

            cg = {
                "LogicalOperator": op,
                "Conditions": normalized_conds,
            }

        built_widget: dict[str, Any] = {
            "Title": meta.get("title") or "",
            "Description": meta.get("description") or "",
            "Identifier": meta.get("identifier") or "",
            "Order": meta.get("order") or 0,
            "TemplateIdentifier": meta.get("templateIdentifier") or "",
            "Type": meta.get("type") or 0,
            "DataDefinitionJson": data_definition_json,
            "GridColumns": meta.get("width") or 1,
            "ActionWidgetTemplateIdentifier": meta.get("actionWidgetTemplateIdentifier"),
            "StepIdentifier": meta.get("stepIdentifier"),
            "StepIntegration": meta.get("stepIntegration"),
            "BlockStepIdentifier": meta.get("blockStepIdentifier"),
            "BlockStepInstanceName": meta.get("blockStepInstanceName"),
            "PresentIfEmpty": meta.get("presentIfEmpty") or False,
            "ConditionsGroup": cg,
            "IntegrationName": meta.get("integrationName"),
        }
        built_widgets.append(built_widget)

    overview_template: dict[str, Any] = {
        "Identifier": flat_view.get("identifier") or "",
        "Name": flat_view.get("name") or "",
        "Creator": flat_view.get("creator"),
        "PlaybookDefinitionIdentifier": flat_view.get("playbookIdentifier") or "",
        "Type": flat_view.get("type") or 0,
        "AlertRuleType": flat_view.get("alertRuleType"),
        "Widgets": built_widgets,
        "Roles": flat_view.get("roles") or [],
    }

    return {
        "OverviewTemplate": cast("BuiltOverviewDetails", overview_template),
        "Roles": flat_view.get("roleNames") or [],
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
    """Pull and deconstruct a view template from the SOAR environment.

    Raises:
        typer.Exit: If the pull or deconstruction fails.

    """
    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Fetching installed views...")
    try:
        installed_views = backend_api.list_views()
    except Exception as e:
        logger.exception("Failed to fetch installed views")
        raise typer.Exit(1) from e

    view_identifier = _find_view_identifier(view_name_or_id, installed_views)
    logger.info("Downloading view '%s' (ID: %s)...", view_name_or_id, view_identifier)

    try:
        built_view_data = backend_api.download_view(view_identifier)
    except Exception as e:
        logger.exception("Failed to download view '%s'", view_name_or_id)
        raise typer.Exit(1) from e

    if not isinstance(built_view_data, dict):
        logger.error("Downloaded view data is not a valid JSON object.")
        raise typer.Exit(1)

    # Determine destination path
    if dst is None:
        views_root = mp.core.file_utils.create_or_get_views_root_dir()
        dst = views_root / view_identifier
    else:
        dst /= view_identifier

    # Parse built payload into Overview model and deconstruct
    try:
        normalized_view_data = _normalize_downloaded_view(built_view_data)
        overview = Overview.from_built(normalized_view_data)
        logger.info("Deconstructing view to %s...", dst)
        deconstructor = ViewDeconstructor(overview, dst)
        deconstructor.deconstruct()
    except Exception as e:
        logger.exception("Deconstruction failed for view '%s'", view_name_or_id)
        raise typer.Exit(1) from e

    logger.info("✅ View '%s' pulled and deconstructed successfully to %s", view_name_or_id, dst)


def _find_view_identifier(view_name_or_id: str, installed_views: list[dict[str, Any]] | None) -> str:
    """Find the view identifier matching the given name or identifier.

    Args:
        view_name_or_id: The view name or identifier to search for.
        installed_views: The list of installed views fetched from SOAR.

    Returns:
        The matching view identifier.

    Raises:
        typer.Exit: If the view is not found in the installed views.

    """
    for view in installed_views or []:
        identifier = view.get("Identifier") or view.get("identifier")
        name = view.get("Name") or view.get("name")

        if identifier and (view_name_or_id.lower() == identifier.lower() or view_name_or_id == name):
            return cast("str", identifier)

    logger.error("View '%s' not found in installed views in SOAR platform.", view_name_or_id)
    raise typer.Exit(1)
