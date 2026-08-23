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

"""Accept module for promoting generated AI descriptions to official baselines."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from rich.console import Console
from rich.table import Table

from mp.core.constants import AI_DIR, RESOURCES_DIR
from mp.describe.common.describe_all import get_all_integrations_paths
from mp.describe.common.utils.paths import get_integration_path

from .orchestrator import METADATA_FILES, _resolve_test_file

logger: logging.Logger = logging.getLogger(__name__)


def _remove_empty_parents(path: Path, stop_at: Path) -> None:
    """Remove empty parent directories up to stop_at.

    Args:
        path: Starting directory path.
        stop_at: Top-level boundary path where cleanup stops.

    """
    curr = path
    stop_resolved = stop_at.resolve()
    while curr.resolve() != stop_resolved and curr.exists():
        try:
            if not any(curr.iterdir()):
                curr.rmdir()
                curr = curr.parent
            else:
                break
        except OSError:
            break


def _find_local_integration_fallback(name: str) -> Path | None:
    """Fallback search for integration in local repo if global config path fails.

    Args:
        name: Integration name.

    Returns:
        Path | None: Local path if found, None otherwise.

    """
    for base in [
        Path.cwd() / "content" / "response_integrations",
        Path.cwd() / "integrations",
    ]:
        if not base.exists():
            continue
        for sub in base.rglob(name):
            if sub.is_dir() and ((sub / "definition.yaml").exists() or (sub / "resources").exists()):
                return sub
    return None


def run_accept_regression_test(  # ruff:ignore[complex-structure,too-many-arguments]
    content_type: str,
    resource_names: list[str] | None = None,
    integration: str | None = None,
    *,
    all_marketplace: bool = False,
    src: Path | None = None,
    dst: Path | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Accept generated AI descriptions by overwriting official baseline files.

    Args:
        content_type: Type of content to accept ('action', 'integration', 'connector', 'job', 'all-content').
        resource_names: Specific resource names if passed.
        integration: Specific integration name if passed.
        all_marketplace: Whether to check all integrations.
        src: Custom source path.
        dst: Custom destination/test path where candidate files are located.
        dry_run: If True, simulate operations without modifying files on disk.

    Returns:
        list[str]: List of official baseline file paths that were accepted/updated.

    """
    target_dst: Path = dst or Path("test_descriptions")
    console = Console(width=160)

    integrations_to_check: list[str] = []
    if integration:
        integrations_to_check = [i.strip() for i in integration.split(",") if i.strip()]
    elif content_type in {"integration", "all-content"} and resource_names and not all_marketplace:
        integrations_to_check = resource_names
    else:
        paths: list[Path] = get_all_integrations_paths(src=src)
        integrations_to_check = [p.name for p in paths]

    metadata_filenames: list[str] = METADATA_FILES.get(content_type, METADATA_FILES["all-content"])

    accepted_rows: list[tuple[str, str, str, str]] = []
    accepted_files: list[str] = []

    for int_name in integrations_to_check:
        try:
            int_path_anyio = get_integration_path(int_name, src=src)
            int_path = Path(str(int_path_anyio))
        except Exception:  # ruff:ignore[blind-except]
            fallback_path = _find_local_integration_fallback(int_name)
            if fallback_path is None:
                logger.warning("Could not find path for integration %s", int_name)
                continue
            int_path = fallback_path

        baseline_ai_dir = int_path / RESOURCES_DIR / AI_DIR

        for metadata_filename in metadata_filenames:
            test_file: Path = _resolve_test_file(int_name, metadata_filename, target_dst)
            if not test_file.exists():
                continue

            baseline_file: Path = baseline_ai_dir / metadata_filename
            status_text = "DRY-RUN (would overwrite)" if dry_run else "ACCEPTED"

            if not dry_run:
                baseline_ai_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(test_file, baseline_file)

                # Remove accepted candidate test file from test_descriptions
                test_file.unlink()
                _remove_empty_parents(test_file.parent, target_dst)

            accepted_files.append(str(baseline_file))
            accepted_rows.append((int_name, metadata_filename, str(baseline_file), status_text))

    if accepted_rows:
        table = Table(title="AI Metadata Acceptance Summary")
        table.add_column("Integration", style="cyan", no_wrap=True)
        table.add_column("Metadata File", style="blue", no_wrap=True)
        table.add_column("Target Baseline Path", style="magenta", no_wrap=True)
        table.add_column("Status", style="bold green" if not dry_run else "bold yellow", no_wrap=True)

        for row in accepted_rows:
            table.add_row(*row)

        console.print(table)
        console.print(
            f"\n[bold green]Accepted {len(accepted_rows)} file(s). "
            f"{'Simulation complete.' if dry_run else 'Official baselines updated!'}[/bold green]\n"
        )
    else:
        console.print(
            f"\n[bold green]No generated test descriptions found in '{target_dst}'. "
            "All baselines are already up to date![/bold green]\n"
        )

    return accepted_files
