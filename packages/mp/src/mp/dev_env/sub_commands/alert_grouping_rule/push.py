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


@push_app.command(name="alert-grouping-rule")
@track_command
def push_alert_grouping_rule(
    rule_file_or_name: Annotated[
        str | None, typer.Argument(help="The alert grouping rule YAML file path or name to push.")
    ] = None,
    *,
    push_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Push all alert grouping rules from the local directory to the environment.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Force creating new alert grouping rules if they do not exist on the platform.",
        ),
    ] = False,
) -> None:
    """Push alert grouping rule(s) to the SOAR environment.

    Raises:
        typer.Exit: If the push fails.

    """
    if rule_file_or_name is None and not push_all:
        logger.error("You must specify either an alert grouping rule name/file, or use the --all flag.")
        raise typer.Exit(1)

    rules_root = mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir()

    if push_all:
        logger.info("Pushing all alert grouping rules from '%s'...", rules_root)
        if not rules_root.exists() or not rules_root.is_dir():
            logger.error("Alert grouping rules directory not found.")
            raise typer.Exit(1)

        yaml_files = list(rules_root.glob("*.yaml")) + list(rules_root.glob("*.yml"))
        if not yaml_files:
            logger.info("No alert grouping rule files found to push.")
            return

        for f in yaml_files:
            _push_single_alert_grouping_rule(f, force)

        logger.info("Successfully finished pushing all alert grouping rules.")
        return

    # Standard single push
    assert rule_file_or_name is not None  # noqa: S101
    rule_file = Path(rule_file_or_name)
    if rule_file.is_file():
        _push_single_alert_grouping_rule(rule_file, force)
    else:
        # Resolve by name/prefix lookup
        # E.g. rule_file_or_name = "AlertType" -> matches AlertType.yaml, AlertType_malware.yaml, etc.
        safe_name = rule_file_or_name.replace("/", "_").replace(" ", "_")
        matched_files = list(rules_root.glob(f"{safe_name}*.yaml")) + list(rules_root.glob(f"{safe_name}*.yml"))
        if not matched_files:
            logger.error("No alert grouping rule files matching '%s' found in '%s'", rule_file_or_name, rules_root)
            raise typer.Exit(1)

        for f in matched_files:
            _push_single_alert_grouping_rule(f, force)


def _push_single_alert_grouping_rule(rule_file: Path, force: bool) -> None:  # noqa: C901, FBT001, PLR0912, PLR0915
    logger.info("Loading alert grouping rule YAML from '%s'...", rule_file)
    try:
        rule_data = mp.core.file_utils.load_yaml_file(rule_file)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to parse alert grouping rule YAML: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None

    if not isinstance(rule_data, dict):
        logger.error("Alert grouping rule data must be a dictionary.")
        raise typer.Exit(1)

    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Checking if alert grouping rule exists on server...")
    try:
        installed_rules = backend_api.list_alert_grouping_rules()
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to fetch installed alert grouping rules: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None

    rule_category = rule_data.get("category")
    if not rule_category:
        logger.error("Alert grouping rule data is missing a 'category' field.")
        raise typer.Exit(1)

    local_subs = {x.get("identifier") for x in rule_data.get("categoryDetails", []) if x.get("identifier")}

    existing_id = None
    for rule in installed_rules:
        if str(rule.get("category")).lower() == str(rule_category).lower():
            server_subs = {x.get("identifier") for x in rule.get("categoryDetails", []) if x.get("identifier")}
            if server_subs == local_subs:
                existing_id = rule.get("id")
                break

    if existing_id is not None:
        logger.info("Updating existing alert grouping rule (ID: %s)...", existing_id)
        try:
            numeric_id = int(existing_id)
            # Update the payload with the target environment's ID and name
            rule_data["id"] = numeric_id
            rule_data["name"] = f"projects//locations//instances//alertGroupingRules/{numeric_id}"

            backend_api.update_alert_grouping_rule(numeric_id, rule_data)
        except (ValueError, TypeError) as e:
            logger.error("Invalid existing ID '%s': Must be a numeric value.", existing_id)  # noqa: TRY400
            raise typer.Exit(1) from e
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to update alert grouping rule for category '%s': %s", rule_category, e)  # noqa: TRY400
            raise typer.Exit(1) from None
    else:
        if not force:
            logger.error("=" * 80)
            logger.error("[VALIDATION ERROR] Alert Grouping Rule Not Installed")
            logger.error("Alert grouping rule for category '%s' not found on the platform.", rule_category)
            logger.error(
                "Creation of new alert grouping rules is blocked by default. Use the --force flag to force creation."
            )
            logger.error("=" * 80)
            raise typer.Exit(1)

        logger.info("Creating new alert grouping rule...")
        try:
            backend_api.create_alert_grouping_rule(rule_data)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to create alert grouping rule for category '%s': %s", rule_category, e)  # noqa: TRY400
            raise typer.Exit(1) from None

    logger.info("Alert grouping rule for category '%s' pushed successfully.", rule_category)
