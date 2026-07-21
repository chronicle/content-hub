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
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import yaml

from mp.build_project.restructure.views.build import ViewBuilder
from mp.build_project.restructure.views.deconstruct import ViewDeconstructor
from mp.core.data_models.common.condition.condition_group import ConditionGroup, LogicalOperator
from mp.core.data_models.common.overview.metadata import (
    Overview,
    OverviewType,
)
from mp.core.data_models.common.widget.data import (
    HtmlWidgetDataDefinition,
    WidgetDefinitionScope,
    WidgetSize,
    WidgetType,
)
from mp.core.data_models.playbooks.widget.metadata import PlaybookWidgetMetadata


def test_view_deconstruct_and_build_roundtrip(tmp_path: Path) -> None:
    # 1. Setup mock Overview object
    overview = Overview(
        identifier="system_case_default",
        name="Default Case View",
        creator="system",
        playbook_id="playbook_1",
        type_=OverviewType.SYSTEM_CASE,
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
    assert view_data["identifier"] == "system_case_default"
    assert view_data["type"] == "system_case"
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
    assert built_data["OverviewTemplate"]["Identifier"] == "system_case_default"
    assert built_data["OverviewTemplate"]["Type"] == OverviewType.SYSTEM_CASE.value
    assert len(built_data["OverviewTemplate"]["Widgets"]) == 2

    # Check HTML content was successfully re-loaded into the built JSON
    widgets = built_data["OverviewTemplate"]["Widgets"]
    html_widget = next(w for w in widgets if w["Title"] == "Widget One")
    html_widget_def = json.loads(html_widget["DataDefinitionJson"])
    assert html_widget_def["htmlContent"] == "<h1>Hello World</h1>"


def test_view_deconstructor_html_widget_oserror(tmp_path: Path) -> None:
    """Test that OSError when writing an HTML widget file raises OSError and logs exception."""
    overview = Overview(
        identifier="system_case_default",
        name="Default Case View",
        creator="system",
        playbook_id="playbook_1",
        type_=OverviewType.SYSTEM_CASE,
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
        ],
    )

    src_dir = tmp_path / "src"
    deconstructor = ViewDeconstructor(overview, src_dir)

    orig_write_text = Path.write_text
    err_msg = "Disk full"

    def side_effect(self: Path, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if self.suffix == ".html":
            raise OSError(err_msg)
        return orig_write_text(self, *args, **kwargs)

    with (
        mock.patch.object(Path, "write_text", autospec=True, side_effect=side_effect),
        pytest.raises(OSError, match="Disk full"),
    ):
        deconstructor.deconstruct()


def test_from_non_built_with_missing_optional_fields(tmp_path: Path) -> None:
    """Verify Overview.from_non_built_view_path succeeds when optional fields are omitted from view.yaml."""
    src_dir = tmp_path / "minimal_view"
    src_dir.mkdir()

    # Create minimal view.yaml missing creator, alert_rule_type, roles, etc.
    with (src_dir / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(
            {
                "identifier": "min_uuid",
                "name": "Minimal View",
                "type": "system_case",
                "widgets_details": [],
            },
            f,
        )

    (src_dir / "widgets").mkdir()

    overview = Overview.from_non_built_view_path(src_dir)
    assert overview.identifier == "min_uuid"
    assert overview.name == "Minimal View"
    assert overview.creator is None
    assert overview.alert_rule_type is None
    assert overview.roles == []
    assert overview.role_names == []


def test_from_non_built_with_null_widget_size(tmp_path: Path) -> None:
    """Verify Overview.from_non_built_view_path handles size: null in widgets_details without raising error."""
    src_dir = tmp_path / "null_size_view"
    src_dir.mkdir()

    with (src_dir / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(
            {
                "identifier": "null_size_uuid",
                "name": "Null Size View",
                "type": "system_case",
                "widgets_details": [{"title": "Widget One", "order": 1, "size": None}],
            },
            f,
        )

    (src_dir / "widgets").mkdir()
    with (src_dir / "widgets" / "Widget One.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(
            {
                "title": "Widget One",
                "description": "Widget One",
                "identifier": "w1",
                "order": 1,
                "template_identifier": "temp_1",
                "type": "key_value",
                "data_definition": {},
                "widget_size": "half_width",
                "action_widget_template_id": None,
                "step_id": None,
                "step_integration": None,
                "block_step_id": None,
                "block_step_instance_name": None,
                "present_if_empty": False,
                "conditions_group": {"logical_operator": "and", "conditions": []},
                "integration_name": None,
            },
            f,
        )

    overview = Overview.from_non_built_view_path(src_dir)
    assert len(overview.widgets) == 1
    # Original widget_size from widget file should be preserved since w_d size is None
    assert overview.widgets[0].widget_size == WidgetSize.HALF_WIDTH
