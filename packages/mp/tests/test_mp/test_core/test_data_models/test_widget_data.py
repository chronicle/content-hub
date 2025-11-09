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

import pytest
from mp.core.data_models.widget.data import (
    HtmlWidgetDataDefinition,
    BuiltWidgetDataDefinition,
    NonBuiltWidgetDataDefinition,
    WidgetType,
    WidgetDefinitionScope,
)

HTML_CONTENT = """<!DOCTYPE html>
<html>
<head>
<title>Test Widget</title>
</head>
<body>
<h1>Hello, Widget!</h1>
</body>
</html>"""

BUILT_WIDGET_DATA_DEFINITION: BuiltWidgetDataDefinition = {
    "htmlHeight": 100,
    "safeRendering": True,
    "type": 3,
    "widgetDefinitionScope": 0,
    "htmlContent": HTML_CONTENT,
}

NON_BUILT_WIDGET_DATA_DEFINITION: NonBuiltWidgetDataDefinition = {
    "html_height": 100,
    "safe_rendering": True,
    "type": "HTML",
    "widget_definition_scope": "CASE",
    "html_content": HTML_CONTENT,
}

HTML_WIDGET_DATA_DEFINITION = HtmlWidgetDataDefinition(
    html_height=100,
    safe_rendering=True,
    type=WidgetType.HTML,
    widget_definition_scope=WidgetDefinitionScope.CASE,
    html_content=HTML_CONTENT,
)

BUILT_WIDGET_DATA_DEFINITION_WITH_NONE: BuiltWidgetDataDefinition = {
    "htmlHeight": 100,
    "safeRendering": True,
    "type": 3,
    "widgetDefinitionScope": 0,
    "htmlContent": None,
}

NON_BUILT_WIDGET_DATA_DEFINITION_WITH_NONE: NonBuiltWidgetDataDefinition = {
    "html_height": 100,
    "safe_rendering": True,
    "type": "HTML",
    "widget_definition_scope": "CASE",
    "html_content": None,
}

HTML_WIDGET_DATA_DEFINITION_WITH_NONE = HtmlWidgetDataDefinition(
    html_height=100,
    safe_rendering=True,
    type=WidgetType.HTML,
    widget_definition_scope=WidgetDefinitionScope.CASE,
    html_content=None,
)


class TestHtmlWidgetDataDefinitionModel:
    def test_from_built_with_valid_data(self):
        assert HtmlWidgetDataDefinition.from_built("", BUILT_WIDGET_DATA_DEFINITION) == HTML_WIDGET_DATA_DEFINITION

    def test_from_non_built_with_valid_data(self):
        assert HtmlWidgetDataDefinition.from_non_built("", NON_BUILT_WIDGET_DATA_DEFINITION) == HTML_WIDGET_DATA_DEFINITION

    def test_to_built(self):
        assert HTML_WIDGET_DATA_DEFINITION.to_built() == BUILT_WIDGET_DATA_DEFINITION

    def test_to_non_built(self):
        assert HTML_WIDGET_DATA_DEFINITION.to_non_built() == NON_BUILT_WIDGET_DATA_DEFINITION

    def test_from_built_with_none_values(self):
        assert HtmlWidgetDataDefinition._from_built("", BUILT_WIDGET_DATA_DEFINITION_WITH_NONE) == HTML_WIDGET_DATA_DEFINITION_WITH_NONE

    def test_from_non_built_with_none_values(self):
        assert HtmlWidgetDataDefinition._from_non_built("", NON_BUILT_WIDGET_DATA_DEFINITION_WITH_NONE) == HTML_WIDGET_DATA_DEFINITION_WITH_NONE

    def test_to_built_with_none_values(self):
        assert HTML_WIDGET_DATA_DEFINITION_WITH_NONE.to_built() == BUILT_WIDGET_DATA_DEFINITION_WITH_NONE

    def test_to_non_built_with_none_values(self):
        assert HTML_WIDGET_DATA_DEFINITION_WITH_NONE.to_non_built() == NON_BUILT_WIDGET_DATA_DEFINITION_WITH_NONE

    def test_from_built_to_built_is_idempotent(self):
        assert HtmlWidgetDataDefinition._from_built("", BUILT_WIDGET_DATA_DEFINITION).to_built() == BUILT_WIDGET_DATA_DEFINITION

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert HtmlWidgetDataDefinition._from_non_built("", NON_BUILT_WIDGET_DATA_DEFINITION).to_non_built() == NON_BUILT_WIDGET_DATA_DEFINITION
