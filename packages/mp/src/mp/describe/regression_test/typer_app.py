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

"""Typer application for describe-regression-test command."""

from __future__ import annotations

import logging
import pathlib  # ruff:ignore[typing-only-standard-library-import]
from typing import Annotated

import typer

import mp.core.config

from .orchestrator import run_regression_test

logger: logging.Logger = logging.getLogger(__name__)

app: typer.Typer = typer.Typer(
    help="Perform regression testing by comparing baseline and test described YAML metadata."
)


@app.command(
    name="action",
    help="Run regression test comparing baseline and test YAML for action descriptions.",
)
def describe_action(  # ruff:ignore[too-many-arguments]
    actions: Annotated[list[str] | None, typer.Argument(help="Action names")] = None,
    integration: Annotated[str | None, typer.Option("-i", "--integration", help="Integration name")] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Test all integrations in the marketplace, or all actions if an integration is specified",
        ),
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder to compare from.")] = None,
    dst: Annotated[pathlib.Path | None, typer.Option(help="Customize destination/test folder to compare with.")] = None,
    override: Annotated[
        bool, typer.Option("--override", "-o", help="Rewrite content that already have their description.")
    ] = False,
    report_file: Annotated[
        pathlib.Path | None, typer.Option("--report-file", help="CSV report file path for results.")
    ] = None,
    run_describe: Annotated[
        bool, typer.Option("--run-describe/--no-run-describe", help="Run Gemini describe generation before comparing.")
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
) -> None:
    """Run regression test for action metadata.

    Args:
        actions: Action names.
        integration: Integration name.
        all_marketplace: Test all marketplace integrations.
        src: Source directory.
        dst: Test/Destination directory.
        override: Override flag.
        report_file: Report file path.
        run_describe: Run describe generation first.
        quiet: Quiet log option.
        verbose: Verbose log option.

    Raises:
        typer.Exit: If neither --integration nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if not integration and not all_marketplace:
        logger.error("Please specify either --integration or --all")
        raise typer.Exit(code=1)

    run_regression_test(
        content_type="action",
        resource_names=actions,
        integration=integration,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        override=override,
        report_file=report_file,
        run_describe=run_describe,
    )


@app.command(
    name="integration",
    help="Run regression test comparing baseline and test YAML for integration descriptions.",
)
def describe_integration(  # ruff:ignore[too-many-arguments]
    integrations: Annotated[list[str] | None, typer.Argument(help="Integration names")] = None,
    *,
    all_marketplace: Annotated[
        bool, typer.Option("-a", "--all", help="Test all integrations in the marketplace")
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder to compare from.")] = None,
    dst: Annotated[pathlib.Path | None, typer.Option(help="Customize destination/test folder to compare with.")] = None,
    override: Annotated[
        bool, typer.Option("--override", "-o", help="Rewrite content that already have their description.")
    ] = False,
    report_file: Annotated[
        pathlib.Path | None, typer.Option("--report-file", help="CSV report file path for results.")
    ] = None,
    run_describe: Annotated[
        bool, typer.Option("--run-describe/--no-run-describe", help="Run Gemini describe generation before comparing.")
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
) -> None:
    """Run regression test for integration metadata.

    Args:
        integrations: Integration names.
        all_marketplace: Test all marketplace integrations.
        src: Source directory.
        dst: Test/Destination directory.
        override: Override flag.
        report_file: Report file path.
        run_describe: Run describe generation first.
        quiet: Quiet log option.
        verbose: Verbose log option.

    Raises:
        typer.Exit: If neither integrations nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if not integrations and not all_marketplace:
        logger.error("Please specify either integrations or --all")
        raise typer.Exit(code=1)

    run_regression_test(
        content_type="integration",
        resource_names=integrations,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        override=override,
        report_file=report_file,
        run_describe=run_describe,
    )


@app.command(
    name="connector",
    help="Run regression test comparing baseline and test YAML for connector descriptions.",
)
def describe_connector(  # ruff:ignore[too-many-arguments]
    connectors: Annotated[list[str] | None, typer.Argument(help="Connector names")] = None,
    integration: Annotated[str | None, typer.Option("-i", "--integration", help="Integration name")] = None,
    *,
    all_marketplace: Annotated[
        bool, typer.Option("-a", "--all", help="Test all integrations in the marketplace")
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder to compare from.")] = None,
    dst: Annotated[pathlib.Path | None, typer.Option(help="Customize destination/test folder to compare with.")] = None,
    override: Annotated[
        bool, typer.Option("--override", "-o", help="Rewrite content that already have their description.")
    ] = False,
    report_file: Annotated[
        pathlib.Path | None, typer.Option("--report-file", help="CSV report file path for results.")
    ] = None,
    run_describe: Annotated[
        bool, typer.Option("--run-describe/--no-run-describe", help="Run Gemini describe generation before comparing.")
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
) -> None:
    """Run regression test for connector metadata.

    Args:
        connectors: Connector names.
        integration: Integration name.
        all_marketplace: Test all marketplace integrations.
        src: Source directory.
        dst: Test/Destination directory.
        override: Override flag.
        report_file: Report file path.
        run_describe: Run describe generation first.
        quiet: Quiet log option.
        verbose: Verbose log option.

    Raises:
        typer.Exit: If neither --integration nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if not integration and not all_marketplace:
        logger.error("Please specify either --integration or --all")
        raise typer.Exit(code=1)

    run_regression_test(
        content_type="connector",
        resource_names=connectors,
        integration=integration,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        override=override,
        report_file=report_file,
        run_describe=run_describe,
    )


@app.command(
    name="job",
    help="Run regression test comparing baseline and test YAML for job descriptions.",
)
def describe_job(  # ruff:ignore[too-many-arguments]
    jobs: Annotated[list[str] | None, typer.Argument(help="Job names")] = None,
    integration: Annotated[str | None, typer.Option("-i", "--integration", help="Integration name")] = None,
    *,
    all_marketplace: Annotated[
        bool, typer.Option("-a", "--all", help="Test all integrations in the marketplace")
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder to compare from.")] = None,
    dst: Annotated[pathlib.Path | None, typer.Option(help="Customize destination/test folder to compare with.")] = None,
    override: Annotated[
        bool, typer.Option("--override", "-o", help="Rewrite content that already have their description.")
    ] = False,
    report_file: Annotated[
        pathlib.Path | None, typer.Option("--report-file", help="CSV report file path for results.")
    ] = None,
    run_describe: Annotated[
        bool, typer.Option("--run-describe/--no-run-describe", help="Run Gemini describe generation before comparing.")
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
) -> None:
    """Run regression test for job metadata.

    Args:
        jobs: Job names.
        integration: Integration name.
        all_marketplace: Test all marketplace integrations.
        src: Source directory.
        dst: Test/Destination directory.
        override: Override flag.
        report_file: Report file path.
        run_describe: Run describe generation first.
        quiet: Quiet log option.
        verbose: Verbose log option.

    Raises:
        typer.Exit: If neither --integration nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if not integration and not all_marketplace:
        logger.error("Please specify either --integration or --all")
        raise typer.Exit(code=1)

    run_regression_test(
        content_type="job",
        resource_names=jobs,
        integration=integration,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        override=override,
        report_file=report_file,
        run_describe=run_describe,
    )


@app.command(
    name="all-content",
    help="Run regression test comparing baseline and test YAML for all content.",
)
def describe_all_content(  # ruff:ignore[too-many-arguments]
    integrations: Annotated[list[str] | None, typer.Argument(help="Integration names")] = None,
    *,
    all_marketplace: Annotated[
        bool, typer.Option("-a", "--all", help="Test all content for all integrations in the marketplace")
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder to compare from.")] = None,
    dst: Annotated[pathlib.Path | None, typer.Option(help="Customize destination/test folder to compare with.")] = None,
    override: Annotated[
        bool, typer.Option("--override", "-o", help="Rewrite content that already have their description.")
    ] = False,
    report_file: Annotated[
        pathlib.Path | None, typer.Option("--report-file", help="CSV report file path for results.")
    ] = None,
    run_describe: Annotated[
        bool, typer.Option("--run-describe/--no-run-describe", help="Run Gemini describe generation before comparing.")
    ] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
) -> None:
    """Run regression test for all content in integrations.

    Args:
        integrations: Integration names.
        all_marketplace: Test all content for all marketplace integrations.
        src: Source directory.
        dst: Test/Destination directory.
        override: Override flag.
        report_file: Report file path.
        run_describe: Run describe generation first.
        quiet: Quiet log option.
        verbose: Verbose log option.

    Raises:
        typer.Exit: If neither integrations nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if not integrations and not all_marketplace:
        logger.error("Please specify either integrations or --all")
        raise typer.Exit(code=1)

    run_regression_test(
        content_type="all-content",
        resource_names=integrations,
        all_marketplace=all_marketplace,
        src=src,
        dst=dst,
        override=override,
        report_file=report_file,
        run_describe=run_describe,
    )
