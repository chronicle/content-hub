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

from .action_capabilities import ActionCapabilities  # noqa: TC001
from .action_tags import ActionTags  # noqa: TC001
from .entity_usage import EntityUsage  # noqa: TC001


class ActionAiMetadata(BaseModel):
    capabilities: Annotated[
        ActionCapabilities,
        Field(
            description=(
                "Fields that describe how the action operates. Determine these fields based on the"
                "metadata json and the code itself."
            )
        ),
    ]
    tags: Annotated[
        ActionTags,
        Field(
            description=(
                "Tags that describe the action's capabilities."
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
