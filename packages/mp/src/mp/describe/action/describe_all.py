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
from typing import TYPE_CHECKING

from rich.logging import RichHandler
from rich.progress import track

from mp.core import constants
from mp.core.custom_types import RepositoryType
from mp.core.file_utils import get_integrations_repo_base_path
from mp.describe.action.describe import DescribeAction

if TYPE_CHECKING:
    from pathlib import Path


logger: logging.Logger = logging.getLogger("mp.describe_marketplace")
logging.basicConfig(level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])


async def describe_all_actions() -> None:
    """Describe all actions in all integrations in the marketplace."""
    integrations_paths: list[Path] = _get_all_integrations_paths()
    for integration_path in track(integrations_paths, description="Describing integrations..."):
        try:
            await describe_integration(integration_path)
        except Exception:
            logger.exception("Failed to describe integration %s", integration_path.name)


async def describe_integration(integration_path: Path) -> None:
    """Describe all actions in a given integration."""
    if action_files := _get_action_files(integration_path):
        await DescribeAction(integration_path.name, set(action_files)).describe_actions()


def _get_action_files(integration_path: Path) -> list[str]:
    actions_dir: Path = integration_path / constants.ACTIONS_DIR
    if not actions_dir.exists():
        return []

    return [f.stem for f in actions_dir.glob("*.py") if f.name != "__init__.py"]


def _get_all_integrations_paths() -> list[Path]:
    paths: list[Path] = []
    for repo_type in [RepositoryType.COMMERCIAL, RepositoryType.THIRD_PARTY]:
        base_path: Path = get_integrations_repo_base_path(repo_type)
        if not base_path.exists():
            continue

        if repo_type == RepositoryType.COMMERCIAL:
            paths.extend([
                p for p in base_path.iterdir() if p.is_dir() and not p.name.startswith(".")
            ])
        else:
            for sub in base_path.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    paths.extend([
                        p for p in sub.iterdir() if p.is_dir() and not p.name.startswith(".")
                    ])
    return paths
