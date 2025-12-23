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

from mp.core.data_models.common.widget.data import (
    BuiltWidgetDataDefinition,
    HtmlWidgetDataDefinition,
    NonBuiltWidgetDataDefinition,
    WidgetDefinitionScope,
    WidgetType,
)

BUILT_WIDGET_DATA_DEFINITION: BuiltWidgetDataDefinition = {
    "htmlHeight": 100,
    "safeRendering": True,
    "type": 3,
    "widgetDefinitionScope": 0,
    "htmlContent": "",
}

NON_BUILT_WIDGET_DATA_DEFINITION: NonBuiltWidgetDataDefinition = {
    "html_height": 100,
    "safe_rendering": True,
    "type": "html",
    "widget_definition_scope": "case",
}

HTML_WIDGET_DATA_DEFINITION = HtmlWidgetDataDefinition(
    html_height=100,
    safe_rendering=True,
    type=WidgetType.HTML,
    widget_definition_scope=WidgetDefinitionScope.CASE,
)

BUILT_WIDGET_DATA_DEFINITION_WITH_NONE: BuiltWidgetDataDefinition = {
    "htmlHeight": 100,
    "safeRendering": True,
    "type": 3,
    "widgetDefinitionScope": 0,
    "htmlContent": "",
}

NON_BUILT_WIDGET_DATA_DEFINITION_WITH_NONE: NonBuiltWidgetDataDefinition = {
    "html_height": 100,
    "safe_rendering": True,
    "type": "html",
    "widget_definition_scope": "case",
}

HTML_WIDGET_DATA_DEFINITION_WITH_NONE = HtmlWidgetDataDefinition(
    html_height=100,
    safe_rendering=True,
    type=WidgetType.HTML,
    widget_definition_scope=WidgetDefinitionScope.CASE,
)


class TestHtmlWidgetDataDefinitionModel:
    def test_from_built_with_valid_data(self) -> None:
        assert (
            HtmlWidgetDataDefinition.from_built("", BUILT_WIDGET_DATA_DEFINITION)
            == HTML_WIDGET_DATA_DEFINITION
        )

    def test_from_non_built_with_valid_data(self) -> None:
        assert (
            HtmlWidgetDataDefinition.from_non_built("", NON_BUILT_WIDGET_DATA_DEFINITION)
            == HTML_WIDGET_DATA_DEFINITION
        )

    def test_to_built(self) -> None:
        assert HTML_WIDGET_DATA_DEFINITION.to_built() == BUILT_WIDGET_DATA_DEFINITION

    def test_to_non_built(self) -> None:
        assert HTML_WIDGET_DATA_DEFINITION.to_non_built() == NON_BUILT_WIDGET_DATA_DEFINITION

    def test_from_built_with_none_values(self) -> None:
        assert (
            HtmlWidgetDataDefinition.from_built("", BUILT_WIDGET_DATA_DEFINITION_WITH_NONE)
            == HTML_WIDGET_DATA_DEFINITION_WITH_NONE
        )

    def test_from_non_built_with_none_values(self) -> None:
        assert (
            HtmlWidgetDataDefinition.from_non_built("", NON_BUILT_WIDGET_DATA_DEFINITION_WITH_NONE)
            == HTML_WIDGET_DATA_DEFINITION_WITH_NONE
        )

    def test_to_built_with_none_values(self) -> None:
        assert (
            HTML_WIDGET_DATA_DEFINITION_WITH_NONE.to_built()
            == BUILT_WIDGET_DATA_DEFINITION_WITH_NONE
        )

    def test_to_non_built_with_none_values(self) -> None:
        assert (
            HTML_WIDGET_DATA_DEFINITION_WITH_NONE.to_non_built()
            == NON_BUILT_WIDGET_DATA_DEFINITION_WITH_NONE
        )

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert (
            HtmlWidgetDataDefinition.from_built("", BUILT_WIDGET_DATA_DEFINITION).to_built()
            == BUILT_WIDGET_DATA_DEFINITION
        )

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            HtmlWidgetDataDefinition.from_non_built(
                "", NON_BUILT_WIDGET_DATA_DEFINITION
            ).to_non_built()
            == NON_BUILT_WIDGET_DATA_DEFINITION
        )
