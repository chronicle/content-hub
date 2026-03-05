from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.logging import RichHandler

from legacy_integration_describer.core import process_csv
from legacy_integration_describer.models import AppConfig

app = typer.Typer(help="Process partner integrations and generate AI descriptions.")
logger = logging.getLogger("legacy_integration_describer")


def setup_logger(verbose: bool, quiet: bool) -> None:  # noqa: FBT001
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


@app.command()
def execute(  # noqa: PLR0913, PLR0917
    tip_marketplace: str | None = typer.Option(None, help="tip-marketplace directory"),
    tip_marketplace_uncertified: str | None = typer.Option(
        None, help="tip-marketplace-uncertified directory"
    ),
    content_hub: str | None = typer.Option(None, help="content-hub directory"),
    source: str | None = typer.Option(None, "-s", "--source", help="Path to input CSVs folder"),
    destination: str | None = typer.Option(
        None, "-d", "--destination", help="Path to outputs folder"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),  # noqa: FBT001, FBT003
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output logs except errors"),  # noqa: FBT001, FBT003
) -> None:
    """Execute main entry point coordinating multi-repository version searches dynamically."""  # noqa: DOC501
    setup_logger(verbose, quiet)

    current_dir = Path(__file__).parent.parent
    root_dir = current_dir.parent.parent

    inputs_dir = Path(source).expanduser() if source else root_dir / "DesignPartnersIntegrations"
    outputs_dir = (
        Path(destination).expanduser() if destination else root_dir / "DesignPartnersIntegrations"
    )

    inputs_dir.mkdir(exist_ok=True, parents=True)
    outputs_dir.mkdir(exist_ok=True, parents=True)

    csv_files = list(inputs_dir.rglob("*_integrations.csv"))
    if not csv_files:
        logger.warning("No *_integrations.csv files found in %s", inputs_dir)
        raise typer.Exit

    repos_config: list[tuple[Path, str]] = []

    if tip_marketplace:
        repos_config.append((Path(tip_marketplace).expanduser(), "Integrations"))
    else:
        logger.warning(
            "Repository 'tip-marketplace' not specified. "
            "You should clone it to ensure integrations are found:\n"
            "    git clone sso://chronicle-soar/tip-marketplace"
        )

    if tip_marketplace_uncertified:
        repos_config.append((Path(tip_marketplace_uncertified).expanduser(), "Integrations"))
    else:
        logger.warning(
            "Repository 'tip-marketplace-uncertified' not specified. "
            "You should clone it to ensure integrations are found:\n"
            "    git clone sso://chronicle-soar/tip-marketplace-uncertified"
        )

    if content_hub:
        repos_config.extend([
            (Path(content_hub).expanduser(), "content/response_integrations/power_ups"),
            (Path(content_hub).expanduser(), "content/response_integrations/third_party"),
        ])
    else:
        logger.warning(
            "Repository 'content-hub' not specified. "
            "You should clone it to ensure integrations are found:\n"
            "    git clone https://github.com/chronicle/content-hub"
        )

    if not repos_config:
        logger.warning("No repositories provided. Please provide valid local repository paths.")

    config = AppConfig(inputs_dir=inputs_dir, outputs_dir=outputs_dir, repos_config=repos_config)

    for csv_file in csv_files:
        process_csv(csv_file, config)
