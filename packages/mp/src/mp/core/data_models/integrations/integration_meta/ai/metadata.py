# Copyright 2025 Google LLC
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

from .product_categories import IntegrationProductCategories  # noqa: TC001


class IntegrationAiMetadata(BaseModel):
    product_categories: Annotated[
        IntegrationProductCategories,
        Field(
            description=(
                "Categories that describe the integration's capabilities as a security product."
                " It shows the category and explains when to use it and the expected outcome"
                " of the usage."
            )
        ),
    ]
