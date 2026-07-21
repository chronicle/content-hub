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

"""Typed models for the Chronicle API JSON responses consumed by the dev-env client.

Responses are parsed once into these models at the boundary and accessed via attributes,
rather than navigated as raw dicts. Only the fields the client actually consumes are
modelled; unknown fields are ignored (``extra="ignore"``).
"""

from __future__ import annotations

from pydantic import Base64Bytes, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _ChronicleModel(BaseModel):
    """Base for Chronicle API models: camelCase JSON aliases, tolerant of unknown fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class Integration(_ChronicleModel):
    """A Chronicle ``Integration`` resource (subset used for listing/resolution)."""

    name: str | None = None
    identifier: str | None = None
    display_name: str | None = None
    description: str | None = None
    version: str | None = None
    latest_version: str | None = None
    production_identifier: str | None = None
    python_version: str | None = None
    categories: list[str] = Field(default_factory=list)
    image_base64: str | None = None
    svg_icon: str | None = None
    custom: bool | None = None
    certified: bool | None = None
    staging: bool | None = None
    internal: bool | None = None
    update_available: bool | None = None


class ListIntegrationsResponse(_ChronicleModel):
    """Response body of ``integrations.list``."""

    integrations: list[Integration] = Field(default_factory=list)
    next_page_token: str | None = None


class Media(_ChronicleModel):
    """Subset of the shared ``Media`` type: the inline payload and its descriptors.

    ``inline`` holds the media bytes when the reference type is INLINE; ``Base64Bytes``
    decodes the base64 JSON value into raw bytes on parse.
    """

    inline: Base64Bytes | None = None
    content_type: str | None = None
    filename: str | None = None
    length: str | None = None


class ExportResponse(_ChronicleModel):
    """Envelope returned by the integration/playbook export methods: ``{ "media": Media }``."""

    media: Media | None = None
