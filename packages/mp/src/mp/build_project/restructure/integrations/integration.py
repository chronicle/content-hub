"""Orchestrates the restructuring process for an integration.

This module provides a high-level function, `restructure_integration`, which
coordinates the individual restructuring steps for an integration, including
metadata, scripts, code, and dependencies. It adapts the process based on
whether the integration is fully built or partially built.
"""

# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

import rich

import mp.core.file_utils

from . import code, dependencies, metadata, scripts

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.integrations.integration import BuiltIntegration


def restructure_integration(
    integration_metadata: BuiltIntegration,
    integration_path: Path,
    integration_out_path: Path,
) -> None:
    """Restructure an integration to its "out" path.

    The restructure includes metadata, scripts, code, and dependencies.

    Args:
        integration_metadata: An integration's meta - built version
        integration_path: The path to the integration's folder
        integration_out_path: The path to the integration's "out" folder

    """
    rich.print(f"Restructuring {integration_metadata['metadata']['Identifier']}")
    if mp.core.file_utils.is_non_built_integration(integration_path):
        rich.print("Restructuring metadata")
        metadata.Metadata(integration_out_path, integration_metadata).restructure()

        rich.print("Restructuring scripts")
        scripts.Scripts(integration_path, integration_out_path).restructure()

        rich.print("Restructuring code")
        code.Code(integration_out_path).restructure()

    if not mp.core.file_utils.is_built(integration_path):
        rich.print("Restructuring dependencies")
        dependencies.Dependencies(integration_path, integration_out_path).restructure()
