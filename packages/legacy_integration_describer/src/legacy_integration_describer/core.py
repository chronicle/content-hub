from __future__ import annotations

import csv
import logging
import subprocess  # noqa: S404
from typing import TYPE_CHECKING

from legacy_integration_describer.git_utils import checkout_integration_version
from legacy_integration_describer.models import AppConfig, IntegrationRequest, IntegrationResult
from legacy_integration_describer.mp_utils import parse_ai_metadata, run_mp_describe


if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def ingest_partner_integrations(csv_path: Path) -> list[IntegrationRequest]:
    """Parse Design Partner explicit historical records avoiding custom internal dependencies.

    Returns:
        list[IntegrationRequest]: Formatted inputs.

    """
    requests = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("IsCustom", "").strip().lower() == "true":
                continue
            requests.append(
                IntegrationRequest(identifier=row["Identifier"], version=row["Version"])
            )
    return requests


def write_csv_output(
    results_dir: Path, partner_name: str, results: list[IntegrationResult]
) -> None:
    """Store dynamically generated AI descriptors centrally organized per partner format."""
    out_csv = results_dir / f"{partner_name}_output.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Integration Name",
                "Action Name",
                "AI Description",
                "AI Categories",
                "Entity Usage",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(result.to_row())
    logger.info("Wrote output to %s", out_csv)


def write_error_manifest(results_dir: Path, partner_name: str, errors: list[str]) -> None:
    """Gracefully record missing parameters tracking historical version discrepancies visually."""
    out_err = results_dir / f"{partner_name}_errors.txt"
    with out_err.open("w", encoding="utf-8") as f:
        if errors:
            f.write("Errors Summary:\n")
            f.write("\n".join(errors))
            f.write("\n")
            logger.warning("Wrote errors to %s", out_err)
        else:
            f.write("No errors.")


def process_csv(csv_path: Path, config: AppConfig) -> None:
    """Orchestrate parsing operations strictly over inputs producing output AI definitions."""
    partner_name = csv_path.stem.split("_integrations")[0]
    # Place all assets within the isolated output partner dir natively
    partner_dir = config.outputs_dir / partner_name

    integrations_dir = partner_dir / "integrations"
    results_dir = partner_dir / "results"
    integrations_dir.mkdir(exist_ok=True, parents=True)
    results_dir.mkdir(exist_ok=True, parents=True)

    logger.info("\n==============================")
    logger.info("Processing partner: %s", partner_name)
    logger.info("==============================")

    output_rows = []
    errors: list[str] = []

    requests = ingest_partner_integrations(csv_path)

    for request in requests:
        logger.info(
            "Processing integration: %s (Requested v%s)", request.identifier, request.version
        )
        dest_dir = integrations_dir / request.identifier

        if dest_dir.exists():
            subprocess.run(["rm", "-rf", str(dest_dir)], check=False)  # noqa: S603, S607

        success = checkout_integration_version(request, dest_dir, config, errors)
        if not success:
            logger.warning("Skipping %s due to checkout failure.", request.identifier)
            continue

    for integration_dir in integrations_dir.iterdir():
        if not integration_dir.is_dir():
            continue

        results = parse_ai_metadata(integration_dir, errors)
        output_rows.extend(results)

    if output_rows:
        write_csv_output(results_dir, partner_name, output_rows)
    else:
        logger.info("No output to write for %s", partner_name)

    write_error_manifest(results_dir, partner_name, errors)
