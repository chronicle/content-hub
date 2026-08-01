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

"""Orchestrator for running regression testing on described YAML metadata."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from mp.core.constants import AI_DIR, RESOURCES_DIR
from mp.describe.action.describe import DescribeAction
from mp.describe.common.describe_all import get_all_integrations_paths
from mp.describe.common.utils.paths import get_integration_path
from mp.describe.connector.describe import DescribeConnector
from mp.describe.job.describe import DescribeJob

from .comparator import RegressionIssue, compare_yaml_files, write_regression_report_csv
from .judge import TextCandidate, run_judge_evaluation_sync

logger: logging.Logger = logging.getLogger(__name__)

MAX_DISPLAY_ISSUES: int = 20

METADATA_FILES: dict[str, list[str]] = {
    "action": ["actions_ai_description.yaml"],
    "integration": ["integration_ai_description.yaml"],
    "connector": ["connectors_ai_description.yaml"],
    "job": ["jobs_ai_description.yaml"],
    "all-content": [
        "actions_ai_description.yaml",
        "integration_ai_description.yaml",
        "connectors_ai_description.yaml",
        "jobs_ai_description.yaml",
    ],
}


def _resolve_test_file(
    integration_name: str,
    metadata_filename: str,
    dst: Path,
) -> Path:
    """Resolve the test YAML file path based on destination directory settings.

    Args:
        integration_name: Name of the integration.
        metadata_filename: Name of the metadata YAML file.
        dst: Destination directory path.

    Returns:
        Path: Resolved test file path.

    """
    candidates: list[Path] = [
        dst / integration_name / RESOURCES_DIR / AI_DIR / metadata_filename,
        dst / integration_name / metadata_filename,
        dst / RESOURCES_DIR / AI_DIR / metadata_filename,
        dst / metadata_filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


MIN_PATH_PARTS: int = 2


def format_integration_and_component(path_str: str) -> tuple[str, str]:
    """Extract integration name and component type from metadata file path.

    Args:
        path_str: Metadata file path string.

    Returns:
        tuple[str, str]: A tuple of (integration_name, component_type).

    """
    p = Path(path_str)
    name_lower = p.name.lower()
    component = "metadata"
    if "actions_" in name_lower:
        component = "action"
    elif "connectors_" in name_lower:
        component = "connector"
    elif "jobs_" in name_lower:
        component = "job"
    elif "integration_" in name_lower:
        component = "integration"

    parts = p.parts
    integration_name = p.stem
    if "resources" in parts:
        idx = parts.index("resources")
        if idx > 0:
            integration_name = parts[idx - 1]
    elif len(parts) >= MIN_PATH_PARTS:
        integration_name = parts[-MIN_PATH_PARTS]

    return integration_name, component


async def run_describe_generation(  # ruff:ignore[too-many-arguments]
    content_type: str,
    resource_names: list[str] | None,
    integration: str | None,
    *,
    all_marketplace: bool,
    src: Path | None,
    dst: Path,
    override: bool,
) -> None:
    """Run the underlying describe generation if test files need to be produced.

    Args:
        content_type: Content type ('action', 'integration', 'connector', 'job', 'all-content').
        resource_names: Resource names argument if provided.
        integration: Integration name if provided.
        all_marketplace: Whether --all flag was set.
        src: Source directory path.
        dst: Destination directory path.
        override: Override flag.

    """
    gen_override: bool = override or True
    integrations_to_run: list[str] = []
    if integration:
        integrations_to_run = [i.strip() for i in integration.split(",") if i.strip()]
    elif content_type in {"integration", "all-content"} and resource_names and not all_marketplace:
        integrations_to_run = resource_names
    else:
        paths = get_all_integrations_paths(src=src)
        integrations_to_run = [p.name for p in paths]

    sem = asyncio.Semaphore(1)
    for int_name in integrations_to_run:
        int_dst = dst / int_name / RESOURCES_DIR / AI_DIR

        if content_type in {"action", "all-content"}:
            target_actions: set[str] = set(resource_names) if resource_names and integration else set()
            await DescribeAction(
                int_name, target_actions, src=src, dst=int_dst, override=gen_override
            ).describe_actions(sem=sem)

        if content_type in {"connector", "all-content"}:
            target_connectors: set[str] = set(resource_names) if resource_names and integration else set()
            await DescribeConnector(int_name, target_connectors, src=src, dst=int_dst, override=gen_override).describe(
                sem=sem
            )

        if content_type in {"job", "all-content"}:
            target_jobs: set[str] = set(resource_names) if resource_names and integration else set()
            await DescribeJob(int_name, target_jobs, src=src, dst=int_dst, override=gen_override).describe(sem=sem)


def run_regression_test(  # ruff:ignore[too-many-arguments,complex-structure,too-many-locals,too-many-branches,too-many-statements]
    content_type: str,
    resource_names: list[str] | None = None,
    integration: str | None = None,
    *,
    all_marketplace: bool = False,
    src: Path | None = None,
    dst: Path | None = None,
    override: bool = False,
    report_file: Path | None = None,
    run_describe: bool = True,
    use_llm_judge: bool = False,
    use_batch_api: bool = False,
) -> list[RegressionIssue]:
    """Execute regression testing comparing baseline YAML metadata with test YAML metadata.

    Args:
        content_type: Type of content to test ('action', 'integration', 'connector', 'job', 'all-content').
        resource_names: Specific resource names if passed.
        integration: Specific integration name if passed.
        all_marketplace: Whether to check all integrations.
        src: Custom source path.
        dst: Custom destination/test path.
        override: Whether to force rewrite/re-run describe generation.
        report_file: Output CSV report path (defaults to 'regression_report.csv').
        run_describe: Whether to run Gemini describe generation before comparing.
        use_llm_judge: Whether to use Gemini Judge to evaluate text field equivalence.
        use_batch_api: Whether to use Google GenAI Batch API for LLM Judge.

    Returns:
        list[RegressionIssue]: List of all identified regression issues.

    """
    target_dst: Path = dst or Path("test_descriptions")
    start_time: float = time.perf_counter()

    if run_describe:
        asyncio.run(
            run_describe_generation(
                content_type=content_type,
                resource_names=resource_names,
                integration=integration,
                all_marketplace=all_marketplace,
                src=src,
                dst=target_dst,
                override=override,
            )
        )

    out_report: Path = report_file or Path("regression_report.csv")

    integrations_to_check: list[str] = []
    if integration:
        integrations_to_check = [i.strip() for i in integration.split(",") if i.strip()]
    elif content_type in {"integration", "all-content"} and resource_names and not all_marketplace:
        integrations_to_check = resource_names
    else:
        paths: list[Path] = get_all_integrations_paths(src=src)
        integrations_to_check = [p.name for p in paths]

    metadata_filenames: list[str] = METADATA_FILES.get(content_type, METADATA_FILES["all-content"])

    all_issues: list[RegressionIssue] = []
    global_text_candidates: list[TextCandidate] = []

    for int_name in integrations_to_check:
        try:
            int_path_anyio = get_integration_path(int_name, src=src)
            int_path = Path(str(int_path_anyio))
        except Exception:  # ruff:ignore[blind-except]
            logger.warning("Could not find path for integration %s", int_name)
            continue

        baseline_ai_dir = int_path / RESOURCES_DIR / AI_DIR

        for metadata_filename in metadata_filenames:
            baseline_file: Path = baseline_ai_dir / metadata_filename
            test_file: Path = _resolve_test_file(int_name, metadata_filename, target_dst)

            if not baseline_file.exists() and not test_file.exists():
                continue

            target_entries: set[str] | None = (
                set(resource_names) if content_type != "integration" and resource_names else None
            )
            issues: list[RegressionIssue] = compare_yaml_files(
                baseline_path=baseline_file,
                test_path=test_file,
                path_of_files=str(baseline_file),
                use_llm_judge=use_llm_judge,
                use_batch_api=use_batch_api,
                target_entries=target_entries,
                deferred_judge_pool=global_text_candidates,
            )
            all_issues.extend(issues)

    if use_llm_judge and global_text_candidates:
        console = Console()
        with console.status(
            f"[bold cyan]Evaluating {len(global_text_candidates)} text candidates via LLM Judge...[/bold cyan]"
        ):
            judge_results = run_judge_evaluation_sync(global_text_candidates, use_batch=use_batch_api)
        for res in judge_results:
            if res.verdict.verdict == "NOT_EQUIVALENT":
                issue_type = f"text semantic mismatch ({res.verdict.change_type})"
                missing_info = ""
                if res.verdict.missing_operational_facts:
                    missing_info = (
                        f" | Missing facts: {', '.join(res.verdict.missing_operational_facts)}"
                    )
                all_issues.append(
                    RegressionIssue(
                        path_of_files=res.candidate.path_of_files if res.candidate else "",
                        baseline_file=res.candidate.baseline_file if res.candidate else "",
                        test_file=res.candidate.test_file if res.candidate else "",
                        entry=res.entry_path,
                        issue=issue_type,
                        llm_input=f"Reasoning: {res.verdict.comparison_reasoning}{missing_info}",
                    )
                )

    write_regression_report_csv(all_issues, out_report)

    elapsed_seconds: float = time.perf_counter() - start_time
    console = Console()
    if all_issues:
        console.print(
            f"\n[bold red]Regression Test Summary: Found {len(all_issues)} issue(s)"
            f" in {elapsed_seconds:.1f}s.[/bold red]"
        )
        console.print(f"[bold yellow]Report written to: {out_report.resolve()}[/bold yellow]\n")

        table = Table(title="Regression Testing Results")
        table.add_column("Integration", style="cyan")
        table.add_column("Component", style="blue")
        table.add_column("Entry", style="magenta")
        table.add_column("Issue", style="bold red")

        for issue_item in all_issues[:MAX_DISPLAY_ISSUES]:
            int_name, comp_name = format_integration_and_component(issue_item.path_of_files)
            table.add_row(int_name, comp_name, issue_item.entry, issue_item.issue)

        if len(all_issues) > MAX_DISPLAY_ISSUES:
            table.add_row("...", "...", f"... and {len(all_issues) - MAX_DISPLAY_ISSUES} more", "...")

        console.print(table)
    else:
        console.print(
            f"\n[bold green]Regression Test Summary: 0 issues found in {elapsed_seconds:.1f}s."
            " All metadata matches![/bold green]"
        )
        console.print(f"[green]Empty report generated at: {out_report.resolve()}[/green]\n")

    return all_issues
