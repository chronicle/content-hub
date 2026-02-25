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

from .capabilities import ActionCapabilities  # noqa: TC001
from .categories import AiCategories  # noqa: TC001
from .entity_usage import EntityUsage  # noqa: TC001


class ActionAiMetadata(BaseModel):
    ai_description: Annotated[
        str,
        Field(
            description=(
                "Detailed description that will be used by LLMs to understand what the action does."
                " This should be a concise yet informative summary of the action's purpose and"
                " expected outcome."
                " Use markdown formatting for clarity, as this is a description for LLMs."
                " Please add a description of the flow of the action in numbered or bulleted points"
                " to describe each stage of the action logically. In addition, create a table that"
                " describes the parameters. How to use them, what is the expected type of value,"
                " whether the parameter is mandatory or not, and describe what each of them does"
                " and how it might affect the action's flow."
                " If you notice a parameter is not mandatory but in the code it is required to"
                " fill it with a value depending on whether other parameters are filled or not -"
                " mention it in the description of the parameter if it makes sense, or in an"
                " 'additional notes' section of the entire description of the action."
                " Something like 'either this set of parameters or this set of"
                " parameters must be configured for the action to run'."
                " If there are no parameters, mention that under the parameters section."
                " Overall the description should be decided into 3-4 sections, General description,"
                " Parameters description, additional notes, and Flow description."
                " If there are no parameters just mention that there are no parameters"
                " in the parameters section or additional notes section."
            ),
        ),
    ]
    capabilities: Annotated[
        ActionCapabilities,
        Field(
            description=(
                "Fields that describe how the action operates. Determine these fields based on the"
                "metadata json and the code itself."
            )
        ),
    ]
    categories: Annotated[
        AiCategories,
        Field(
            description=(
                "Categories that describe the action's capabilities."
                " These tags are inferred based on the fields."
            )
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
