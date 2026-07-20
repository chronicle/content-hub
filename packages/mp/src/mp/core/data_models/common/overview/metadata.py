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
import logging
from typing import TYPE_CHECKING, NotRequired, Self, TypedDict, cast

import mp.core.constants
import mp.core.utils
from mp.core.data_models.abc import RepresentableEnum, SequentialMetadata
from mp.core.data_models.common.widget.data import WidgetSize
from mp.core.data_models.playbooks.widget.metadata import PlaybookWidgetMetadata
from mp.core.file_utils import load_yaml_file

logger: logging.Logger = logging.getLogger(__name__)

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
    SYSTEM_DEFAULT_CASE = 5
    SYSTEM_DEFAULT_ALERT = 6
    SYSTEM_DETECTION = 7


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


class Overview(SequentialMetadata[BuiltOverview, NonBuiltOverview]):
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

        overviews_data = cast("list[NonBuiltOverview]", load_yaml_file(meta_path) or [])
        for non_built_overview in overviews_data:
            widget_details: list[OverviewWidgetDetails] = non_built_overview.get("widgets_details", [])
            widget_names: frozenset[WidgetName] = frozenset([w_d["title"] for w_d in widget_details])
            widgets: list[PlaybookWidgetMetadata] = [w for w in all_widget if w.title in widget_names]
            ov: Self = cls._from_non_built(non_built_overview)
            ov.widgets = widgets
            res.append(ov)

        return res

    @classmethod
    def from_non_built_view_path(cls, path: Path) -> Self:
        """Create an Overview object from a non-built view directory path.

        Args:
            path: The path to the non-built view directory (e.g. content/views/some_view).

        Returns:
            An Overview object.

        Raises:
            FileNotFoundError: If the view.yaml file doesn't exist.
            ValueError: If a widget declared in widgets_details cannot be found in the widgets directory.

        """
        view_yaml_path: Path = path / mp.core.constants.VIEW_FILE_NAME
        if not view_yaml_path.exists():
            msg: str = f"Missing view config at: {view_yaml_path}"
            raise FileNotFoundError(msg)

        non_built_view: NonBuiltOverview = cast(
            "NonBuiltOverview",
            load_yaml_file(view_yaml_path) or {},
        )

        # Load all widgets from widgets/ directory
        all_widget: list[PlaybookWidgetMetadata] = PlaybookWidgetMetadata.from_non_built_path(path)
        all_widget.sort(key=lambda w: w.order)

        widget_details: list[OverviewWidgetDetails] = non_built_view.get("widgets_details") or []
        widget_details.sort(key=lambda wd: wd.get("order") or 0)

        widget_by_title: dict[str, list[PlaybookWidgetMetadata]] = {}
        for w in all_widget:
            if w.title:
                widget_by_title.setdefault(w.title, []).append(w)

        widgets: list[PlaybookWidgetMetadata] = []
        for w_d in widget_details:
            title = w_d.get("title")
            if title and title in widget_by_title and widget_by_title[title]:
                widget = widget_by_title[title].pop(0)
                if w_d.get("order") is not None:
                    widget.order = w_d["order"]
                if w_d.get("size") is not None:
                    widget.widget_size = WidgetSize.from_string(w_d["size"])
                widgets.append(widget)
            elif title:
                err_msg = f"Widget '{title}' declared in widgets_details but not found in widgets directory."
                logger.error(err_msg)
                raise ValueError(err_msg)

        ov: Self = cls._from_non_built(non_built_view)
        ov.widgets = widgets

        return ov

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
            widgets=sorted(
                [
                    PlaybookWidgetMetadata.from_built("", built_widget)
                    for built_widget in built["OverviewTemplate"]["Widgets"]
                ],
                key=lambda w: w.order,
            ),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltOverview) -> Self:
        raw_type = non_built.get("type") or "system_case"
        return cls(
            identifier=non_built.get("identifier") or "",
            name=non_built.get("name") or "",
            creator=non_built.get("creator"),
            playbook_id=non_built.get("playbook_id") or "",
            type_=OverviewType.from_string(raw_type),
            alert_rule_type=non_built.get("alert_rule_type"),
            roles=non_built.get("roles") or [],
            role_names=non_built.get("role_names") or [],
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
                for w in sorted(self.widgets, key=lambda w: w.order)
            ],
        )
        return non_built
