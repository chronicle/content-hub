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
from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

import mp.core.file_utils
from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.sub_commands.utils import get_backend_api_clean as get_backend_api
from mp.dev_env.utils import find_entity_identifier, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


@pull_app.command(name="alert-grouping-rule")
@track_command
def pull_alert_grouping_rule(
    rule_name_or_id: Annotated[
        str | None, typer.Argument(help="The alert grouping rule name or identifier to pull.")
    ] = None,
    dst: Annotated[
        Path | None,
        typer.Option(
            "--custom",
            help="Destination file. Defaults to 'content/alert_grouping_rules/<name>.yaml'.",
        ),
    ] = None,
    *,
    pull_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Pull all alert grouping rules from the environment.",
        ),
    ] = False,
    list_only: Annotated[
        bool,
        typer.Option(
            "--list",
            help="List all alert grouping rules available in the environment without pulling.",
        ),
    ] = False,
) -> None:
    """Pull alert grouping rules from the SOAR environment.

    Raises:
        typer.Exit: If the pull fails or invalid arguments are provided.

    """
    if rule_name_or_id is None and not pull_all and not list_only:
        logger.error("You must specify either a rule name/identifier, or use the --all or --list flags.")
        raise typer.Exit(1)

    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Fetching installed alert grouping rules...")
    try:
        installed_rules = backend_api.list_alert_grouping_rules()
    except Exception as e:
        logger.error("Failed to fetch installed alert grouping rules: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None

    if list_only:
        _list_alert_grouping_rules(installed_rules)
        return

    if pull_all:
        _pull_all_alert_grouping_rules(installed_rules, dst)
        return

    # Standard single pull
    if rule_name_or_id is None:
        logger.error("rule_name_or_id is required if not pulling or listing all")
        raise typer.Exit(1)
    matched_rules = []
    
    # First, try to match by ID if it's numeric
    try:
        numeric_id = int(rule_name_or_id)
        rule_data = next((r for r in installed_rules if r.get("id") == numeric_id), None)
        if rule_data:
            matched_rules.append(rule_data)
    except (ValueError, TypeError):
        pass
        
    # If not matched by ID, match by Category name (friendly display name or code)
    if not matched_rules:
        def match_category(user_input: str, rule: dict) -> bool:
            category = str(rule.get("category", "")).lower()
            category_mappings = {
                "all": "all",
                "alert type": "alerttype",
                "alert_type": "alerttype",
                "alerttype": "alerttype",
                "data source": "datasource",
                "data_source": "datasource",
                "datasource": "datasource",
                "product": "productname",
                "product name": "productname",
                "product_name": "productname",
                "productname": "productname"
            }
            normalized_input = category_mappings.get(user_input.lower(), user_input.lower())
            return normalized_input == category

        matched_rules = [r for r in installed_rules if match_category(rule_name_or_id, r)]

    if not matched_rules:
        logger.error("Could not find rule data matching '%s'", rule_name_or_id)
        raise typer.Exit(1)

    if len(matched_rules) > 1 and dst is not None and dst.suffix in {".yaml", ".yml"}:
        logger.error(
            "Multiple alert grouping rules found matching '%s', but target destination '%s' is a single file path.",
            rule_name_or_id,
            dst,
        )
        raise typer.Exit(1)

    for rule in matched_rules:
        _save_alert_grouping_rule(rule, dst)


def _list_alert_grouping_rules(installed_rules: list[dict]) -> None:
    logger.info("Available Alert Grouping Rules:")
    for rule in installed_rules:
        category = rule.get("category") or "Unknown"
        details = rule.get("categoryDetails") or []
        subs = [x.get("identifier") or x.get("displayName") for x in details if isinstance(x, dict) and (x.get("identifier") or x.get("displayName"))]
        subs_str = ", ".join(subs) if subs else "All"
        logger.info("  - Category: '%s' (Subcategories: %s)", category, subs_str)


def _pull_all_alert_grouping_rules(installed_rules: list[dict], dst: Path | None) -> None:
    logger.info("Pulling all %d alert grouping rules...", len(installed_rules))
    for rule in installed_rules:
        rule_id = rule.get("id")
        rule_name = rule.get("name") or rule_id
        if not rule_id:
            continue

        try:
            _save_alert_grouping_rule(rule, dst)
        except Exception as e:
            logger.error("Skipping alert grouping rule '%s' due to an error: %s", rule_name, e)  # noqa: TRY400

    logger.info("Successfully finished pulling all alert grouping rules.")


def _save_alert_grouping_rule(rule_data: dict, dst: Path | None) -> None:
    # Determine destination path using category and subcategories to keep it clean and prevent collisions
    category_name = rule_data.get("category") or "Unknown"
    subs = [x.get("identifier") for x in rule_data.get("categoryDetails", []) if x.get("identifier")]
    if subs:
        # Join sorted subcategories to create a clean suffix
        safe_subs = [str(s).replace(" ", "_").replace("/", "_").lower() for s in sorted(subs)]
        file_name = f"{category_name}_{'_'.join(safe_subs)}.yaml"
    else:
        file_name = f"{category_name}.yaml"

    if dst is None:
        rules_root = mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir()
        actual_dst = rules_root / file_name
    elif dst.is_dir() or dst.suffix not in {".yaml", ".yml"}:
        dst.mkdir(parents=True, exist_ok=True)
        actual_dst = dst / file_name
    else:
        actual_dst = dst

    logger.info("Saving alert grouping rule to %s...", actual_dst)
    # Clean up environment-specific fields to keep the files environment-agnostic
    rule_data.pop("id", None)
    rule_data.pop("name", None)
    try:
        actual_dst.parent.mkdir(parents=True, exist_ok=True)
        mp.core.file_utils.save_yaml(rule_data, actual_dst)
    except Exception as e:
        logger.error("Failed to save alert grouping rule to '%s': %s", actual_dst, e)  # noqa: TRY400
        raise typer.Exit(1) from None
