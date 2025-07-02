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

from typing import TypedDict

import mp.core.data_models.abc


class WidgetType(mp.core.data_models.abc.RepresentableEnum):
    KEY_VALUE = 0
    EVENTS = 1
    JSON_RESULT = 2
    HTML = 3
    WALL_ACTIVITIES = 4
    ALERTS = 5
    TIMELINE = 6
    GRAPH = 7
    TEXT = 8
    POTENTIALLY_GROUPED_ALERTS = 9
    ENTITIES_HIGHLIGHTS = 10
    PENDING_STEPS = 11
    CASE_RECOMMENDATIONS = 12
    STATISTICS = 13
    CASE_DESCRIPTION = 14
    INSIGHT = 15
    CASE_ASSISTANT = 16
    CASE_APS_GRAPH = 17
    CASE_RELATED_FINDINGS = 18
    CASE_IMPACTED_RESOURCES = 19
    FORM = 20
    QUICK_ACTIONS = 21


class WidgetDefinitionScope(mp.core.data_models.abc.RepresentableEnum):
    CASE = 0
    ALERT = 1
    BOTH = 2


class BuiltWidgetDataDefinition(TypedDict):
    htmlHeight: int
    safeRendering: bool
    type: int
    widgetDefinitionScope: int


class NonBuiltWidgetDataDefinition(TypedDict):
    html_height: int
    safe_rendering: bool
    type: str
    widget_definition_scope: str


class WidgetDataDefinition(
    mp.core.data_models.abc.Buildable[BuiltWidgetDataDefinition, NonBuiltWidgetDataDefinition]
):
    html_height: int
    safe_rendering: bool
    type: WidgetType
    widget_definition_scope: WidgetDefinitionScope

    @classmethod
    def _from_built(cls, built: BuiltWidgetDataDefinition) -> WidgetDataDefinition:
        return cls(
            html_height=built["htmlHeight"],
            safe_rendering=built["safeRendering"],
            widget_definition_scope=WidgetDefinitionScope(
                built["widgetDefinitionScope"],
            ),
            type=WidgetType(built["type"]),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltWidgetDataDefinition) -> WidgetDataDefinition:
        return cls(
            html_height=non_built["html_height"],
            safe_rendering=non_built["safe_rendering"],
            widget_definition_scope=WidgetDefinitionScope.from_string(
                non_built["widget_definition_scope"],
            ),
            type=WidgetType.from_string(non_built["type"]),
        )

    def to_built(self) -> BuiltWidgetDataDefinition:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" representation of the object.

        """
        return BuiltWidgetDataDefinition(
            htmlHeight=self.html_height,
            safeRendering=self.safe_rendering,
            widgetDefinitionScope=self.widget_definition_scope.value,
            type=self.type.value,
        )

    def to_non_built(self) -> NonBuiltWidgetDataDefinition:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" representation of the object

        """
        return NonBuiltWidgetDataDefinition(
            html_height=self.html_height,
            safe_rendering=self.safe_rendering,
            widget_definition_scope=self.widget_definition_scope.to_string(),
            type=self.type.to_string(),
        )
