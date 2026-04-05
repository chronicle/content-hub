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
from mp.describe.connector.describe import DescribeConnector
from mp.describe.integration.describe import DescribeIntegration
from mp.describe.job.describe import DescribeJob

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_integration_path(tmp_path: Path) -> Path:
    integration_path = tmp_path / "mock_integration"
    integration_path.mkdir()

    # Create connectors dir
    connectors_dir = integration_path / constants.CONNECTORS_DIR
    connectors_dir.mkdir()
    (connectors_dir / "test_connector.yaml").write_text(
        yaml.safe_dump({"name": "Test Connector", "description": "A test connector"}),
        encoding="utf-8",
    )
    (connectors_dir / "test_connector.py").write_text("class TestConnector: pass", encoding="utf-8")

    # Create jobs dir
    jobs_dir = integration_path / constants.JOBS_DIR
    jobs_dir.mkdir()
    (jobs_dir / "test_job.yaml").write_text(
        yaml.safe_dump({"name": "Test Job", "description": "A test job"}), encoding="utf-8"
    )
    (jobs_dir / "test_job.py").write_text("class TestJob: pass", encoding="utf-8")

    return integration_path


@pytest.mark.anyio
async def test_describe_connector(mock_integration_path: Path) -> None:
    describer = DescribeConnector(
        integration="mock_integration",
        connectors={"Test Connector"},
        src=mock_integration_path.parent,
    )

    mock_response = mock.Mock()
    mock_response.ai_description = "AI-generated connector description"
    mock_response.model_dump.return_value = {"ai_description": "AI-generated connector description"}

    with mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", return_value=[mock_response]):
        await describer.describe()

    # Verify output file
    ai_dir = mock_integration_path / constants.RESOURCES_DIR / constants.AI_DIR
    output_file = ai_dir / constants.CONNECTORS_AI_DESCRIPTION_FILE
    assert output_file.exists()

    content = yaml.safe_load(output_file.read_text(encoding="utf-8"))
    assert "Test Connector" in content
    assert content["Test Connector"]["ai_description"] == "AI-generated connector description"


@pytest.mark.anyio
async def test_describe_job(mock_integration_path: Path) -> None:
    describer = DescribeJob(
        integration="mock_integration", jobs={"Test Job"}, src=mock_integration_path.parent
    )

    mock_response = mock.Mock()
    mock_response.ai_description = "AI-generated job description"
    mock_response.model_dump.return_value = {"ai_description": "AI-generated job description"}

    with mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", return_value=[mock_response]):
        await describer.describe()

    # Verify output file
    ai_dir = mock_integration_path / constants.RESOURCES_DIR / constants.AI_DIR
    output_file = ai_dir / constants.JOBS_AI_DESCRIPTION_FILE
    assert output_file.exists()

    content = yaml.safe_load(output_file.read_text(encoding="utf-8"))
    assert "Test Job" in content
    assert content["Test Job"]["ai_description"] == "AI-generated job description"


@pytest.mark.anyio
async def test_describe_integration(mock_integration_path: Path) -> None:
    # 1. Create AI description files for context
    ai_dir = mock_integration_path / constants.RESOURCES_DIR / constants.AI_DIR
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE).write_text(
        yaml.safe_dump({"test_action": {"description": "Action description"}}),
        encoding="utf-8",
    )
    (ai_dir / constants.CONNECTORS_AI_DESCRIPTION_FILE).write_text(
        yaml.safe_dump({"test_connector": {"description": "Connector description"}}),
        encoding="utf-8",
    )
    (ai_dir / constants.JOBS_AI_DESCRIPTION_FILE).write_text(
        yaml.safe_dump({"test_job": {"description": "Job description"}}), encoding="utf-8"
    )

    # 2. Add description to definition.yaml
    (mock_integration_path / constants.DEFINITION_FILE).write_text(
        yaml.safe_dump({"name": "mock_integration", "description": "integration_description"}),
        encoding="utf-8",
    )

    describer = DescribeIntegration(
        integration="mock_integration",
        src=mock_integration_path.parent,
    )

    mock_response = mock.Mock()
    mock_response.model_dump.return_value = {
        "product_categories": ["SIEM"],
        "summary": "Integration summary",
    }

    with mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", return_value=[mock_response]):
        await describer.describe()

    # 3. Verify output file
    output_file = ai_dir / constants.INTEGRATIONS_AI_DESCRIPTION_FILE
    assert output_file.exists()

    content = yaml.safe_load(output_file.read_text(encoding="utf-8"))
    assert content["product_categories"] == ["SIEM"]
    assert content["summary"] == "Integration summary"
