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
import pathlib
from typing import Annotated

import typer

import mp.core.config
from mp.core import constants
from mp.describe.common.describe_all import get_all_integrations_paths
from mp.describe.common.utils.paths import get_integration_path

from .evaluator import EvaluationEngine
from .reporter import EvaluationReporter

logger: logging.Logger = logging.getLogger(__name__)

app: typer.Typer = typer.Typer(help="Commands for evaluating logical quality of AI descriptions.")


def _resolve_target_integrations(
    integration: str | None,
    *,
    all_marketplace: bool = False,
    src: pathlib.Path | None = None,
) -> list[str]:
    """Resolve target integration names to evaluate.

    Args:
        integration: Integration name.
        all_marketplace: Evaluate all marketplace integrations.
        src: Custom source folder.

    Returns:
        List of integration names.

    Raises:
        typer.Exit: If integration is not specified and neither --all nor --src is provided, or no integrations found.

    """
    if not integration and not all_marketplace and not src:
        logger.error("Please specify an integration name, --src, or use --all.")
        raise typer.Exit(code=1)

    if integration:
        get_integration_path(integration, src=src)
        return [integration]

    if all_marketplace or src:
        integration_paths = get_all_integrations_paths(src=src)
        if src and not integration_paths:
            logger.error("No integrations found in source '%s'", src)
            raise typer.Exit(code=1)
        return [p.name for p in integration_paths if p.is_dir()]

    return []


@app.command(
    name="evaluate",
    help="Evaluate the logical quality of generated AI descriptions against rule criteria.",
    no_args_is_help=True,
)
def evaluate(  # ruff: ignore[too-many-arguments]
    integration: Annotated[str | None, typer.Argument(help="Integration name to evaluate")] = None,
    *,
    all_marketplace: Annotated[
        bool, typer.Option("-a", "--all", help="Evaluate AI descriptions for all integrations in marketplace.")
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder to evaluate from.")] = None,
    action: Annotated[str | None, typer.Option("--action", help="Name of a single action to evaluate.")] = None,
    config_yaml: Annotated[
        pathlib.Path | None, typer.Option("--config-yaml", help="Path to AI evaluation YAML configuration.")
    ] = None,
    ruleset: Annotated[
        pathlib.Path | None,
        typer.Option(
            "--ruleset",
            help="Path to external evaluation ruleset YAML file. Defaults to bundled default_rules.yaml.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    db_path: Annotated[
        pathlib.Path | None, typer.Option("--db-path", help="Path to SQLite DB storage for rule evaluations.")
    ] = None,
    export_format: Annotated[
        str, typer.Option("--export-format", help="Format for exported evaluation report (markdown, json, html).")
    ] = "markdown",
    output_path: Annotated[
        pathlib.Path | None, typer.Option("--output-path", help="Destination file path for generated report.")
    ] = None,
    add_prompt: Annotated[bool, typer.Option("--add-prompt", help="Include prompt info in generated report.")] = False,
    use_batch_api: Annotated[
        bool, typer.Option("--use-batch-api", help="Use Google GenAI Batch API for rule evaluations.")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
) -> None:
    """Evaluate quality of generated AI descriptions for an integration."""
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    integrations_to_eval = _resolve_target_integrations(integration, all_marketplace=all_marketplace, src=src)
    db_target = db_path or pathlib.Path("rule_evaluations.db")

    if config_yaml and config_yaml.exists():
        logger.info("Using AI evaluation YAML config: %s", config_yaml)
    if ruleset and ruleset.exists():
        logger.info("Using AI evaluation ruleset YAML: %s", ruleset)
    else:
        logger.info("Using default bundled AI evaluation ruleset.")

    engine = EvaluationEngine()

    for target_integration in integrations_to_eval:
        logger.info("Starting evaluation for integration: %s", target_integration)
        report = engine.evaluate_integration(
            integration_id=target_integration,
            db_path=db_target,
            src=src,
            config_yaml=config_yaml,
            ruleset=ruleset,
            action=action,
            add_prompt=add_prompt,
            use_batch=use_batch_api,
        )

        if not output_path:
            int_path = pathlib.Path(str(get_integration_path(target_integration, src=src)))
            ai_dir = int_path / constants.RESOURCES_DIR / constants.AI_DIR
            ext = {"json": "json", "html": "html"}.get(export_format.lower(), "md")
            dest_file = ai_dir / f"evaluation_report.{ext}"
        else:
            dest_file = output_path

        EvaluationReporter.export_report(
            report=report,
            export_format=export_format,
            output_path=dest_file,
        )

        logger.debug("Evaluation report saved to: %s", dest_file)
        if not quiet:
            typer.echo(f"Evaluation report saved to: {dest_file}")
