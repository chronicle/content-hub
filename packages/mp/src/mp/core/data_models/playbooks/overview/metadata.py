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

import json
from typing import TYPE_CHECKING, NotRequired, Self, TypedDict

import yaml

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils
from mp.core.data_models.abc import RepresentableEnum
from mp.core.data_models.playbooks.widget.metadata import PlaybookWidgetMetadata

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import WidgetName
    from mp.core.data_models.playbooks.widget.metadata import BuiltPlaybookWidgetMetadata


class OverviewType(RepresentableEnum):
    PLAYBOOK_DEFAULT = 0
    REGULAR = 1
    SYSTEM_ALERT = 2
    SYSTEM_CASE = 3
    ALERT_TYPE = 4


class OverviewWidgetDetails(TypedDict):
    title: str
    size: str
    order: int


class BuiltOverviewDetails(TypedDict):
    Identifier: str
    Name: str
    Creator: str | None
    PlaybookDefinitionIdentifier: str
    Type: int
    AlertRuleType: str | None
    Roles: list[int]
    Widgets: list[BuiltPlaybookWidgetMetadata]


class BuiltOverview(TypedDict):
    OverviewTemplate: BuiltOverviewDetails
    Roles: NotRequired[list[str]]


class NonBuiltOverview(TypedDict):
    identifier: str
    name: str
    creator: str | None
    playbook_id: str
    widgets_details: list[OverviewWidgetDetails]
    type: str
    alert_rule_type: str | None
    roles: list[int]
    role_names: list[str]


class Overview(mp.core.data_models.abc.SequentialMetadata[BuiltOverview, NonBuiltOverview]):
    identifier: str
    name: str
    creator: str | None
    playbook_id: str
    type_: OverviewType
    alert_rule_type: str | None
    roles: list[int]
    role_names: list[str]
    widgets: list[PlaybookWidgetMetadata]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create a list of Overview objects from a built playbook path.

        Args:
            path: The path to the built playbook.

        Returns:
            A list of Overview objects.

        Raises:
            ValueError: If the file at `path` fails to load or parse as JSON.

        """
        if not path.exists():
            return []
        built_playbook: str = path.read_text(encoding="utf-8")
        try:
            full_playbook = json.loads(built_playbook)
            built_overview: list[BuiltOverview] = full_playbook["OverviewTemplatesDetails"]
            return [cls._from_built(overview) for overview in built_overview]
        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {path}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create a list of Overview objects from a non-built playbook path.

        Args:
            path: The path to the non-built playbook directory.

        Returns:
            A list of Overview objects.

        """
        meta_path: Path = path / mp.core.constants.OVERVIEWS_FILE_NAME
        if not meta_path.exists():
            return []

        all_widget: list[PlaybookWidgetMetadata] = PlaybookWidgetMetadata.from_non_built_path(path)
        res: list[Self] = []

        for non_built_overview in yaml.safe_load(meta_path.read_text(encoding="utf-8")):
            widget_details: list[OverviewWidgetDetails] = non_built_overview.get(
                "widgets_details", []
            )
            widget_names: frozenset[WidgetName] = frozenset([
                w_d["title"] for w_d in widget_details
            ])
            widgets: list[PlaybookWidgetMetadata] = [
                w for w in all_widget if w.title in widget_names
            ]
            ov: Self = cls._from_non_built(non_built_overview)
            ov.widgets = widgets
            res.append(ov)

        return res

    @classmethod
    def _from_built(cls, built: BuiltOverview) -> Self:
        return cls(
            identifier=built["OverviewTemplate"]["Identifier"],
            name=built["OverviewTemplate"]["Name"],
            creator=built["OverviewTemplate"]["Creator"],
            playbook_id=built["OverviewTemplate"]["PlaybookDefinitionIdentifier"],
            type_=OverviewType(built["OverviewTemplate"]["Type"]),
            alert_rule_type=built["OverviewTemplate"]["AlertRuleType"],
            roles=built["OverviewTemplate"]["Roles"],
            role_names=built.get("Roles", []),
            widgets=[
                PlaybookWidgetMetadata.from_built("", built_widget)
                for built_widget in built["OverviewTemplate"]["Widgets"]
            ],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltOverview) -> Self:
        return cls(
            identifier=non_built["identifier"],
            name=non_built["name"],
            creator=non_built["creator"],
            playbook_id=non_built["playbook_id"],
            type_=OverviewType.from_string(non_built["type"]),
            alert_rule_type=non_built["alert_rule_type"],
            roles=non_built["roles"],
            role_names=non_built.get("role_names", []),
            widgets=[],
        )

    def to_built(self) -> BuiltOverview:
        """Convert the Overview to its "built" representation.

        Returns:
            A BuiltOverview dictionary.

        """
        return BuiltOverview(
            OverviewTemplate=BuiltOverviewDetails(
                Identifier=self.identifier,
                Name=self.name,
                Creator=self.creator,
                PlaybookDefinitionIdentifier=self.playbook_id,
                Type=self.type_.value,
                AlertRuleType=self.alert_rule_type,
                Roles=self.roles,
                Widgets=[PlaybookWidgetMetadata.to_built(w) for w in self.widgets],
            ),
            Roles=self.role_names,
        )

    def to_non_built(self) -> NonBuiltOverview:
        """Convert the Overview to its "non-built" representation.

        Returns:
            A NonBuiltOverview dictionary.

        """
        non_built: NonBuiltOverview = NonBuiltOverview(
            identifier=self.identifier,
            name=self.name,
            creator=self.creator,
            playbook_id=self.playbook_id,
            type=self.type_.to_string(),
            alert_rule_type=self.alert_rule_type,
            roles=self.roles,
            role_names=self.role_names,
            widgets_details=[
                OverviewWidgetDetails(
                    title=w.title,
                    size=w.widget_size.to_string(),
                    order=w.order,
                )
                for w in self.widgets
            ],
        )
        return non_built
