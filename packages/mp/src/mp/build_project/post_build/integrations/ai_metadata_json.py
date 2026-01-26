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

import json
import logging
from typing import TYPE_CHECKING

import yaml
from rich.logging import RichHandler

from mp.core import constants

if TYPE_CHECKING:
    from pathlib import Path

logger: logging.Logger = logging.getLogger("mp.build.ai_metadata")
logging.basicConfig(level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])


def write_actions_ai_metadata_json(out_dir: Path) -> None:
    """Aggregate ai_description.yaml files from integrations into a single JSON file."""
    metadata_collection: dict[str, dict[str, str]] = {}
    for integration_path in out_dir.iterdir():
        if not integration_path.is_dir() or integration_path.name.startswith("."):
            continue

        ai_file: Path = integration_path / constants.RESOURCES_DIR / "ai" / "ai_description.yaml"
        if ai_file.exists():
            try:
                with ai_file.open(encoding="utf-8") as f:
                    if data := yaml.safe_load(f):
                        metadata_collection[integration_path.name] = data

            except Exception:
                logger.exception("Failed to read AI metadata for %s", integration_path.name)

    output_file: Path = out_dir / "actions_ai_metadata.json"
    try:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(metadata_collection, f, indent=4)

        logger.info("Generated actions_ai_metadata.json at %s", output_file)

    except Exception:
        logger.exception("Failed to write actions_ai_metadata.json")
