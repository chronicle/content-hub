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

"""Module Name: [datamodels] defined datamodels classes."""
from __future__ import annotations

from typing import Any

from TIPCommon import dict_to_flat
from .utils import rec_mask_sensitive_values


class BaseModel:
    """Base model for inheritance."""

    def __init__(self, raw_data: dict[str, Any]) -> None:
        self.raw_data = raw_data

    def to_json(self) -> dict[str, Any]:
        return self.raw_data

    def to_csv(self) -> dict[str, Any]:
        return dict_to_flat(self.raw_data)


class ChildPages(BaseModel):
    """Model for the json resonse to have trasformation methods."""

    def __init__(self, raw_data: dict[str, Any], **kwargs) -> None:
        raw_data = rec_mask_sensitive_values(raw_data, sensitive_keys=["base", "self"])
        super().__init__(raw_data)
        self.kwargs = kwargs


class ListPages(BaseModel):
    """Model for the json response to have transformation methods."""

    def __init__(
        self,
        raw_data: dict[str, Any],
        id: str | None = None,
        title: str | None = None,
        space: str | None = None,
        status: str | None = None,
        history: str | None = None,
        **kwargs,
    ) -> None:
        raw_data = rec_mask_sensitive_values(raw_data, sensitive_keys=["base", "self"])
        super().__init__(raw_data)
        self.id = id
        self.title = title
        self.space = space
        self.name = self.space["name"]
        self.status = status
        self.history = history
        self.created = self.history["createdDate"]
        self.kwargs = kwargs

    def to_table(self) -> dict[str, str]:
        return {
            "ID": self.id,
            "Title": self.title,
            "Space": self.name,
            "Status": self.status,
            "Created": self.created,
        }


class PageComments(BaseModel):
    """Model for the json resonse to have trasformation methods."""

    def __init__(self, raw_data: dict[str, Any], **kwargs) -> None:
        raw_data = rec_mask_sensitive_values(raw_data, sensitive_keys=["base", "self"])
        super().__init__(raw_data)
        self.kwargs = kwargs


class PageByID(BaseModel):
    """Model for the json resonse to have trasformation methods."""

    def __init__(self, raw_data: dict[str, Any], **kwargs) -> None:
        raw_data = rec_mask_sensitive_values(raw_data, sensitive_keys=["base", "self"])
        super().__init__(raw_data)
        self.kwargs = kwargs
