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

""" Data model classes used in Google Asset Inventory integration."""
from __future__ import annotations

from itertools import chain
from typing import Any

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from . import constants
from .UtilsManager import exclude_fields_from_dict, extract_fields_from_dict


class BaseModel:
    """
    Parent class that provides resouce details
    """

    def __init__(self, raw_data: dict):
        self.raw_data = raw_data

    def to_json(self) -> dict:
        """Returns a single resource detail

        Returns:
            Data to be used for JSON results
        """
        return self.raw_data


class Resource(BaseModel):
    """Defines the structure for a Resource"""

    def __init__(self, raw_data: dict, resource_name: str):
        super().__init__(raw_data)
        self.resource_name = resource_name

    def to_json(
        self,
        logger: SiemplifyLogger = None,
        fields_to_return: list[list[str]] = (),
        fields_to_exclude: list[list[str]] = (),
    ) -> dict:
        resulting_json_data = exclude_fields_from_dict(
            logger, super().to_json(), fields_to_exclude
        )
        if [constants.DEFAULT_FIELDS_TO_RETURN] in fields_to_return:
            return resulting_json_data

        # This is needed to ensure that if some nested key is excluded, it's
        # parent dict will stay in the payload.
        for field in fields_to_exclude:
            if len(field) <= 1:
                continue

            field_extracted = any(
                set(field[:-1] or field).issubset(_field)
                for _field in fields_to_return
                if len(_field)
            )

            if not field_extracted:
                fields_to_return.append(field[:-1])

        return extract_fields_from_dict(logger, resulting_json_data, fields_to_return)


class ResourceSnapshot(BaseModel):
    """Defines the structure for a Resource Snapshot"""

    def __init__(self, raw_data: dict, asset_name: str):
        super().__init__(raw_data)
        self.asset_name = asset_name


class AccessControlList(BaseModel):
    """Defines the structure for an Access Control List."""

    def __init__(
        self,
        raw_data: dict[str, Any],
        resources: list[str],
        roles: list[str],
        permissions: list[str],
    ):
        super().__init__(raw_data=raw_data)
        self.resources = resources
        self.roles = roles
        self.permissions = permissions


class AnalysisQueryResult(BaseModel):
    """Defines the structure for an Analysis Query Result."""

    def __init__(
        self,
        raw_data: dict[str, Any],
        attached_resource_full_name: str,
        iam_binding_role: str,
        access_control_lists: list[AccessControlList],
    ):
        super().__init__(raw_data=raw_data)
        self.resource_full_name = attached_resource_full_name
        self.iam_binding_role = iam_binding_role
        self.access_control_lists = access_control_lists

    def get_unique_roles(self) -> set[str]:
        return set(
            role
            for role in chain(*map(lambda acl: acl.roles, self.access_control_lists))
        )

    def get_unique_permissions(self) -> set[str]:
        return set(
            role
            for role in chain(
                *map(lambda acl: acl.permissions, self.access_control_lists)
            )
        )
