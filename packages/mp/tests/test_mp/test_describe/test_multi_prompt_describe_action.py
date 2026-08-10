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
from typing import TYPE_CHECKING, Any
from unittest import mock

import anyio
import pytest

from mp.core.data_models.integrations.action.ai.metadata import ActionAiMetadata
from mp.describe.action.describe import DescriptionParams, MultiPromptDescribeAction
from mp.describe.action.prompt_constructors.source import SourcePromptConstructor
from mp.describe.action.utils import create_nested_schema
from mp.describe.common.describe import DescriptionResult, IntegrationStatus
from mp.describe.common.metadata import PromptOverrideConfig

if TYPE_CHECKING:
    import pathlib

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
async def test_multi_prompt_describe_action_empty_yaml_config(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    config_file = tmp_path / "prompt_overrides.yaml"
    config_file.write_text("[]")

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    with mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results):
        results = await describer.describe_bulk(["Ping"], status)
        assert results == baseline_results
        assert isinstance(results[0].metadata, ActionAiMetadata)
        assert results[0].metadata.ai_description == "Original description"


@pytest.mark.anyio
async def test_multi_prompt_describe_action_with_yaml_ruleset_criteria(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()

    # Evaluation-like ruleset with multiple criteria targeting parameters_description
    config_file = tmp_path / "parameters_ruleset.yaml"
    config_file.write_text("""
- title: "Mandatory Column Strict Value Constraint"
  target_field: "parameters_description"
  criteria: >
    Does every row in the parameters table use exclusively 'Yes' or 'No'?

- title: "Exhaustive Enum Choices"
  target_field: "parameters_description"
  criteria: >
    Are all allowed choices explicitly listed in Description column?
""")

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=config_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    def mock_call_gemini_bulk(prompts: list[str], schema_type: type[BaseModel]) -> list[BaseModel]:
        # Verify prompts contain the consolidated criteria
        assert len(prompts) == 1
        assert "Mandatory Column Strict Value Constraint" in prompts[0]
        assert "Exhaustive Enum Choices" in prompts[0]
        return [schema_type.model_construct(parameters_description="New generated parameters table")]

    with (
        mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results),
        mock.patch(
            "mp.describe.action.describe.MultiPromptDescribeAction._construct_custom_prompts",
            return_value=[
                "Consolidated prompt with Mandatory Column Strict Value Constraint and Exhaustive Enum Choices"
            ],
        ),
        mock.patch("mp.describe.common.utils.llm.call_gemini_bulk", side_effect=mock_call_gemini_bulk),
    ):
        results = await describer.describe_bulk(["Ping"], status)
        assert len(results) == 1
        assert isinstance(results[0].metadata, ActionAiMetadata)
        assert results[0].metadata.parameters_description == "New generated parameters table"
        assert results[0].metadata.ai_description == "Original description"


@pytest.mark.anyio
async def test_prompt_constructor_auto_appends_sources(tmp_path: pathlib.Path) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    actions_dir = int_dir / "actions"
    actions_dir.mkdir()
    (actions_dir / "ping.py").write_text("def ping(): pass")
    (actions_dir / "ping.yaml").write_text("name: Ping")

    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))
    params = DescriptionParams(
        anyio.Path(int_dir),
        "test_int",
        "Ping",
        "ping",
        status,
    )
    constructor = SourcePromptConstructor(
        params.integration,
        params.integration_name,
        params.action_name,
        params.action_file_name,
        params.status.out_path,
    )

    # Custom template with NO placeholders
    custom_template = string.Template("Generate parameters table strictly obeying rules.")
    rendered = await constructor.construct(template=custom_template)

    assert "Generate parameters table strictly obeying rules." in rendered
    assert '<python_script filename="ping.py">' in rendered
    assert "def ping(): pass" in rendered
    assert '<action_definition filename="ping.yaml">' in rendered


@pytest.mark.anyio
async def test_source_prompt_constructor_construct_override(tmp_path: pathlib.Path) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    actions_dir = int_dir / "actions"
    actions_dir.mkdir()
    (actions_dir / "ping.py").write_text("def ping(): pass")
    (actions_dir / "ping.yaml").write_text("name: Ping")

    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))
    params = DescriptionParams(
        anyio.Path(int_dir),
        "test_int",
        "Ping",
        "ping",
        status,
    )
    constructor = SourcePromptConstructor(
        params.integration,
        params.integration_name,
        params.action_name,
        params.action_file_name,
        params.status.out_path,
    )

    override = PromptOverrideConfig(
        target_field="parameters_description",
        criteria="Must be a valid markdown table.",
    )
    rendered = await constructor.construct_override(override)

    assert "### SOURCE CODE & SPECIFICATIONS" in rendered
    assert '<python_script filename="ping.py">' in rendered
    assert "def ping(): pass" in rendered
    assert '<action_definition filename="ping.yaml">' in rendered
    assert "Must be a valid markdown table." in rendered
    assert "'parameters_description'" in rendered


@pytest.mark.anyio
async def test_multi_prompt_describe_action_yaml_multiple_field_overrides(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    override_all_config = tmp_path / "override_all.yaml"
    override_all_config.write_text("""
- title: "Parameters Description Rule"
  target_field: "parameters_description"
  criteria: >
    Parameters criteria for ${python_file_name}

- title: "Entity Usage Rule"
  target_field: "entity_usage"
  criteria: >
    Entity usage criteria for ${python_file_name}

- title: "Outcome Categories Rule"
  target_field: "outcome_categories"
  criteria: >
    Outcome categories criteria for ${python_file_name}
""")

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=override_all_config)
    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    def mock_call_gemini_bulk(prompts: list[str], schema_type: type[BaseModel]) -> list[BaseModel]:
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
        assert meta.parameters_description == "Custom parameters table"
        assert meta.entity_usage == {"reasoning": "Custom entity usage"}
        assert meta.outcome_categories == {"reasoning": "Custom outcome categories"}
        assert meta.ai_description == "Original description"
        assert meta.ai_short_description == "Original short description"


@pytest.mark.anyio
async def test_multi_prompt_describe_action_error_handling_missing_config(
    tmp_path: pathlib.Path, mock_action_ai_metadata: ActionAiMetadata
) -> None:
    int_dir = tmp_path / "test_int"
    int_dir.mkdir()
    non_existent_file = tmp_path / "missing_overrides.yaml"

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
    malformed_file = tmp_path / "malformed.yaml"
    malformed_file.write_text("invalid: [yaml: broken")

    describer = MultiPromptDescribeAction("test_int", {"Ping"}, src=tmp_path, prompt_overrides=malformed_file)
    status = IntegrationStatus(is_built=False, out_path=anyio.Path(int_dir))

    baseline_results = [DescriptionResult("Ping", mock_action_ai_metadata)]

    with (
        mock.patch("mp.describe.action.describe.DescribeAction.describe_bulk", return_value=baseline_results),
        pytest.raises(ValueError, match="Failed to parse prompt overrides"),
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
