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

"""Typer application for describe-accept command."""

from __future__ import annotations

import logging
import pathlib  # ruff:ignore[typing-only-standard-library-import]
from typing import Annotated

import typer

from .accept import run_accept_regression_test

logger: logging.Logger = logging.getLogger(__name__)

app: typer.Typer = typer.Typer(
    help="Accept generated AI descriptions by overwriting official baseline files in resources/ai."
)


@app.command(
    name="action",
    help="Accept generated AI descriptions for action metadata.",
)
def accept_action(  # ruff:ignore[too-many-arguments]
    actions: Annotated[list[str] | None, typer.Argument(help="Action names")] = None,
    integration: Annotated[
        str | None, typer.Option("-i", "--integration", help="Integration name(s), comma-separated")
    ] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Accept all integrations in the marketplace, or all actions if an integration is specified",
        ),
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder.")] = None,
    dst: Annotated[
        pathlib.Path | None, typer.Option(help="Customize destination/test folder where candidate files are located.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate acceptance without modifying files on disk.")
    ] = False,
) -> None:
    """Run accept for action descriptions."""
    run_accept_regression_test(
        content_type="action",
        resource_names=actions,
        integration=integration,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        dry_run=dry_run,
    )


@app.command(
    name="connector",
    help="Accept generated AI descriptions for connector metadata.",
)
def accept_connector(  # ruff:ignore[too-many-arguments]
    connectors: Annotated[list[str] | None, typer.Argument(help="Connector names")] = None,
    integration: Annotated[
        str | None, typer.Option("-i", "--integration", help="Integration name(s), comma-separated")
    ] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Accept all integrations in the marketplace, or all connectors if an integration is specified",
        ),
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder.")] = None,
    dst: Annotated[
        pathlib.Path | None, typer.Option(help="Customize destination/test folder where candidate files are located.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate acceptance without modifying files on disk.")
    ] = False,
) -> None:
    """Run accept for connector descriptions."""
    run_accept_regression_test(
        content_type="connector",
        resource_names=connectors,
        integration=integration,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        dry_run=dry_run,
    )


@app.command(
    name="job",
    help="Accept generated AI descriptions for job metadata.",
)
def accept_job(  # ruff:ignore[too-many-arguments]
    jobs: Annotated[list[str] | None, typer.Argument(help="Job names")] = None,
    integration: Annotated[
        str | None, typer.Option("-i", "--integration", help="Integration name(s), comma-separated")
    ] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Accept all integrations in the marketplace, or all jobs if an integration is specified",
        ),
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder.")] = None,
    dst: Annotated[
        pathlib.Path | None, typer.Option(help="Customize destination/test folder where candidate files are located.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate acceptance without modifying files on disk.")
    ] = False,
) -> None:
    """Run accept for job descriptions."""
    run_accept_regression_test(
        content_type="job",
        resource_names=jobs,
        integration=integration,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        dry_run=dry_run,
    )


@app.command(
    name="integration",
    help="Accept generated AI descriptions for integration-level metadata.",
)
def accept_integration(  # ruff:ignore[too-many-arguments]
    integrations: Annotated[list[str] | None, typer.Argument(help="Integration names")] = None,
    integration: Annotated[
        str | None, typer.Option("-i", "--integration", help="Integration name(s), comma-separated")
    ] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Accept all integrations in the marketplace",
        ),
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder.")] = None,
    dst: Annotated[
        pathlib.Path | None, typer.Option(help="Customize destination/test folder where candidate files are located.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate acceptance without modifying files on disk.")
    ] = False,
) -> None:
    """Run accept for integration-level description."""
    target_ints = list(integrations or [])
    if integration:
        target_ints.extend([i.strip() for i in integration.split(",") if i.strip()])
    run_accept_regression_test(
        content_type="integration",
        resource_names=target_ints or None,
        integration=",".join(target_ints) if target_ints else None,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        dry_run=dry_run,
    )


@app.command(
    name="all-content",
    help="Accept generated AI descriptions for all content types (actions, connectors, jobs, integration).",
)
def accept_all_content(  # ruff:ignore[too-many-arguments]
    integrations: Annotated[list[str] | None, typer.Argument(help="Integration names")] = None,
    integration: Annotated[
        str | None, typer.Option("-i", "--integration", help="Integration name(s), comma-separated")
    ] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Accept all content for all integrations in the marketplace",
        ),
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder.")] = None,
    dst: Annotated[
        pathlib.Path | None, typer.Option(help="Customize destination/test folder where candidate files are located.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate acceptance without modifying files on disk.")
    ] = False,
) -> None:
    """Run accept for all content types."""
    target_ints = list(integrations or [])
    if integration:
        target_ints.extend([i.strip() for i in integration.split(",") if i.strip()])
    run_accept_regression_test(
        content_type="all-content",
        resource_names=target_ints or None,
        integration=",".join(target_ints) if target_ints else None,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        dry_run=dry_run,
    )
