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

"""Typed models for Chronicle API JSON responses consumed by the client."""

from __future__ import annotations

from pydantic import Base64Bytes, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _ChronicleModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Integration(_ChronicleModel):
    """A Chronicle Integration resource subset for listing and resolution."""

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
    """Response body of integrations.list."""

    integrations: list[Integration] = Field(default_factory=list)
    next_page_token: str | None = None


class Media(_ChronicleModel):
    """Inline payload and descriptors for the shared Media type."""

    inline: Base64Bytes | None = None
    content_type: str | None = None
    filename: str | None = None
    length: str | None = None


class ExportResponse(_ChronicleModel):
    """Envelope returned by integration and playbook export endpoints."""

    media: Media | None = None


class WorkflowMenuCard(_ChronicleModel):
    """A playbook or workflow menu card subset for identifier resolution."""

    name: str | None = None
    identifier: str | None = None


class WorkflowMenuCardsResponse(_ChronicleModel):
    """Response body of legacyPlaybooks menu cards listing."""

    payload: list[WorkflowMenuCard] = Field(default_factory=list)
