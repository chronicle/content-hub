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

import pytest
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


@mock.patch("mp.dev_env.sub_commands.view.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.pull.get_backend_api")
def test_pull_view_matches_local_folder(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Setup mock backend API
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_views.return_value = [
        {"Identifier": "system_case_default", "Name": "Default Case View"}
    ]

    mock_api.download_view.return_value = {
        "identifier": "system_case_default",
        "name": "Default Case View",
        "creator": "system",
        "playbookIdentifier": "playbook_1",
        "type": 3,
        "widgets": [],
        "roles": [],
    }

    # Pre-create local view folder with a custom name but matching view name
    custom_folder = tmp_path / "my_custom_folder_name"
    custom_folder.mkdir()
    (custom_folder / "view.yaml").write_text(yaml.dump({
        "identifier": "old_identifier",
        "name": "Default Case View",
        "type": "system_case",
        "creator": "system",
        "widgets_details": []
    }), encoding="utf-8")

    with mock.patch("mp.core.file_utils.create_or_get_views_root_dir", return_value=tmp_path):
        result = runner.invoke(pull_app, ["view", "Default Case View"])

    assert result.exit_code == 0
    # Overwrote local folder in-place
    assert (custom_folder / "view.yaml").exists()
    with (custom_folder / "view.yaml").open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["identifier"] == "system_case_default"

    # No duplicate folder was created
    assert not (tmp_path / "system_case_default").exists()


@mock.patch("mp.dev_env.sub_commands.view.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.pull.get_backend_api")
def test_pull_view_all(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_views.return_value = [
        {"identifier": "view_id_1", "name": "View One"},
        {"identifier": "view_id_2", "name": "View Two"},
    ]

    mock_api.download_view.side_effect = [
        {"identifier": "view_id_1", "name": "View One", "type": 3, "widgets": [], "roles": []},
        {"identifier": "view_id_2", "name": "View Two", "type": 3, "widgets": [], "roles": []},
    ]

    with mock.patch("mp.core.file_utils.create_or_get_views_root_dir", return_value=tmp_path):
        result = runner.invoke(pull_app, ["view", "--all"])

    assert result.exit_code == 0
    assert mock_api.download_view.call_count == 2
    mock_api.download_view.assert_any_call("view_id_1")
    mock_api.download_view.assert_any_call("view_id_2")

    assert (tmp_path / "view_id_1" / "view.yaml").exists()
    assert (tmp_path / "view_id_2" / "view.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_all(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api
    mock_api.upload_view.return_value = {"success": True}
    mock_api.list_views.return_value = [
        {"identifier": "view_id_1", "id": 1},
        {"identifier": "view_id_2", "id": 2},
    ]
    mock_api.download_view.side_effect = [
        {"identifier": "view_id_1", "name": "View One", "type": 3, "widgets": []},
        {"identifier": "view_id_2", "name": "View Two", "type": 3, "widgets": []},
        # For the post-push download_and_deconstruct_view calls:
        {"identifier": "view_id_1", "name": "View One", "type": 3, "widgets": [], "roles": []},
        {"identifier": "view_id_2", "name": "View Two", "type": 3, "widgets": [], "roles": []},
    ]

    # Create dummy local view directories
    view_1_dir = tmp_path / "view_id_1"
    view_1_dir.mkdir()
    (view_1_dir / "view.yaml").write_text(yaml.dump({
        "identifier": "view_id_1",
        "name": "View One",
        "type": "system_case",
        "creator": "system",
        "playbook_id": "playbook_1",
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": []
    }), encoding="utf-8")

    view_2_dir = tmp_path / "view_id_2"
    view_2_dir.mkdir()
    (view_2_dir / "view.yaml").write_text(yaml.dump({
        "identifier": "view_id_2",
        "name": "View Two",
        "type": "system_case",
        "creator": "system",
        "playbook_id": "playbook_1",
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": []
    }), encoding="utf-8")

    with mock.patch("mp.core.file_utils.create_or_get_views_root_dir", return_value=tmp_path):
        result = runner.invoke(push_app, ["view", "--all"])

    assert result.exit_code == 0
    assert mock_api.upload_view.call_count == 2


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

    download_mock_response = {
        "identifier": "system_case_default",
        "name": "Default Case View - Server Updated Name",
        "creator": "system",
        "playbookIdentifier": "playbook_1",
        "type": 3,  # SYSTEM_CASE
        "alertRuleType": None,
        "widgets": [
            {
                "metadata": {
                    "title": "Widget One",
                    "description": "HTML Widget",
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
                    "htmlContent": "<h1>Hello from server</h1>",
                },
            }
        ],
        "roles": [1, 2],
        "roleNames": ["Tier 1", "Tier 2"],
    }
    mock_api.download_view.return_value = download_mock_response

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

    # Verify download_view was only called once during widget verification
    assert mock_api.download_view.call_count == 1
    assert (view_folder / "view.yaml").exists()


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
            ["view", "system_case_default", "--custom", str(src_dir), "--force"],
        )

    # Should succeed with the --force flag
    assert result.exit_code == 0
    mock_api.upload_view.assert_called_once()


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_fallback_to_name_and_type_matching(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Setup mock backend API
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api
    mock_api.upload_view.return_value = {"success": True}

    # Mock list_views:
    # Local has identifier: "local_uuid"
    # Server has identifier: "server_uuid" for Name: "Default Case View" and Type: 3 (SYSTEM_CASE)
    mock_api.list_views.return_value = [
        {"identifier": "server_uuid", "name": "Default Case View", "type": 3, "id": 100}
    ]
    # download_view should be called with the resolved server UUID
    mock_api.download_view.return_value = {"widgets": []}

    # Setup source directory structure to build from
    src_dir = tmp_path / "views"
    view_folder = src_dir / "local_uuid"
    view_folder.mkdir(parents=True)

    # Create view.yaml
    view_yaml_data = {
        "identifier": "local_uuid",
        "name": "Default Case View",
        "creator": "system",
        "playbook_id": "playbook_1",
        "type": "system_case",  # maps to 3
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": [],
    }
    with (view_folder / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(view_yaml_data, f)

    # Invoke mp push view command
    with mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"):
        result = runner.invoke(
            push_app,
            ["view", "local_uuid", "--custom", str(src_dir)],
        )

    assert result.exit_code == 0

    # Verify upload_view was called with the server ID, and UUID was aligned to the server UUID
    mock_api.upload_view.assert_called_once()
    called_args = mock_api.upload_view.call_args[0][0]

    assert called_args["identifier"] == "server_uuid"  # UUID aligned to server UUID
    assert called_args["id"] == 100                 # Server ID is injected
    assert called_args["type"] == 3

    # Verify download_view was only called once during widget verification
    assert mock_api.download_view.call_count == 1
    mock_api.download_view.assert_called_once_with("server_uuid")

    # Verify local folder was not renamed
    assert (src_dir / "local_uuid").exists()
    assert not (src_dir / "server_uuid").exists()


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_validate_only(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Setup mock backend API
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    # Setup source directory structure to build from
    src_dir = tmp_path / "views"
    view_folder = src_dir / "test_uuid"
    view_folder.mkdir(parents=True)

    # Create view.yaml
    view_yaml_data = {
        "identifier": "test_uuid",
        "name": "Test View",
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

    # Invoke mp push view command with --validate
    with mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"):
        result = runner.invoke(
            push_app,
            ["view", "test_uuid", "--custom", str(src_dir), "--validate"],
        )

    assert result.exit_code == 0
    # Verify that upload_view was NOT called
    mock_api.upload_view.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_missing_widget_fails(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    # Setup mock backend API
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    # Setup source directory structure to build from
    src_dir = tmp_path / "views"
    view_folder = src_dir / "test_uuid"
    view_folder.mkdir(parents=True)

    # Create view.yaml declaring a widget that doesn't exist
    view_yaml_data = {
        "identifier": "test_uuid",
        "name": "Test View",
        "creator": "system",
        "playbook_id": "playbook_1",
        "type": "system_case",
        "alert_rule_type": None,
        "roles": [1, 2],
        "role_names": ["Tier 1", "Tier 2"],
        "widgets_details": [
            {
                "title": "Missing Widget",
                "order": 1,
                "size": "MEDIUM",
            }
        ],
    }
    with (view_folder / "view.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(view_yaml_data, f)

    # Invoke mp push view command
    with mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"):
        result = runner.invoke(
            push_app,
            ["view", "test_uuid", "--custom", str(src_dir)],
        )

    # Should fail due to missing widget validation error
    assert result.exit_code != 0
    mock_api.upload_view.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.view.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.push.get_backend_api")
def test_push_view_missing_integration_fails(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api
    mock_api.list_views.return_value = [{"identifier": "test_uuid", "id": 100}]
    mock_api.download_view.return_value = {
        "widgets": [
            {
                "metadata": {
                    "title": "Widget One",
                    "identifier": "widget_one_id",
                }
            }
        ]
    }
    mock_api.list_installed_integrations.return_value = [
        {"identifier": "OtherIntegration", "displayName": "Other Integration"}
    ]

    src_dir = tmp_path / "views"
    view_folder = src_dir / "test_uuid"
    view_folder.mkdir(parents=True)

    view_yaml_data = {
        "identifier": "test_uuid",
        "name": "Test View",
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
        "integration_name": "MissingIntegration",
    }
    with (widgets_dir / "Widget One.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(widget_yaml_data, f)

    with mock.patch("mp.core.file_utils.get_view_out_dir", return_value=tmp_path / "out"):
        result = runner.invoke(
            push_app,
            ["view", "test_uuid", "--custom", str(src_dir)],
        )

    assert result.exit_code != 0
    mock_api.upload_view.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.view.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.view.pull.get_backend_api")
def test_pull_view_list(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_views.return_value = [
        {"name": "Default Case View", "identifier": "uuid-1234", "type": 3},
    ]

    with caplog.at_level("INFO"):
        result = runner.invoke(pull_app, ["view", "--list"])

    assert result.exit_code == 0
    assert "Name: 'Default Case View' (Identifier: uuid-1234, Type: 3)" in caplog.text
