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


class ConnectorAiMetadata(BaseModel):
    ai_description: Annotated[
        str,
        Field(
            description=(
                "Detailed description that will be used by LLMs to understand what the connector"
                " does. This should be a concise yet informative summary of the connector's"
                " purpose, what kind of data it pulls, and the expected outcome."
                " Use markdown formatting for clarity, as this is a description for LLMs."
                " Please add a description of the data ingestion flow in numbered or bulleted"
                " points. In addition, create a table that describes the configuration"
                " parameters. How to use them, what is the expected type of value,"
                " whether the parameter is mandatory or not, and describe what each of them"
                " does. Overall the description should be divided into 3-4 sections,"
                " General description, Parameters description, and Flow description."
            ),
        ),
    ]
