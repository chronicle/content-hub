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

import mp.core.constants
import mp.core.file_utils
from mp.build_project.restructure.views.deconstruct import ViewDeconstructor
from mp.core.data_models.common.overview.metadata import Overview
from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.sub_commands.utils import get_backend_api_clean as get_backend_api
from mp.dev_env.utils import find_entity_identifier, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mp.core.data_models.common.overview.metadata import BuiltOverview, BuiltOverviewDetails
    from mp.dev_env.api import BackendAPI


@pull_app.command(name="view")
@track_command
def pull_view(  # noqa: C901, PLR0912, PLR0914, PLR0915
    view_name_or_id: Annotated[str | None, typer.Argument(help="The view name or identifier to pull.")] = None,
    dst: Annotated[
        Path | None,
        typer.Option(
            "--custom",
            help="Destination folder. Defaults to 'content/views/<view_identifier>'.",
        ),
    ] = None,
    *,
    all_views: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Pull all views from the platform.",
        ),
    ] = False,
    list_only: Annotated[
        bool,
        typer.Option(
            "--list",
            help="List all views available in the environment without pulling.",
        ),
    ] = False,
) -> None:
    """Pull and deconstruct a view template from the SOAR environment.

    Raises:
        typer.Exit: If the pull or deconstruction fails.

    """
    if not all_views and not list_only and not view_name_or_id:
        logger.error("Error: You must specify a view name or ID, or use the --all or --list options.")
        raise typer.Exit(1)

    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Fetching installed views...")
    try:
        installed_views = backend_api.list_views()
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to fetch installed views: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None

    if list_only:
        logger.info("Available View Templates:")
        for view in installed_views:
            name = view.get("name") or view.get("Name") or "Unknown"
            view_type = view.get("type") if view.get("type") is not None else view.get("Type")
            logger.info("  - Name: '%s' (Type: %s)", name, view_type)
        return

    views_root = mp.core.file_utils.create_or_get_views_root_dir()

    if all_views:  # noqa: PLR1702
        if dst is not None:
            logger.error("Error: --custom destination option cannot be used when pulling all views.")
            raise typer.Exit(1)

        logger.info("Pulling all %d views...", len(installed_views))
        for view in installed_views:
            view_id = None
            for key in ("Identifier", "identifier", "Id", "id"):
                if key in view and view[key] is not None:
                    view_id = str(view[key])
                    break

            view_name = None
            for key in ("Name", "name", "DisplayName", "displayName"):
                if key in view and view[key] is not None:
                    view_name = str(view[key])
                    break

            if view_id:
                # Find matching local folder
                existing_local_folder = None
                if views_root.is_dir():
                    for folder in views_root.iterdir():
                        if not folder.is_dir():
                            continue
                        view_yaml_path = folder / mp.core.constants.VIEW_FILE_NAME
                        if not view_yaml_path.exists():
                            continue
                        try:
                            view_meta = mp.core.file_utils.load_yaml_file(view_yaml_path)
                        except Exception:  # noqa: BLE001, S110
                            pass
                        else:
                            if isinstance(view_meta, dict):
                                local_uuid = view_meta.get("identifier")
                                local_name = view_meta.get("name")
                                if (local_uuid and local_uuid.lower() == view_id.lower()) or (
                                    view_name and local_name and local_name.lower() == view_name.lower()
                                ):
                                    existing_local_folder = folder
                                    break

                view_dst = existing_local_folder or views_root / view_id
                try:
                    download_and_deconstruct_view(backend_api, view_id, view_dst)
                    logger.info(
                        "View '%s' (ID: %s) pulled successfully to %s.", view_name or view_id, view_id, view_dst
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to pull view '%s' (ID: %s): %s", view_name or view_id, view_id, e)  # noqa: TRY400
        return

    # Standard single pull
    assert view_name_or_id is not None  # noqa: S101
    view_identifier_raw = find_entity_identifier(view_name_or_id, installed_views, "View")
    if view_identifier_raw is None:
        raise typer.Exit(1)
    view_identifier = str(view_identifier_raw)

    # Determine destination path
    if dst is None:  # noqa: PLR1702
        existing_local_folder = None
        if views_root.is_dir():
            for folder in views_root.iterdir():
                if not folder.is_dir():
                    continue
                view_yaml_path = folder / mp.core.constants.VIEW_FILE_NAME
                if not view_yaml_path.exists():
                    continue
                try:
                    view_meta = mp.core.file_utils.load_yaml_file(view_yaml_path)
                except Exception:  # noqa: BLE001, S110
                    pass
                else:
                    if isinstance(view_meta, dict):
                        local_uuid = view_meta.get("identifier")
                        local_name = view_meta.get("name")
                        if (local_uuid and local_uuid.lower() == view_identifier.lower()) or (
                            local_name and local_name.lower() == view_name_or_id.lower()
                        ):
                            existing_local_folder = folder
                            break

        if existing_local_folder:
            dst = existing_local_folder
            logger.info("Matching local view folder found at '%s'. Overwriting it in-place.", dst)
        else:
            dst = views_root / view_identifier
    else:
        dst /= view_identifier

    download_and_deconstruct_view(backend_api, view_identifier, dst)
    logger.info("View '%s' pulled and deconstructed successfully to %s", view_name_or_id, dst)


def download_and_deconstruct_view(backend_api: BackendAPI, view_identifier: str, dst: Path) -> None:
    """Download and deconstruct a view template from the SOAR environment directly to the destination path.

    Raises:
        typer.Exit: If the download or deconstruction fails.

    """
    logger.info("Downloading view (ID: %s)...", view_identifier)
    try:
        built_view_data = backend_api.download_view(view_identifier)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to download view '%s': %s", view_identifier, e)  # noqa: TRY400
        raise typer.Exit(1) from None

    if not isinstance(built_view_data, dict):
        logger.error("Downloaded view data is not a valid JSON object.")
        raise typer.Exit(1)

    try:
        normalized_view_data = _normalize_downloaded_view(built_view_data, backend_api)
        overview = Overview.from_built(normalized_view_data)
        logger.info("Deconstructing view to %s...", dst)
        deconstructor = ViewDeconstructor(overview, dst)
        deconstructor.deconstruct()
    except Exception as e:  # noqa: BLE001
        logger.error("Deconstruction failed for view '%s': %s", view_identifier, e)  # noqa: TRY400
        raise typer.Exit(1) from None


def _normalize_downloaded_view(flat_view: dict[str, Any], backend_api: BackendAPI) -> BuiltOverview:  # noqa: C901, PLR0912, PLR0914, PLR0915
    """Normalize flat camelCase view payload from SOAR REST API into BuiltOverview.

    Args:
        flat_view: The flat camelCase dictionary representing the view downloaded from SOAR.
        backend_api: The backend API client to fetch installed entities like Custom Fields.

    Returns:
        The normalized BuiltOverview structure.

    """
    installed_cf = []
    try:
        installed_cf = backend_api.list_custom_fields()
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to fetch installed custom fields during view normalization: %s", e)

    id_to_cf_name = {cf.get("id"): cf.get("displayName") for cf in installed_cf if cf.get("id") is not None}

    built_widgets = []
    for w in flat_view.get("widgets") or []:  # noqa: PLR1702
        meta = w.get("metadata") or {}
        config = w.get("config") or {}

        # Resolve Custom Fields
        cfs = config.get("customFields")
        if isinstance(cfs, list):
            for cf_item in cfs:
                if isinstance(cf_item, dict) and "id" in cf_item:
                    cf_id = cf_item.pop("id")
                    cf_name = id_to_cf_name.get(cf_id)
                    if cf_name:
                        cf_item["displayName"] = cf_name
                        # Auto-pull the dependent custom field
                        try:
                            import typer  # noqa: PLC0415

                            from mp.dev_env.sub_commands.custom_field.pull import (  # noqa: PLC0415
                                _download_and_save_custom_field,
                            )
                            _download_and_save_custom_field(backend_api, cf_id, None)
                        except typer.Exit:
                            logger.warning("Failed to auto-pull dependent custom field '%s' (ID: %s).", cf_name, cf_id)
                        except Exception as e:  # noqa: BLE001
                            logger.warning("Error auto-pulling custom field '%s' (ID: %s): %s", cf_name, cf_id, e)
                    else:
                        logger.warning("Could not resolve custom field ID %s to a displayName.", cf_id)
                        cf_item["id"] = cf_id  # Put it back

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
                    "Value": cond.get("value") if cond.get("value") is not None else cond.get("Value"),
                    "MatchType": (
                        cond.get("matchType")
                        if cond.get("matchType") is not None
                        else cond.get("MatchType")
                        if cond.get("MatchType") is not None
                        else 0
                    ),
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

    alert_rule_type = flat_view.get("alertRuleType")
    if alert_rule_type is not None:
        try:
            # It's a small list, so fetching all is fine
            rules = backend_api.list_alert_grouping_rules()
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to auto-pull dependent alert grouping rule (ID: %s): %s", alert_rule_type, e)
        else:
            from mp.dev_env.sub_commands.alert_grouping_rule.pull import _save_alert_grouping_rule  # noqa: PLC0415

            rule_data = next((r for r in rules if str(r.get("id")) == str(alert_rule_type)), None)
            if rule_data:
                _save_alert_grouping_rule(rule_data, None)
            else:
                logger.warning("Alert Grouping Rule ID %s not found on server during auto-pull.", alert_rule_type)

    overview_template: dict[str, Any] = {
        "Identifier": flat_view.get("identifier") or "",
        "Name": flat_view.get("name") or "",
        "Creator": flat_view.get("creator"),
        "PlaybookDefinitionIdentifier": flat_view.get("playbookIdentifier") or "",
        "Type": flat_view.get("type") or 0,
        "AlertRuleType": alert_rule_type,
        "Widgets": built_widgets,
        "Roles": flat_view.get("roles") or [],
    }

    return {
        "OverviewTemplate": cast("BuiltOverviewDetails", overview_template),
        "Roles": flat_view.get("roleNames") or [],
    }
