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

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from mp.core.data_models.integrations.integration_meta.ai.metadata import IntegrationAiMetadata
from mp.core.data_models.integrations.integration_meta.ai.product_categories import (
    IntegrationProductCategories,
)
from mp.describe.integration.typer_app import app

runner = CliRunner()


def test_describe_integration_command(non_built_integration):
    integration_name = "mock_integration"

    # Create AI_DIR if it doesn't exist to avoid issues,
    # though the code should handle it.

    with patch(
        "mp.describe.common.utils.llm.call_gemini_bulk", new_callable=AsyncMock
    ) as mock_bulk:
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
                )
            )
        ]

        # We need to mock get_integration_path to return the non_built_integration path
        with patch("mp.describe.common.utils.paths.get_integration_path") as mock_get_path:
            import anyio

            mock_get_path.return_value = anyio.Path(non_built_integration)

            # Run the command
            result = runner.invoke(app, ["-i", integration_name])

            assert result.exit_code == 0
            mock_bulk.assert_called_once()

            # Check if the file was created
            ai_file = (
                non_built_integration / "RESOURCES" / "AI" / "integrations_ai_description.yaml"
            )
            assert ai_file.exists()
