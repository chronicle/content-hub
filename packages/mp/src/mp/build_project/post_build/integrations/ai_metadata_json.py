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
from typing import TYPE_CHECKING, Any

import yaml

from mp.core import constants

if TYPE_CHECKING:
    from pathlib import Path

logger: logging.Logger = logging.getLogger("mp.build.ai_metadata")


def write_actions_ai_metadata_json(out_dir: Path, source_paths: list[Path]) -> None:
    """Aggregate ai_description.yaml files from integrations into a single JSON file."""
    metadata_collection: dict[str, dict[str, Any]] = {}
    for integration_dir in out_dir.iterdir():
        if not integration_dir.is_dir() or integration_dir.name.startswith("."):
            continue

        integration_id: str = integration_dir.name
        # Find source directory
        source_dir: Path | None = None
        for base_path in source_paths:
            if (p := base_path / integration_id).exists():
                source_dir = p
                break

        if not source_dir:
            continue

        ai_file: Path = (
            source_dir
            / constants.RESOURCES_DIR
            / constants.AI_FOLDER
            / constants.ACTIONS_AI_DESCRIPTION_FILE
        )
        if ai_file.exists():
            try:
                with ai_file.open(encoding="utf-8") as f:
                    if data := yaml.safe_load(f):
                        metadata_collection[integration_id] = {"actions": data}

            except Exception:
                logger.exception("Failed to read AI metadata for %s", integration_id)

    output_file: Path = out_dir / constants.AI_META_JSON_FILE
    try:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(metadata_collection, f, indent=4)

        logger.info("Generated %s at %s", constants.AI_META_JSON_FILE, output_file)

    except Exception:
        logger.exception("Failed to write %s", constants.AI_META_JSON_FILE)
