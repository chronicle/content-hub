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

import shutil
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import anyio
from typer.testing import CliRunner

from mp.core import constants
from mp.core.data_models.integrations.integration_meta.ai.metadata import IntegrationAiMetadata
from mp.core.data_models.integrations.integration_meta.ai.product_categories import (
    IntegrationProductCategories,
)
from mp.describe.integration.typer_app import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def test_describe_integration_command(tmp_path: Path, non_built_integration: Path) -> None:
    integration: Path = (
        shutil.copytree(non_built_integration, tmp_path, dirs_exist_ok=True) / non_built_integration.name
    )
    integration_name = "mock_integration"

    # Create AI_DIR if it doesn't exist to avoid issues,
    # though the code should handle it.

    with patch("mp.describe.common.utils.llm.call_gemini_bulk", new_callable=AsyncMock) as mock_bulk:
        mock_bulk.return_value = [
            IntegrationAiMetadata(
                product_categories=IntegrationProductCategories(
                    siem=False,
                    edr=False,
                    network_security=True,
                    threat_intelligence=False,
                    email_security=False,
                    iam_and_identity_management=False,
                    cloud_security=False,
                    itsm=False,
                    vulnerability_management=False,
                    asset_inventory=False,
                    collaboration=False,
                    reasoning="Some reason",
                )
            )
        ]

        # We need to mock get_integration_path and get_out_path
        with (
            patch("mp.describe.common.utils.paths.get_integration_path") as mock_get_path,
            patch("mp.describe.common.utils.paths.get_out_path") as mock_get_out_path,
            patch("mp.describe.integration.describe_all.get_integration_path", new=mock_get_path),
        ):
            mock_get_path.return_value = anyio.Path(integration)
            mock_get_out_path.return_value = anyio.Path(integration)

            # Run the command
            result = runner.invoke(app, [integration_name, "--override"])

            assert result.exit_code == 0
            mock_bulk.assert_called_once()

            # Check if the file was created
            ai_file = (
                integration / constants.RESOURCES_DIR / constants.AI_DIR / constants.INTEGRATIONS_AI_DESCRIPTION_FILE
            )
            assert ai_file.exists()
