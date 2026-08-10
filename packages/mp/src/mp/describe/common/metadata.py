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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pathlib

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

_TYPE_MAPPING: dict[str, type[Any]] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
    "dict": dict,
    "object": dict,
    "list": list,
    "array": list,
}


class FieldSchemaConfig(BaseModel):
    """Configuration schema definition for custom prompt override fields."""

    model_name: str | None = None
    type: str | None = None
    description: str | None = None
    required: bool | None = None


class PromptOverrideConfig(BaseModel):
    """Configuration item mapping an evaluation rule/criteria to a field override."""

    model_config = ConfigDict(populate_by_name=True)

    target_field: str
    criteria: str
    title: str = ""
    rule_id: str | None = None
    schema_def: FieldSchemaConfig | None = Field(default=None, alias="schema")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: object) -> object:
        """Normalize field names in input data dictionary before model validation.

        Args:
            data: Raw input data to normalize.

        Returns:
            object: Normalized data dictionary or original data object.

        """
        if isinstance(data, dict) and "rule_id" not in data and "id" in data:
            # Support rule_id / id
            data["rule_id"] = data["id"]
        return data


def group_prompt_overrides(
    overrides: list[PromptOverrideConfig],
) -> list[PromptOverrideConfig]:
    """Group multiple rules or overrides targeting the same field into consolidated overrides.

    Args:
        overrides: List of raw parsed prompt override configurations.

    Returns:
        list[PromptOverrideConfig]: List of consolidated PromptOverrideConfig items.

    """
    grouped_by_field: dict[str, list[PromptOverrideConfig]] = {}
    for item in overrides:
        if not item.target_field:
            continue
        grouped_by_field.setdefault(item.target_field, []).append(item)

    consolidated: list[PromptOverrideConfig] = []
    for field_name, items in grouped_by_field.items():
        if len(items) == 1:
            consolidated.append(items[0])
            continue

        rule_texts: list[str] = []
        schema_def: FieldSchemaConfig | None = None
        for i, it in enumerate(items, 1):
            if it.schema_def and not schema_def:
                schema_def = it.schema_def
            title = it.title or f"Rule {i}"
            content = it.criteria or ""
            if content:
                rule_texts.append(f"#### {title}\n{content}")

        combined_criteria = "\n\n".join(rule_texts)
        consolidated.append(
            PromptOverrideConfig(
                target_field=field_name,
                criteria=combined_criteria,
                title=f"Consolidated Rules for {field_name}",
                schema=schema_def,
            )
        )

    return consolidated


def parse_prompt_overrides_content(content: str) -> list[PromptOverrideConfig]:
    """Parse prompt override items from YAML or JSON string content and group by field.

    Args:
        content: Raw YAML or JSON string content.

    Returns:
        list[PromptOverrideConfig]: List of parsed prompt override configurations.

    Raises:
        TypeError: If YAML content is not a list or mapping with overrides/rules.
        ValueError: If content cannot be parsed as valid YAML.

    """
    if not content.strip():
        return []

    try:
        data = yaml.safe_load(content)
    except Exception as exc:
        msg = f"Failed to parse prompt overrides YAML: {exc}"
        raise ValueError(msg) from exc

    items: list[Any]
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("overrides") or data.get("rules") or []
    else:
        msg = "Prompt overrides YAML must be a list of overrides or a mapping with 'overrides'/'rules'."
        raise TypeError(msg)

    configs: list[PromptOverrideConfig] = [
        PromptOverrideConfig.model_validate(item)
        for item in items
        if isinstance(item, dict)
    ]

    return group_prompt_overrides(configs)


def load_prompt_overrides_from_yaml(
    overrides_path: pathlib.Path,
) -> list[PromptOverrideConfig]:
    """Load prompt overrides from a YAML or JSON file.

    Args:
        overrides_path: Path to the YAML file containing prompt override definitions.

    Returns:
        list[PromptOverrideConfig]: List of PromptOverrideConfig objects.

    Raises:
        FileNotFoundError: If the specified prompt overrides file does not exist.

    """
    if not overrides_path.exists():
        msg = f"Prompt overrides file '{overrides_path}' does not exist."
        raise FileNotFoundError(msg)

    content = overrides_path.read_text(encoding="utf-8")
    return parse_prompt_overrides_content(content)


@dataclass(slots=True, frozen=True)
class ActionOverridePromptParams:
    """Parameters for constructing action override prompts."""

    target_field: str
    criteria: str
    action_name: str
    py_name: str
    py_content: str
    json_name: str
    json_content: str
    manager_names: str = ""
    manager_content: str = ""


@dataclass(slots=True, frozen=True)
class IntegrationOverridePromptParams:
    """Parameters for constructing integration override prompts."""

    target_field: str
    criteria: str
    integration_name: str
    integration_description: str
    actions_ai_descriptions: str
    connectors_ai_descriptions: str
    jobs_ai_descriptions: str


def build_action_override_prompt(params: ActionOverridePromptParams) -> str:
    """Construct prompt for action field override.

    Args:
        params: Parameters for constructing action override prompt.

    Returns:
        str: The constructed prompt.

    """
    source_block = (
        f"### SOURCE CODE & SPECIFICATIONS\n\n"
        f'<python_script filename="{params.py_name}">\n{params.py_content}\n</python_script>\n\n'
        f'<action_definition filename="{params.json_name}">\n{params.json_content}\n</action_definition>\n'
    )
    if params.manager_content and params.manager_content != "N/A":
        source_block += (
            f'\n<shared_modules filenames="{params.manager_names}">\n'
            f"{params.manager_content}\n"
            f"</shared_modules>\n"
        )

    return (
        f"{source_block}\n"
        f"---\n\n"
        f"### YOUR TASK\n\n"
        f"You are an expert security engineer generating documentation for Google SecOps SOAR.\n"
        f"Your task is to generate the '{params.target_field}' field for the action '{params.action_name}'.\n\n"
        f"You MUST strictly adhere to the source code and specifications provided above.\n\n"
        f"---\n\n"
        f"### EVALUATION RULES & CONSTRAINTS\n\n"
        f"You MUST strictly follow all of the following rules and criteria "
        f"when generating the '{params.target_field}' field:\n\n"
        f"{params.criteria}"
    )


def build_integration_override_prompt(
    params: IntegrationOverridePromptParams,
) -> str:
    """Construct prompt for integration field override.

    Args:
        params: Parameters for constructing integration override prompt.

    Returns:
        str: The constructed prompt.

    """
    return (
        f"### INTEGRATION CONTEXT\n\n"
        f"<integration_name>\n{params.integration_name}\n</integration_name>\n\n"
        f"<integration_description>\n{params.integration_description}\n</integration_description>\n\n"
        f"<actions_ai_descriptions>\n{params.actions_ai_descriptions}\n</actions_ai_descriptions>\n\n"
        f"<connectors_ai_descriptions>\n{params.connectors_ai_descriptions}\n</connectors_ai_descriptions>\n\n"
        f"<jobs_ai_descriptions>\n{params.jobs_ai_descriptions}\n</jobs_ai_descriptions>\n\n"
        f"---\n\n"
        f"### YOUR TASK\n\n"
        f"You are an expert security engineer generating documentation for Google SecOps SOAR.\n"
        f"Your task is to generate the '{params.target_field}' field "
        f"for the integration '{params.integration_name}'.\n\n"
        f"---\n\n"
        f"### EVALUATION RULES & CONSTRAINTS\n\n"
        f"You MUST strictly follow all of the following rules and criteria "
        f"when generating the '{params.target_field}' field:\n\n"
        f"{params.criteria}"
    )
