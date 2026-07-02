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
from mp.dev_env.utils import find_entity_identifier, get_backend_api, load_dev_env_config
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


@push_app.command(name="alert-grouping-rule")
@track_command
def push_alert_grouping_rule(
    rule_file_or_name: Annotated[str, typer.Argument(help="The alert grouping rule YAML file path or name to push.")],
) -> None:
    """Push an alert grouping rule to the SOAR environment.

    Raises:
        typer.Exit: If the push fails.

    """
    rule_file = Path(rule_file_or_name)
    if not rule_file.is_file():
        # Try resolving by name in the default alert grouping rules directory
        rules_root = mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir()
        safe_name = rule_file_or_name.replace("/", "_").replace(" ", "_")
        candidate_file = rules_root / f"{safe_name}.yaml"
        if candidate_file.is_file():
            rule_file = candidate_file
        else:
            logger.error("Alert grouping rule file not found at '%s' or '%s'", rule_file_or_name, candidate_file)
            raise typer.Exit(1)

    logger.info("Loading alert grouping rule YAML...")
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

    rule_name = rule_data.get("name")
    if not rule_name:
        logger.error("Alert grouping rule data is missing a 'name' field.")
        raise typer.Exit(1)

    existing_id = None
    with contextlib.suppress(typer.Exit):
        existing_id = find_entity_identifier(rule_name, installed_rules, "Alert Grouping Rule")

    if existing_id is not None:
        logger.info("Updating existing alert grouping rule (ID: %s)...", existing_id)
        try:
            backend_api.update_alert_grouping_rule(int(existing_id), rule_data)
        except Exception as e:
            logger.exception("Failed to update alert grouping rule '%s'", rule_name)
            raise typer.Exit(1) from e
    else:
        logger.info("Creating new alert grouping rule...")
        try:
            backend_api.create_alert_grouping_rule(rule_data)
        except Exception as e:
            logger.exception("Failed to create alert grouping rule '%s'", rule_name)
            raise typer.Exit(1) from e

    logger.info("Alert grouping rule '%s' pushed successfully.", rule_name)
