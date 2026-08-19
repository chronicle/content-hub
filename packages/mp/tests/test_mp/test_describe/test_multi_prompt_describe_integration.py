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

import string
from typing import TYPE_CHECKING
from unittest import mock

import anyio
import pytest

from mp.core.data_models.integrations.integration_meta.ai.metadata import IntegrationAiMetadata
from mp.core.data_models.integrations.integration_meta.ai.product_categories import (
    IntegrationProductCategories,
)
from mp.describe.common.describe import DescriptionResult, IntegrationStatus
from mp.describe.common.metadata import PromptOverrideConfig
from mp.describe.integration.describe import MultiPromptDescribeIntegration
from mp.describe.integration.prompt_constructors.integration import IntegrationPromptConstructor

if TYPE_CHECKING:
    import pathlib

    from pydantic import BaseModel


@pytest.fixture
def mock_integration_ai_metadata() -> IntegrationAiMetadata:
    return IntegrationAiMetadata(
        product_categories=IntegrationProductCategories(
            siem=False,
            edr=False,
            network_security=False,
            threat_intelligence=True,
            email_security=False,
            iam_and_identity_management=False,
            cloud_security=False,
            itsm=False,
            vulnerability_management=False,
            asset_inventory=False,
            collaboration=False,
            reasoning="Original reasoning",
        )
    )


@pytest.mark.anyio
async def test_multi_prompt_describe_integration_no_overrides(
    tmp_path: pathlib.Path, mock_integration_ai_metadata: IntegrationAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    describer = MultiPromptDescribeIntegration("test_int", src=tmp_path, prompt_overrides=None)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("test_int", mock_integration_ai_metadata)]

    with mock.patch(
        "mp.describe.integration.describe.DescribeIntegration.describe_bulk",
        return_value=baseline_results,
    ):
        results = await describer.describe_bulk(["test_int"], status)
        assert results == baseline_results
        assert isinstance(results[0].metadata, IntegrationAiMetadata)
        assert results[0].metadata.product_categories.reasoning == "Original reasoning"


@pytest.mark.anyio
async def test_multi_prompt_describe_integration_empty_yaml_config(
    tmp_path: pathlib.Path, mock_integration_ai_metadata: IntegrationAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    config_file = tmp_path / "prompt_overrides.yaml"
    config_file.write_text("[]")

    describer = MultiPromptDescribeIntegration("test_int", src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("test_int", mock_integration_ai_metadata)]

    with mock.patch(
        "mp.describe.integration.describe.DescribeIntegration.describe_bulk",
        return_value=baseline_results,
    ):
        results = await describer.describe_bulk(["test_int"], status)
        assert results == baseline_results
        assert isinstance(results[0].metadata, IntegrationAiMetadata)
        assert results[0].metadata.product_categories.reasoning == "Original reasoning"


@pytest.mark.anyio
async def test_multi_prompt_describe_integration_with_yaml_criteria_overrides(
    tmp_path: pathlib.Path, mock_integration_ai_metadata: IntegrationAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()

    config_file = tmp_path / "product_categories_ruleset.yaml"
    config_file.write_text("""
- title: "SIEM & Network Security Categories"
  target_field: "product_categories"
  criteria: >
    Should mark SIEM and Network Security if log analytics or firewall controls exist.
""")

    describer = MultiPromptDescribeIntegration("test_int", src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("test_int", mock_integration_ai_metadata)]

    def mock_call_gemini_bulk(prompts: list[str], schema_type: type[BaseModel]) -> list[BaseModel]:
        return [
            schema_type.model_construct(
                product_categories=IntegrationProductCategories(
                    siem=True,
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
                    reasoning="Overridden product category reasoning",
                )
            )
        ]

    with (
        mock.patch(
            "mp.describe.integration.describe.DescribeIntegration.describe_bulk",
            return_value=baseline_results,
        ),
        mock.patch(
            "mp.describe.integration.describe.MultiPromptDescribeIntegration._construct_custom_prompts",
            return_value=["Custom prompt content"],
        ),
        mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", side_effect=mock_call_gemini_bulk),
    ):
        results = await describer.describe_bulk(["test_int"], status)
        assert len(results) == 1
        assert isinstance(results[0].metadata, IntegrationAiMetadata)
        assert results[0].metadata.product_categories.reasoning == "Overridden product category reasoning"
        assert results[0].metadata.product_categories.siem is True
        assert results[0].metadata.product_categories.network_security is True


@pytest.mark.anyio
async def test_integration_prompt_constructor_construct_override(tmp_path: pathlib.Path) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    (int_dir / "definition.yaml").write_text("description: My custom integration description")

    constructor = IntegrationPromptConstructor(anyio.Path(int_dir), "test_int", anyio.Path(int_dir))

    override = PromptOverrideConfig(
        target_field="product_categories",
        criteria="Must categorize SIEM accurately.",
    )
    rendered = await constructor.construct_override(override)

    assert "### INTEGRATION CONTEXT" in rendered
    assert "<integration_description>" in rendered
    assert "My custom integration description" in rendered
    assert "Must categorize SIEM accurately." in rendered
    assert "'product_categories'" in rendered


@pytest.mark.anyio
async def test_integration_prompt_constructor_auto_appends_context(tmp_path: pathlib.Path) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    (int_dir / "definition.yaml").write_text("description: My custom integration description")

    constructor = IntegrationPromptConstructor(anyio.Path(int_dir), "test_int", anyio.Path(int_dir))

    custom_template = string.Template("Generate product categories adhering to rules.")
    rendered = await constructor.construct(template=custom_template)

    assert "Generate product categories adhering to rules." in rendered
    assert "<integration_description>" in rendered
    assert "My custom integration description" in rendered


@pytest.mark.anyio
async def test_multi_prompt_describe_integration_error_handling_missing_config(
    tmp_path: pathlib.Path, mock_integration_ai_metadata: IntegrationAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    non_existent_file = tmp_path / "missing_overrides.yaml"

    describer = MultiPromptDescribeIntegration("test_int", src=tmp_path, prompt_overrides=non_existent_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("test_int", mock_integration_ai_metadata)]

    with (
        mock.patch(
            "mp.describe.integration.describe.DescribeIntegration.describe_bulk",
            return_value=baseline_results,
        ),
        pytest.raises(FileNotFoundError, match="does not exist"),
    ):
        await describer.describe_bulk(["test_int"], status)


@pytest.mark.anyio
async def test_multi_prompt_describe_integration_error_handling_malformed_config(
    tmp_path: pathlib.Path, mock_integration_ai_metadata: IntegrationAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    malformed_file = tmp_path / "malformed.yaml"
    malformed_file.write_text("invalid: [broken: yaml")

    describer = MultiPromptDescribeIntegration("test_int", src=tmp_path, prompt_overrides=malformed_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("test_int", mock_integration_ai_metadata)]

    with (
        mock.patch(
            "mp.describe.integration.describe.DescribeIntegration.describe_bulk",
            return_value=baseline_results,
        ),
        pytest.raises(ValueError, match="Failed to parse prompt overrides"),
    ):
        await describer.describe_bulk(["test_int"], status)


@pytest.mark.anyio
async def test_multi_prompt_describe_integration_llm_error_graceful_handling(
    tmp_path: pathlib.Path, mock_integration_ai_metadata: IntegrationAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()

    config_file = tmp_path / "prompt_overrides.yaml"
    config_file.write_text("""
- target_field: "product_categories"
  criteria: >
    Custom criteria content
""")

    describer = MultiPromptDescribeIntegration("test_int", src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("test_int", mock_integration_ai_metadata)]

    with (
        mock.patch(
            "mp.describe.integration.describe.DescribeIntegration.describe_bulk",
            return_value=baseline_results,
        ),
        mock.patch(
            "mp.describe.integration.describe.MultiPromptDescribeIntegration._construct_custom_prompts",
            return_value=["Custom prompt content"],
        ),
        mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", return_value=["Error from LLM API"]),
    ):
        results = await describer.describe_bulk(["test_int"], status)
        assert len(results) == 1
        assert results[0].metadata == mock_integration_ai_metadata
