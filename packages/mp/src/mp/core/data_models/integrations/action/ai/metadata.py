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

from typing import Annotated

from pydantic import BaseModel, Field

from .capabilities import ActionCapabilities  # ruff:ignore[typing-only-first-party-import]
from .entity_usage import EntityUsage  # ruff:ignore[typing-only-first-party-import]
from .outcome_categories import OutcomeCategories  # ruff:ignore[typing-only-first-party-import]


class ActionAiMetadata(BaseModel):
    ai_description: Annotated[
        str,
        Field(
            description=(
                "Detailed description that will be used by LLMs to understand what the action does."
                " This should be an informative summary of the action's purpose and expected outcome."
                " Use markdown formatting for clarity, as this is a description for LLMs."
                " The description must be divided into 3 distinct sections: 'General Description',"
                " 'Flow Description', and 'Additional Notes'."
                " Under the 'Flow Description' section, please add a description of the flow of the action"
                " in numbered or bulleted points to describe each stage of the action logically."
                " If an API call is being made during the execution of this action, it must be explicitly"
                " mentioned and detailed within this flow description."
            ),
        ),
    ]
    ai_short_description: Annotated[
        str,
        Field(
            description=(
                "A concise, high-level summary of the action's primary purpose and expected outcome."
                " This should be a direct, single-paragraph distillation of the 'General Description'"
                " designed for quick LLM parsing, completely free of step-by-step flow overhead"
                " or parameter details."
            ),
        ),
    ]
    parameters_description: Annotated[
        str,
        Field(
            description=(
                "Detailed description of the action's parameters, formatted using markdown for LLM clarity."
                "CRITICAL SOURCE CONSTRAINT: You must extract parameter information EXCLUSIVELY from the action's "
                "parameters list (under 'Parameters' or 'parameters' key in the metadata definitions). You "
                "are strictly "
                "forbidden from including, inferring, or falling back to any integration-level parameters "
                "(including parameters retrieved via siemplify.extract_configuration_param or listed under "
                "integration-level configurations)."
                "Create a table that describes these action-specific parameters with the following columns: "
                "Parameter, Type, Mandatory, Description."
                "The Description column should explain how to use the parameter and how it might affect the "
                "action's flow."
                "If there are no action-specific parameters defined, you must NOT generate a table. Instead, "
                "set this field value exactly to: 'There are no parameters for this action'."
                "If a parameter is not mandatory but code execution requires it based on the presence of other "
                "parameters, mention this relationship within its specific row description, or add an optional "
                "'Parameter Notes' section below the table (e.g., 'Either this set of parameters or this set of "
                "parameters must be configured')."
            ),
        ),
    ]
    entity_usage: Annotated[
        EntityUsage,
        Field(
            description=(
                "A detailed set of properties that describe how the action uses entities."
                " Determine each of the fields by going over the code."
            ),
        ),
    ]
    outcome_categories: Annotated[
        OutcomeCategories,
        Field(
            description=(
                "Describes what the action achieves - its expected outcomes."
                " This field classifies the action based on what it does, rather than how it operates."
            ),
        ),
    ]
    capabilities: Annotated[
        ActionCapabilities,
        Field(
            description=(
                "Fields that describe how the action operates. Determine these fields based on the"
                "metadata json and the code itself."
            ),
        ),
    ]


ActionAiMetadata.model_rebuild()
