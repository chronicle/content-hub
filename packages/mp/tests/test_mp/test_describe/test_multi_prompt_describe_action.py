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

import pathlib
from typing import TYPE_CHECKING, Any
from unittest import mock

import anyio
import pytest

from mp.core.data_models.integrations.action.ai.metadata import ActionAiMetadata
from mp.describe.action.describe import MultiPromptDescribeAction
from mp.describe.action.utils import create_nested_schema
from mp.describe.common.describe import DescriptionResult, IntegrationStatus

if TYPE_CHECKING:
    from pydantic import BaseModel


@pytest.fixture
def mock_action_ai_metadata() -> ActionAiMetadata:
    return ActionAiMetadata.model_construct(
        ai_description="Original description",
        ai_short_description="Original short description",
        parameters_description="Original parameters",
    )


@pytest.mark.anyio
async def test_multi_prompt_describe_action_no_overrides(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=None)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    with mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results):
        results = await describer.describe_bulk(["Ping"], status)
        assert results == baseline_results
        assert isinstance(results[0].metadata, ActionAiMetadata)
        assert results[0].metadata.ai_description == "Original description"


@pytest.mark.anyio
async def test_multi_prompt_describe_action_empty_config(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    config_file = tmp_path / "prompt_overrides.json"
    config_file.write_text('{"prompt_config": []}')

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    with mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results):
        results = await describer.describe_bulk(["Ping"], status)
        assert results == baseline_results
        assert isinstance(results[0].metadata, ActionAiMetadata)
        assert results[0].metadata.ai_description == "Original description"


@pytest.mark.anyio
async def test_multi_prompt_describe_action_with_overrides(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    prompt_file = tmp_path / "custom_prompt.md"
    prompt_file.write_text("Custom prompt for ${python_file_name}")

    config_file = tmp_path / "prompt_overrides.json"
    config_file.write_text(f"""{{
      "prompt_config": [
        {{
          "location": "{prompt_file}",
          "field_name": "ai_description"
        }}
      ]
    }}""")

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    def mock_call_gemini_bulk(prompts: list[str], schema_type: type[BaseModel]) -> list[BaseModel]:
        return [schema_type(ai_description="Overridden description from custom LLM")]  # ty: ignore[pydantic-discarded-extra-argument]

    with (
        mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results),
        mock.patch(
            "mp.describe.action.describe.MultiPromptDescribeAction._construct_custom_prompts",
            return_value=["Custom prompt content"],
        ),
        mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", side_effect=mock_call_gemini_bulk),
    ):
        results = await describer.describe_bulk(["Ping"], status)
        assert len(results) == 1
        assert isinstance(results[0].metadata, ActionAiMetadata)
        assert results[0].metadata.ai_description == "Overridden description from custom LLM"
        assert results[0].metadata.ai_short_description == "Original short description"


@pytest.mark.anyio
async def test_multi_prompt_describe_action_test_data_overrides(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    test_data_dir = (
        pathlib.Path(__file__).parent / "test_data" / "prompt_overrides"
    )
    override_all_config = test_data_dir / "override_all.json"

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=override_all_config)
    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    def mock_call_gemini_bulk(prompts: list[str], schema_type: type[BaseModel]) -> list[BaseModel]:
        # Handle parameter_description, entity_usage, or outcome_categories depending on model
        fields = schema_type.model_fields
        if "parameters_description" in fields:
            return [schema_type.model_construct(parameters_description="Custom parameters table")]
        if "entity_usage" in fields:
            return [schema_type.model_construct(entity_usage={"reasoning": "Custom entity usage"})]
        if "outcome_categories" in fields:
            return [schema_type.model_construct(outcome_categories={"reasoning": "Custom outcome categories"})]
        return [schema_type.model_construct()]

    with (
        mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results),
        mock.patch(
            "mp.describe.action.describe.MultiPromptDescribeAction._construct_custom_prompts",
            return_value=["Custom prompt content"],
        ),
        mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", side_effect=mock_call_gemini_bulk),
    ):
        results = await describer.describe_bulk(["Ping"], status)
        assert len(results) == 1
        meta = results[0].metadata
        assert isinstance(meta, ActionAiMetadata)
        # Targeted fields are overridden
        assert meta.parameters_description == "Custom parameters table"
        assert meta.entity_usage == {"reasoning": "Custom entity usage"}
        assert meta.outcome_categories == {"reasoning": "Custom outcome categories"}
        # Unrelated fields remain unchanged
        assert meta.ai_description == "Original description"
        assert meta.ai_short_description == "Original short description"


@pytest.mark.anyio
async def test_multi_prompt_describe_action_error_handling_missing_config(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    non_existent_file = tmp_path / "missing_overrides.json"

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=non_existent_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    with (
        mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results),
        pytest.raises(FileNotFoundError, match="does not exist"),
    ):
        await describer.describe_bulk(["Ping"], status)


@pytest.mark.anyio
async def test_multi_prompt_describe_action_error_handling_malformed_config(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    malformed_file = tmp_path / "malformed.json"
    malformed_file.write_text("{invalid json}")

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=malformed_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    with (
        mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results),
        pytest.raises(ValueError, match="Failed to parse prompt overrides file"),
    ):
        await describer.describe_bulk(["Ping"], status)


@pytest.mark.anyio
async def test_multi_prompt_describe_action_error_handling_missing_prompt_template(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    config_file = tmp_path / "prompt_overrides.json"
    config_file.write_text("""{
      "prompt_config": [
        {
          "location": "non_existent_prompt.md",
          "field_name": "ai_description"
        }
      ]
    }""")

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    with (
        mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results),
        pytest.raises(FileNotFoundError, match="Custom prompt location"),
    ):
        await describer.describe_bulk(["Ping"], status)


def test_create_nested_schema() -> None:
    schema_dict: dict[str, Any] = {
        "title": "Test Title",
        "count": 42,
        "section": {"section_name": "General"},
        "items": [{"item_id": "1", "score": 9.5}],
    }
    model_cls = create_nested_schema("TestModel", schema_dict)
    inst: Any = model_cls.model_validate({
        "title": "Sample",
        "count": 10,
        "section": {"section_name": "Main"},
        "items": [{"item_id": "item1", "score": 8.0}],
    })
    assert inst.title == "Sample"
    assert inst.section.section_name == "Main"
    assert inst.items[0].item_id == "item1"
