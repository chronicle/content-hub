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
from typing import Annotated

from pydantic import BaseModel, Field

from mp.core.data_models.integrations.action.ai.capabilities import (
    ActionCapabilities,  # ruff:ignore[typing-only-first-party-import]
)
from mp.core.data_models.integrations.action.ai.entity_usage import (
    EntityUsage,  # ruff:ignore[typing-only-first-party-import]
)
from mp.core.data_models.integrations.action.ai.metadata import (
    ACTION_AI_DESCRIPTION,
    ACTION_AI_SHORT_DESCRIPTION,
    CAPABILITIES_DESCRIPTION,
    ENTITY_USAGE_DESCRIPTION,
    OUTCOME_CATEGORIES_DESCRIPTION,
    PARAMETERS_DESCRIPTION,
)
from mp.core.data_models.integrations.action.ai.outcome_categories import (
    OutcomeCategories,  # ruff:ignore[typing-only-first-party-import]
)

_TYPE_MAPPING: dict[str, type] = {
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
    """Configuration item mapping a prompt template file to a field override."""

    location: str
    field_name: str
    schema_def: FieldSchemaConfig | None = Field(default=None, alias="schema")

    def resolve_location(self, base_dir: pathlib.Path | None = None) -> pathlib.Path:
        """Resolve prompt template path relative to base_dir if relative.

        Args:
            base_dir: Optional base directory to resolve relative paths against.

        Returns:
            pathlib.Path: Absolute or resolved path to the prompt template.

        """
        path = pathlib.Path(self.location)
        if path.is_absolute() or base_dir is None:
            return path
        return (base_dir / path).resolve()


class PromptOverridesFile(BaseModel):
    """Root model for prompt overrides configuration JSON file."""

    prompt_config: list[PromptOverrideConfig] = Field(default_factory=list)


class AiDescriptionOverride(BaseModel):
    ai_description: Annotated[str, Field(description=ACTION_AI_DESCRIPTION)]


class AiShortDescriptionOverride(BaseModel):
    ai_short_description: Annotated[str, Field(description=ACTION_AI_SHORT_DESCRIPTION)]


class ParametersDescriptionOverride(BaseModel):
    parameters_description: Annotated[str, Field(description=PARAMETERS_DESCRIPTION)]


class EntityUsageOverride(BaseModel):
    entity_usage: Annotated[EntityUsage, Field(description=ENTITY_USAGE_DESCRIPTION)]


class OutcomeCategoriesOverride(BaseModel):
    outcome_categories: Annotated[OutcomeCategories, Field(description=OUTCOME_CATEGORIES_DESCRIPTION)]


class CapabilitiesOverride(BaseModel):
    capabilities: Annotated[ActionCapabilities, Field(description=CAPABILITIES_DESCRIPTION)]


FIELD_TO_OVERRIDE_MODEL: dict[str, type[BaseModel]] = {
    "ai_description": AiDescriptionOverride,
    "ai_short_description": AiShortDescriptionOverride,
    "parameters_description": ParametersDescriptionOverride,
    "entity_usage": EntityUsageOverride,
    "outcome_categories": OutcomeCategoriesOverride,
    "capabilities": CapabilitiesOverride,
}
