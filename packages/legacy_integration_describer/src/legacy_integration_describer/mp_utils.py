from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml
from legacy_integration_describer.models import AppConfig, IntegrationResult

from mp.describe.action.describe_all import describe_all_actions


logger = logging.getLogger(__name__)


def purge_existing_definitions(integration_dir: Path) -> None:
    """Hard delete existing descriptions first."""
    for fpath in integration_dir.rglob("actions_ai_description.yaml"):
        fpath.unlink()
    for fpath in integration_dir.rglob("actions_ai_metadata.yaml"):
        fpath.unlink()


def run_mp_describe(integration_dir: Path, errors: list[str]) -> bool:
    """Execute the mp framework regenerating the AI payloads internally via Gemini APIs.

    Returns:
        bool: True if process executed naturally.

    """
    logger.info("Running `mp describe` for %s...", integration_dir.name)
    purge_existing_definitions(integration_dir)

    try:
        asyncio.run(describe_all_actions(src=integration_dir, override=True))
    except Exception as e:
        logger.exception("Failed to run mp describe natively for %s", integration_dir.name)
        errors.append(f"{integration_dir.name}: `mp describe` failed: {e}")
        return False

    return True


def format_scalar_lists(field_data: list | str) -> str:
    """Safely format dictionary lists into scalar string components.

    Returns:
        str: Output flat mapped natively.

    """
    if isinstance(field_data, list):
        return ", ".join(field_data)
    if isinstance(field_data, dict):
        return str(field_data)
    return str(field_data)


def parse_ai_metadata(integration_dir: Path, errors: list[str]) -> list[IntegrationResult]:
    """Parse out cleanly constructed IntegrationResults from unstructured AI schema structures.

    Returns:
        list[IntegrationResult]: Output cleanly.

    """
    results = []

    ai_data_files = list(integration_dir.rglob("actions_ai_description.yaml")) + list(
        integration_dir.rglob("actions_ai_metadata.yaml")
    )
    if not ai_data_files:
        errors.append(
            f"{integration_dir.name}: No actions_ai_description.yaml file found after generation."
        )
        return results

    for ai_file in ai_data_files:
        try:
            with Path(ai_file).open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            for action_name, details in data.items():
                if not isinstance(details, dict):
                    continue

                entity_usage = format_scalar_lists(details.get("entity_usage", ""))
                categories = format_scalar_lists(details.get("categories", ""))

                results.append(
                    IntegrationResult(
                        integration_name=integration_dir.name,
                        action_name=action_name,
                        description=details.get("description", ""),
                        categories=categories,
                        entity_usage=entity_usage,
                    )
                )
        except Exception as e:
            msg = f"{integration_dir.name}: Failed to parse generated AI yaml map: {e}"
            errors.append(msg)
            logger.exception(msg)

    return results
