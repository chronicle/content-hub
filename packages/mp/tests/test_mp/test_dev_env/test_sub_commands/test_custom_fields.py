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


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field"},
        {"name": "projects//locations//instances//customFields/2", "id": 2, "displayName": "Other Field"},
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/1",
        "id": 1,
        "displayName": "Test Field",
        "type": "String",
    }

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "Test Field"])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(1)

    saved_file = tmp_path / "Test_Field.yaml"
    assert saved_file.exists()

    with saved_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["displayName"] == "Test Field"
        assert "id" not in data
        assert "name" not in data


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_all_custom_fields(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field"},
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/1",
        "id": 1,
        "displayName": "Test Field",
        "type": "String",
    }

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "--all"])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(1)
    
    saved_file = tmp_path / "Test_Field.yaml"
    assert saved_file.exists()
    with saved_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert "id" not in data
        assert "name" not in data


@mock.patch("mp.dev_env.sub_commands.custom_field.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.push.get_backend_api")
def test_push_custom_field_update(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field"},
    ]

    field_file = tmp_path / "Test_Field.yaml"
    field_file.write_text(yaml.dump({
        "name": "projects//locations//instances//customFields/1",
        "displayName": "Test Field",
        "type": "String",
    }))

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["custom-field", "Test Field"])

    assert result.exit_code == 0
    mock_api.update_custom_field.assert_called_once_with(
        1,
        {"name": "projects//locations//instances//customFields/1", "displayName": "Test Field", "type": "String", "id": 1},
    )
    mock_api.create_custom_field.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.custom_field.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.push.get_backend_api")
def test_push_custom_field_create(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = []

    field_file = tmp_path / "New_Field.yaml"
    field_file.write_text(yaml.dump({
        "name": "projects//locations//instances//customFields/new",
        "displayName": "New Field",
        "type": "String",
    }))

    result = runner.invoke(push_app, ["custom-field", str(field_file), "--force"])

    assert result.exit_code == 0
    mock_api.create_custom_field.assert_called_once_with(
        {"name": "projects//locations//instances//customFields/new", "displayName": "New Field", "type": "String"},
    )
    mock_api.update_custom_field.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_with_custom_missing_dirs(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field"},
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/1",
        "id": 1,
        "displayName": "Test Field",
        "type": "String",
    }

    custom_dir = tmp_path / "missing" / "dirs"
    custom_path = custom_dir / "field.yaml"

    result = runner.invoke(pull_app, ["custom-field", "Test Field", "--custom", str(custom_path)])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(1)
    assert custom_path.exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_multiple_matches(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field", "scopes": "Alert"},
        {"name": "projects//locations//instances//customFields/2", "id": 2, "displayName": "Test Field", "scopes": "Case"},
    ]

    mock_api.download_custom_field.side_effect = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field", "scopes": "Alert"},
        {"name": "projects//locations//instances//customFields/2", "id": 2, "displayName": "Test Field", "scopes": "Case"},
    ]

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "Test Field"])

    assert result.exit_code == 0
    assert mock_api.download_custom_field.call_count == 2
    mock_api.download_custom_field.assert_any_call(1)
    mock_api.download_custom_field.assert_any_call(2)

    assert (tmp_path / "Test_Field_alert.yaml").exists()
    assert (tmp_path / "Test_Field_case.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_multiple_matches_error_if_destination(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field", "scopes": "Alert"},
        {"name": "projects//locations//instances//customFields/2", "id": 2, "displayName": "Test Field", "scopes": "Case"},
    ]

    custom_path = tmp_path / "out.yaml"

    result = runner.invoke(pull_app, ["custom-field", "Test Field", "--custom", str(custom_path)])

    assert result.exit_code == 1
    mock_api.download_custom_field.assert_not_called()
    assert not custom_path.exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_path_based(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field", "scopes": "Alert"},
        {"name": "projects//locations//instances//customFields/2", "id": 2, "displayName": "Test Field", "scopes": "Case"},
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/2",
        "id": 2,
        "displayName": "Test Field",
        "scopes": "Case",
        "description": "Updated",
    }

    local_file = tmp_path / "Test_Field_case.yaml"
    local_file.write_text(yaml.dump({
        "displayName": "Test Field",
        "scopes": "Case",
        "description": "Old",
    }))

    result = runner.invoke(pull_app, ["custom-field", str(local_file)])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(2)
    
    with local_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["description"] == "Updated"


@mock.patch("mp.dev_env.sub_commands.custom_field.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.push.get_backend_api")
def test_push_custom_field_multiple_matching_files(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {"name": "projects//locations//instances//customFields/1", "id": 1, "displayName": "Test Field", "scopes": "Alert"},
        {"name": "projects//locations//instances//customFields/2", "id": 2, "displayName": "Test Field", "scopes": "Case"},
    ]

    file1 = tmp_path / "Test_Field_alert.yaml"
    file1.write_text(yaml.dump({
        "displayName": "Test Field",
        "scopes": "Alert",
        "description": "Alert Desc",
    }))

    file2 = tmp_path / "Test_Field_case.yaml"
    file2.write_text(yaml.dump({
        "displayName": "Test Field",
        "scopes": "Case",
        "description": "Case Desc",
    }))

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["custom-field", "Test Field"])

    assert result.exit_code == 0
    assert mock_api.update_custom_field.call_count == 2
    mock_api.update_custom_field.assert_any_call(
        1, {"displayName": "Test Field", "scopes": "Alert", "description": "Alert Desc", "id": 1, "name": "projects//locations//instances//customFields/1"}
    )
    mock_api.update_custom_field.assert_any_call(
        2, {"displayName": "Test Field", "scopes": "Case", "description": "Case Desc", "id": 2, "name": "projects//locations//instances//customFields/2"}
    )
