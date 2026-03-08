from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler

from legacy_integration_describer.core import process_csv
from legacy_integration_describer.models import AppConfig

app = typer.Typer(help="Process partner integrations and generate AI descriptions.")
logger = logging.getLogger("legacy_integration_describer")


@app.command()
def execute(  # noqa: PLR0913
    tip_marketplace: Annotated[str | None, typer.Option(help="tip-marketplace directory")] = None,
    tip_marketplace_uncertified: Annotated[
        str | None, typer.Option(help="tip-marketplace-uncertified directory")
    ] = None,
    content_hub: Annotated[str | None, typer.Option(help="content-hub directory")] = None,
    source: Annotated[
        str | None, typer.Option("-s", "--source", help="Path to input CSVs folder")
    ] = None,
    destination: Annotated[
        str | None, typer.Option("-d", "--destination", help="Path to outputs folder")
    ] = None,
    *,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose debug logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress output logs except errors")
    ] = False,
) -> None:
    """Execute the main entry point coordinating multi-repository version searches dynamically.

    Raises:
        typer.Exit: If no *_integrations.csv files are found in the input directory.

    """
    setup_logger(verbose=verbose, quiet=quiet)

    current_dir = Path(__file__).parent.parent.parent
    inputs_dir = Path(source).expanduser() if source else current_dir / "inputs"
    outputs_dir = Path(destination).expanduser() if destination else current_dir / "outputs"

    inputs_dir.mkdir(exist_ok=True, parents=True)
    outputs_dir.mkdir(exist_ok=True, parents=True)

    csv_files = list(inputs_dir.rglob("*_integrations.csv"))
    if not csv_files:
        logger.warning("No *_integrations.csv files found in %s", inputs_dir)
        raise typer.Exit

    repos_config: list[tuple[Path, str]] = []

    tm_path = (
        Path(tip_marketplace).expanduser()
        if tip_marketplace
        else Path("~/repos/tip-marketplace").expanduser()
    )
    if tm_path.exists():
        repos_config.append((tm_path, "Integrations"))
    else:
        logger.warning(
            "Repository 'tip-marketplace' not specified. "
            "You should clone it to ensure integrations are found:\n"
            "    git clone sso://chronicle-soar/tip-marketplace %s",
            tm_path,
        )

    tmu_path = (
        Path(tip_marketplace_uncertified).expanduser()
        if tip_marketplace_uncertified
        else Path("~/repos/tip-marketplace-uncertified").expanduser()
    )
    if tmu_path.exists():
        repos_config.append((tmu_path, "Integrations"))
    else:
        logger.warning(
            "Repository 'tip-marketplace-uncertified' not specified. "
            "You should clone it to ensure integrations are found:\n"
            "    git clone sso://chronicle-soar/tip-marketplace-uncertified %s",
            tmu_path,
        )

    ch_path = (
        Path(content_hub).expanduser() if content_hub else Path("~/repos/content-hub").expanduser()
    )
    if ch_path.exists():
        repos_config.extend([
            (ch_path, "content/response_integrations/power_ups"),
            (ch_path, "content/response_integrations/third_party"),
        ])
    else:
        logger.warning(
            "Repository 'content-hub' not specified. "
            "You should clone it to ensure integrations are found:\n"
            "    git clone https://github.com/chronicle/content-hub %s",
            ch_path,
        )

    if not repos_config:
        logger.warning("No repositories provided. Please provide valid local repository paths.")

    config = AppConfig(inputs_dir=inputs_dir, outputs_dir=outputs_dir, repos_config=repos_config)

    for csv_file in csv_files:
        process_csv(csv_file, config)


def setup_logger(*, verbose: bool, quiet: bool) -> None:
    """Configure system-wide explicit logging frameworks targeting Rich constraints."""
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR

    # Clear previously set handlers naturally assigned if any
    root_val = logging.getLogger()
    if root_val.hasHandlers():
        root_val.handlers.clear()

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
