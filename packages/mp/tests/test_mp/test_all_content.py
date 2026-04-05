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

from typing import TYPE_CHECKING
from unittest import mock

import pytest
import yaml

from mp.core import constants
from mp.describe.all_content import describe_all_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_integration_full(tmp_path: Path) -> Path:
    integration_path = tmp_path / "mock_integration"
    integration_path.mkdir()

    # Create actions
    actions_dir = integration_path / constants.ACTIONS_DIR
    actions_dir.mkdir()
    (actions_dir / "test_action.yaml").write_text(
        yaml.safe_dump({"name": "Test Action", "description": "A test action"}),
        encoding="utf-8",
    )
    (actions_dir / "test_action.py").write_text("def action(): pass", encoding="utf-8")

    # Create connectors
    connectors_dir = integration_path / constants.CONNECTORS_DIR
    connectors_dir.mkdir()
    (connectors_dir / "test_connector.yaml").write_text(
        yaml.safe_dump({"name": "Test Connector", "description": "A test connector"}),
        encoding="utf-8",
    )
    (connectors_dir / "test_connector.py").write_text("class Connector: pass", encoding="utf-8")

    # Create jobs
    jobs_dir = integration_path / constants.JOBS_DIR
    jobs_dir.mkdir()
    (jobs_dir / "test_job.yaml").write_text(
        yaml.safe_dump({"name": "Test Job", "description": "A test job"}), encoding="utf-8"
    )
    (jobs_dir / "test_job.py").write_text("class Job: pass", encoding="utf-8")

    # Create definition.yaml
    (integration_path / constants.DEFINITION_FILE).write_text(
        yaml.safe_dump({"description": "Mock integration description"}), encoding="utf-8"
    )

    return integration_path


@pytest.mark.anyio
async def test_describe_all_content(mock_integration_full: Path) -> None:
    # We need to mock call_gemini_bulk to return appropriate objects for each call.
    # DescribeAction, DescribeConnector, DescribeJob, and finally DescribeIntegration.

    action_response = mock.Mock()
    action_response.model_dump.return_value = {"ai_description": "Action AI"}

    connector_response = mock.Mock()
    connector_response.model_dump.return_value = {"ai_description": "Connector AI"}

    job_response = mock.Mock()
    job_response.model_dump.return_value = {"ai_description": "Job AI"}

    integration_response = mock.Mock()
    # IntegrationAiMetadata (just some categories)
    integration_response.model_dump.return_value = {"endpoint_security": True}

    responses = [
        [action_response],
        [connector_response],
        [job_response],
        [integration_response],
    ]

    with mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", side_effect=responses):
        await describe_all_content(
            integration="mock_integration",
            src=mock_integration_full.parent,
        )

    # Check if all files were created
    ai_dir = mock_integration_full / constants.RESOURCES_DIR / constants.AI_DIR
    assert (ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE).exists()
    assert (ai_dir / constants.CONNECTORS_AI_DESCRIPTION_FILE).exists()
    assert (ai_dir / constants.JOBS_AI_DESCRIPTION_FILE).exists()
    assert (ai_dir / constants.INTEGRATIONS_AI_DESCRIPTION_FILE).exists()

    # Verify integration AI description
    content = yaml.safe_load((ai_dir / constants.INTEGRATIONS_AI_DESCRIPTION_FILE).read_text())
    assert content["endpoint_security"] is True
