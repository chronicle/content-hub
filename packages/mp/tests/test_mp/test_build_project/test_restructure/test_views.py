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

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003

import yaml

from mp.build_project.restructure.views.build import ViewBuilder
from mp.build_project.restructure.views.deconstruct import ViewDeconstructor
from mp.core.data_models.common.condition.condition_group import ConditionGroup, LogicalOperator
from mp.core.data_models.common.widget.data import (
    HtmlWidgetDataDefinition,
    WidgetDefinitionScope,
    WidgetSize,
    WidgetType,
)
from mp.core.data_models.playbooks.overview.metadata import (
    Overview,
    OverviewType,
)
from mp.core.data_models.playbooks.widget.metadata import PlaybookWidgetMetadata


def test_view_deconstruct_and_build_roundtrip(tmp_path: Path) -> None:
    # 1. Setup mock Overview object
    overview = Overview(
        identifier="system_case_v2_default",
        name="Default Case View",
        creator="system",
        playbook_id="playbook_1",
        type_=OverviewType.SYSTEM_CASE_V2,
        alert_rule_type=None,
        roles=[1, 2],
        role_names=["Tier 1", "Tier 2"],
        widgets=[
            PlaybookWidgetMetadata(
                title="Widget One",
                description="HTML Widget",
                identifier="widget_one_id",
                order=1,
                template_identifier="temp_one",
                type=WidgetType.HTML,
                data_definition=HtmlWidgetDataDefinition(
                    html_height=100,
                    safe_rendering=True,
                    widget_definition_scope=WidgetDefinitionScope.ALERT,
                    type=WidgetType.HTML,
                    html_content="<h1>Hello World</h1>",
                ),
                widget_size=WidgetSize.HALF_WIDTH,
                action_widget_template_id=None,
                step_id=None,
                step_integration=None,
                block_step_id=None,
                block_step_instance_name=None,
                present_if_empty=False,
                conditions_group=ConditionGroup(logical_operator=LogicalOperator.OR, conditions=[]),
                integration_name=None,
            ),
            PlaybookWidgetMetadata(
                title="Widget Two",
                description="Regular Widget",
                identifier="widget_two_id",
                order=2,
                template_identifier="temp_two",
                type=WidgetType.KEY_VALUE,
                data_definition="{}",
                widget_size=WidgetSize.FULL_WIDTH,
                action_widget_template_id=None,
                step_id=None,
                step_integration=None,
                block_step_id=None,
                block_step_instance_name=None,
                present_if_empty=True,
                conditions_group=ConditionGroup(logical_operator=LogicalOperator.OR, conditions=[]),
                integration_name=None,
            ),
        ],
    )

    # 2. Deconstruct
    src_dir = tmp_path / "src"
    deconstructor = ViewDeconstructor(overview, src_dir)
    deconstructor.deconstruct()

    # Assert deconstructed files exist
    assert (src_dir / "view.yaml").exists()

    view_data = yaml.safe_load((src_dir / "view.yaml").read_text(encoding="utf-8"))
    assert view_data["identifier"] == "system_case_v2_default"
    assert view_data["type"] == "system_case_v2"
    assert len(view_data["widgets_details"]) == 2

    assert (src_dir / "widgets").exists()
    assert (src_dir / "widgets" / "Widget One.yaml").exists()
    assert (src_dir / "widgets" / "Widget One.html").exists()
    assert (src_dir / "widgets" / "Widget Two.yaml").exists()
    assert not (src_dir / "widgets" / "Widget Two.html").exists()

    assert (src_dir / "widgets" / "Widget One.html").read_text(encoding="utf-8") == "<h1>Hello World</h1>"

    # 3. Build
    out_dir = tmp_path / "out"
    builder = ViewBuilder(src_dir, out_dir)
    builder.build()

    # Assert built file exists
    assert (out_dir / "src.json").exists()

    built_data = json.loads((out_dir / "src.json").read_text(encoding="utf-8"))
    assert built_data["OverviewTemplate"]["Identifier"] == "system_case_v2_default"
    assert built_data["OverviewTemplate"]["Type"] == OverviewType.SYSTEM_CASE_V2.value
    assert len(built_data["OverviewTemplate"]["Widgets"]) == 2

    # Check HTML content was successfully re-loaded into the built JSON
    widgets = built_data["OverviewTemplate"]["Widgets"]
    html_widget = next(w for w in widgets if w["Title"] == "Widget One")
    html_widget_def = json.loads(html_widget["DataDefinitionJson"])
    assert html_widget_def["htmlContent"] == "<h1>Hello World</h1>"
