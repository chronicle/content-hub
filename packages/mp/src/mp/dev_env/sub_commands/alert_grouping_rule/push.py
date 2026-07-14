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
import logging
from pathlib import Path
from typing import Annotated

import typer

import mp.core.file_utils
from mp.dev_env.sub_commands.push import push_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


@push_app.command(name="alert-grouping-rule")
@track_command
def push_alert_grouping_rule(  # noqa: C901, PLR0915
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
    allow_create: Annotated[
        bool,
        typer.Option(
            "--allow-create",
            help="Allow creating new alert grouping rules if they do not exist on the platform.",
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
            _push_single_alert_grouping_rule(f, allow_create)
        
        logger.info("Successfully finished pushing all alert grouping rules.")
        return

    # Standard single push
    rule_file = Path(rule_file_or_name)
    if not rule_file.is_file():
        # Try resolving by name in the default alert grouping rules directory
        safe_name = rule_file_or_name.replace("/", "_").replace(" ", "_")
        candidate_file = rules_root / f"{safe_name}.yaml"
        if candidate_file.is_file():
            rule_file = candidate_file
        else:
            logger.error("Alert grouping rule file not found at '%s' or '%s'", rule_file_or_name, candidate_file)
            raise typer.Exit(1)
            
    _push_single_alert_grouping_rule(rule_file, allow_create)


def _push_single_alert_grouping_rule(rule_file: Path, allow_create: bool) -> None:
    logger.info("Loading alert grouping rule YAML from '%s'...", rule_file)
    try:
        rule_data = mp.core.file_utils.load_yaml_file(rule_file)
    except Exception as e:
        logger.exception("Failed to parse alert grouping rule YAML")
        raise typer.Exit(1) from e

    if not isinstance(rule_data, dict):
        logger.error("Alert grouping rule data must be a dictionary.")
        raise typer.Exit(1)

    config = load_dev_env_config()
    backend_api = get_backend_api(config)

    logger.info("Checking if alert grouping rule exists on server...")
    try:
        installed_rules = backend_api.list_alert_grouping_rules()
    except Exception as e:
        logger.exception("Failed to fetch installed alert grouping rules")
        raise typer.Exit(1) from e

    rule_name = rule_data.get("displayName")
    if not rule_name:
        logger.error("Alert grouping rule data is missing a 'displayName' field.")
        raise typer.Exit(1)

    existing_id = None
    for rule in installed_rules:
        if str(rule.get("displayName")).lower() == rule_name.lower():
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
        except Exception as e:
            logger.exception("Failed to update alert grouping rule '%s'", rule_name)
            raise typer.Exit(1) from e
    else:
        if not allow_create:
            logger.error("Alert grouping rule '%s' not found on the platform. Skipping because --allow-create was not specified.", rule_name)
            raise typer.Exit(1)
            
        logger.info("Creating new alert grouping rule...")
        try:
            backend_api.create_alert_grouping_rule(rule_data)
        except Exception as e:
            logger.exception("Failed to create alert grouping rule '%s'", rule_name)
            raise typer.Exit(1) from e

    logger.info("Alert grouping rule '%s' pushed successfully.", rule_name)
