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

from pathlib import Path  # noqa: TC003
from unittest import mock

import yaml
from typer.testing import CliRunner

from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.sub_commands.push import push_app

runner = CliRunner()


@mock.patch("mp.dev_env.sub_commands.view.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.pull.get_backend_api")
def test_pull_view_cli(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Setup mock backend API
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    # Mock list_views response
    mock_api.list_views.return_value = [
        {"Identifier": "system_case_default", "Name": "Default Case View"}
    ]

    # Mock download_view response (flat camelCase REST API structure)
    mock_api.download_view.return_value = {
        "identifier": "system_case_default",
        "name": "Default Case View",
        "creator": "system",
        "playbookIdentifier": "playbook_1",
        "type": 3,  # SYSTEM_CASE
        "alertRuleType": None,
        "widgets": [
            {
                "metadata": {
                    "title": "Widget One",
                    "description": None,
                    "identifier": "widget_one_id",
                    "order": 1,
                    "templateIdentifier": "temp_one",
                    "type": 3,  # HTML
                    "width": 1,
                    "actionWidgetTemplateIdentifier": None,
                    "stepIdentifier": None,
                    "stepIntegration": None,
                    "blockStepIdentifier": None,
                    "blockStepInstanceName": None,
                    "presentIfEmpty": False,
                    "conditionsGroup": {"logicalOperator": 1, "conditions": []},
                    "integrationName": None,
                },
                "config": {
                    "htmlHeight": 100,
                    "safeRendering": True,
                    "widgetDefinitionScope": 1,
                    "type": 3,
                    "htmlContent": "<h1>Hello</h1>",
                },
            }
        ],
        "roles": [1, 2],
        "roleNames": ["Tier 1", "Tier 2"],
    }

    dst_dir = tmp_path / "content_views"

    # Invoke mp pull view command
    # Usage: mp pull view "Default Case View" --custom <dst_dir>
    result = runner.invoke(
        pull_app,
        ["view", "Default Case View", "--custom", str(dst_dir)],
    )

    assert result.exit_code == 0

    # Verify download_view was called with the identifier
    mock_api.download_view.assert_called_once_with("system_case_default")

    # Verify files are written to tmp_path / content_views / system_case_default
    view_folder = dst_dir / "system_case_default"
    assert view_folder.exists()
    assert (view_folder / "view.yaml").exists()
    assert (view_folder / "widgets" / "Widget One.yaml").exists()
    assert (view_folder / "widgets" / "Widget One.html").exists()

    assert (view_folder / "widgets" / "Widget One.html").read_text(encoding="utf-8") == "<h1>Hello</h1>"


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_cli(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Setup mock backend API
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api
    mock_api.upload_view.return_value = {"success": True}
    mock_api.list_views.return_value = [{"identifier": "system_case_default", "id": 100}]
    mock_api.download_view.return_value = {"widgets": [{"metadata": {"identifier": "widget_one_id"}}]}

    # Setup source directory structure to build from
    src_dir = tmp_path / "views"
    view_folder = src_dir / "system_case_default"
    view_folder.mkdir(parents=True)

    # Create view.yaml
    view_yaml_data = {
        "identifier": "system_case_default",
        "name": "Default Case View",
        "creator": "system",
        "playbook_id": "playbook_1",
        "type": "system_case",
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": [{"title": "Widget One", "size": "half_width", "order": 1}],
    }
    with (view_folder / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(view_yaml_data, f)

    # Create widgets/ folder and Widget One.yaml / Widget One.html
    widgets_dir = view_folder / "widgets"
    widgets_dir.mkdir()
    widget_yaml_data = {
        "title": "Widget One",
        "description": "HTML Widget",
        "identifier": "widget_one_id",
        "order": 1,
        "template_identifier": "temp_one",
        "type": "html",
        "data_definition": {
            "html_height": 100,
            "safe_rendering": True,
            "widget_definition_scope": "alert",
            "type": "html",
        },
        "widget_size": "half_width",
        "action_widget_template_id": None,
        "step_id": None,
        "step_integration": None,
        "block_step_id": None,
        "block_step_instance_name": None,
        "present_if_empty": False,
        "conditions_group": {"logical_operator": "and", "conditions": []},
        "integration_name": None,
    }
    with (widgets_dir / "Widget One.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(widget_yaml_data, f)
    (widgets_dir / "Widget One.html").write_text("<h1>Hello from push</h1>", encoding="utf-8")

    # Invoke mp push view command
    # Usage: mp push view "system_case_default" --custom <src_dir>
    with mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"):
        result = runner.invoke(
            push_app,
            ["view", "system_case_default", "--custom", str(src_dir)],
        )

    assert result.exit_code == 0

    # Verify upload_view was called with built flat camelCase JSON structure
    mock_api.upload_view.assert_called_once()
    called_args = mock_api.upload_view.call_args[0][0]

    assert called_args["identifier"] == "system_case_default"
    assert called_args["type"] == 3  # SYSTEM_CASE
    assert called_args["id"] == 100

    widgets = called_args["widgets"]
    assert len(widgets) == 1
    assert widgets[0]["metadata"]["title"] == "Widget One"
    assert widgets[0]["config"]["htmlContent"] == "<h1>Hello from push</h1>"


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_by_display_name_cli(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Setup mock backend API
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api
    mock_api.upload_view.return_value = {"success": True}
    mock_api.list_views.return_value = [{"identifier": "32c1d430-b143-4db8-a507-c96ae91a46c2", "id": 200}]
    mock_api.download_view.return_value = {"widgets": []}

    # Setup source directory structure to build from
    views_root = tmp_path / "views"
    view_folder = views_root / "32c1d430-b143-4db8-a507-c96ae91a46c2"
    view_folder.mkdir(parents=True)

    # Create view.yaml
    view_yaml_data = {
        "identifier": "32c1d430-b143-4db8-a507-c96ae91a46c2",
        "name": "My Custom View",
        "creator": "system",
        "playbook_id": "playbook_1",
        "type": "system_case",
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": [],
    }
    with (view_folder / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(view_yaml_data, f)

    # Invoke mp push view command using display name
    with (
        mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"),
        mock.patch("mp.core.file_utils.create_or_get_views_root_dir", return_value=views_root),
    ):
        result = runner.invoke(
            push_app,
            ["view", "My Custom View"],
        )

    assert result.exit_code == 0
    mock_api.upload_view.assert_called_once()
    called_args = mock_api.upload_view.call_args[0][0]
    assert called_args["identifier"] == "32c1d430-b143-4db8-a507-c96ae91a46c2"
    assert called_args["name"] == "My Custom View"
    assert called_args["id"] == 200


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_blocks_new_widget_by_default(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api
    mock_api.list_views.return_value = [{"identifier": "system_case_default", "id": 100}]
    # download_view returns view that does NOT contain "widget_one_id" (meaning it is a new widget)
    mock_api.download_view.return_value = {"widgets": []}

    src_dir = tmp_path / "views"
    view_folder = src_dir / "system_case_default"
    view_folder.mkdir(parents=True)

    view_yaml_data = {
        "identifier": "system_case_default",
        "name": "Default Case View",
        "creator": "system",
        "playbook_id": "playbook_1",
        "type": "system_case",
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": [{"title": "Widget One", "size": "half_width", "order": 1}],
    }
    with (view_folder / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(view_yaml_data, f)

    widgets_dir = view_folder / "widgets"
    widgets_dir.mkdir()
    widget_yaml_data = {
        "title": "Widget One",
        "description": "HTML Widget",
        "identifier": "widget_one_id",
        "order": 1,
        "template_identifier": "temp_one",
        "type": "html",
        "data_definition": {
            "html_height": 100,
            "safe_rendering": True,
            "widget_definition_scope": "alert",
            "type": "html",
        },
        "widget_size": "half_width",
        "action_widget_template_id": None,
        "step_id": None,
        "step_integration": None,
        "block_step_id": None,
        "block_step_instance_name": None,
        "present_if_empty": False,
        "conditions_group": {"logical_operator": "and", "conditions": []},
        "integration_name": None,
    }
    with (widgets_dir / "Widget One.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(widget_yaml_data, f)
    (widgets_dir / "Widget One.html").write_text("<h1>Hello</h1>", encoding="utf-8")

    with mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"):
        result = runner.invoke(
            push_app,
            ["view", "system_case_default", "--custom", str(src_dir)],
        )

    # Output should exit with code 1 (blocked)
    assert result.exit_code == 1
    mock_api.upload_view.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_allows_new_widget_with_flag(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api
    mock_api.upload_view.return_value = {"success": True}
    mock_api.list_views.return_value = [{"identifier": "system_case_default", "id": 100}]
    mock_api.download_view.return_value = {"widgets": []}

    src_dir = tmp_path / "views"
    view_folder = src_dir / "system_case_default"
    view_folder.mkdir(parents=True)

    view_yaml_data = {
        "identifier": "system_case_default",
        "name": "Default Case View",
        "creator": "system",
        "playbook_id": "playbook_1",
        "type": "system_case",
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": [{"title": "Widget One", "size": "half_width", "order": 1}],
    }
    with (view_folder / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(view_yaml_data, f)

    widgets_dir = view_folder / "widgets"
    widgets_dir.mkdir()
    widget_yaml_data = {
        "title": "Widget One",
        "description": "HTML Widget",
        "identifier": "widget_one_id",
        "order": 1,
        "template_identifier": "temp_one",
        "type": "html",
        "data_definition": {
            "html_height": 100,
            "safe_rendering": True,
            "widget_definition_scope": "alert",
            "type": "html",
        },
        "widget_size": "half_width",
        "action_widget_template_id": None,
        "step_id": None,
        "step_integration": None,
        "block_step_id": None,
        "block_step_instance_name": None,
        "present_if_empty": False,
        "conditions_group": {"logical_operator": "and", "conditions": []},
        "integration_name": None,
    }
    with (widgets_dir / "Widget One.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(widget_yaml_data, f)
    (widgets_dir / "Widget One.html").write_text("<h1>Hello</h1>", encoding="utf-8")

    with mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"):
        result = runner.invoke(
            push_app,
            ["view", "system_case_default", "--custom", str(src_dir), "--allow-create"],
        )

    # Should succeed with the --allow-create flag
    assert result.exit_code == 0
    mock_api.upload_view.assert_called_once()
