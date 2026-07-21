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

import pytest  # noqa: TC002
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

    saved_file = tmp_path / "shared" / "Test_Field.yaml"
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

    saved_file = tmp_path / "shared" / "Test_Field.yaml"
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
    field_file.write_text(
        yaml.dump({
            "name": "projects//locations//instances//customFields/1",
            "displayName": "Test Field",
            "type": "String",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["custom-field", "Test Field"])

    assert result.exit_code == 0
    mock_api.update_custom_field.assert_called_once_with(
        1,
        {
            "name": "projects//locations//instances//customFields/1",
            "displayName": "Test Field",
            "type": "String",
            "id": 1,
        },
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
    field_file.write_text(
        yaml.dump({
            "name": "projects//locations//instances//customFields/new",
            "displayName": "New Field",
            "type": "String",
        })
    )

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
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
    ]

    mock_api.download_custom_field.side_effect = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
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

    assert (tmp_path / "alert" / "Test_Field_alert.yaml").exists()
    assert (tmp_path / "case" / "Test_Field_case.yaml").exists()


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
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
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
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/2",
        "id": 2,
        "displayName": "Test Field",
        "scopes": "Case",
        "description": "Updated",
    }

    local_file = tmp_path / "Test_Field_case.yaml"
    local_file.write_text(
        yaml.dump({
            "displayName": "Test Field",
            "scopes": "Case",
            "description": "Old",
        })
    )

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
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
    ]

    file1 = tmp_path / "Test_Field_alert.yaml"
    file1.write_text(
        yaml.dump({
            "displayName": "Test Field",
            "scopes": "Alert",
            "description": "Alert Desc",
        })
    )

    file2 = tmp_path / "Test_Field_case.yaml"
    file2.write_text(
        yaml.dump({
            "displayName": "Test Field",
            "scopes": "Case",
            "description": "Case Desc",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["custom-field", "Test Field"])

    assert result.exit_code == 0
    assert mock_api.update_custom_field.call_count == 2
    mock_api.update_custom_field.assert_any_call(
        1,
        {
            "displayName": "Test Field",
            "scopes": "Alert",
            "description": "Alert Desc",
            "id": 1,
            "name": "projects//locations//instances//customFields/1",
        },
    )
    mock_api.update_custom_field.assert_any_call(
        2,
        {
            "displayName": "Test Field",
            "scopes": "Case",
            "description": "Case Desc",
            "id": 2,
            "name": "projects//locations//instances//customFields/2",
        },
    )


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_list(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
    ]

    with caplog.at_level("INFO"):
        result = runner.invoke(pull_app, ["custom-field", "--list"])

    assert result.exit_code == 0
    assert "DisplayName: 'Test Field' (Scopes: Alert)" in caplog.text


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_by_suffix(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/1",
        "id": 1,
        "displayName": "Test Field",
        "scopes": "Alert",
    }

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "Test_Field_alert"])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(1)
    assert (tmp_path / "alert" / "Test_Field_alert.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_with_scope_option(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/2",
        "id": 2,
        "displayName": "Test Field",
        "scopes": "Case",
    }

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "Test Field", "--scope", "case"])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(2)
    assert (tmp_path / "case" / "Test_Field_case.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.push.get_backend_api")
def test_push_custom_field_with_scope_option(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Test Field",
            "scopes": "Case",
        },
    ]

    file1 = tmp_path / "Test_Field_alert.yaml"
    file1.write_text(
        yaml.dump({
            "displayName": "Test Field",
            "scopes": "Alert",
            "description": "Alert Desc",
        })
    )

    file2 = tmp_path / "Test_Field_case.yaml"
    file2.write_text(
        yaml.dump({
            "displayName": "Test Field",
            "scopes": "Case",
            "description": "Case Desc",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["custom-field", "Test Field", "--scope", "alert"])

    assert result.exit_code == 0
    mock_api.update_custom_field.assert_called_once_with(
        1,
        {
            "displayName": "Test Field",
            "scopes": "Alert",
            "description": "Alert Desc",
            "id": 1,
            "name": "projects//locations//instances//customFields/1",
        },
    )


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_overwrites_matching_renamed_file(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/1",
        "id": 1,
        "displayName": "Test Field",
        "scopes": "Alert",
        "description": "Downloaded Description",
    }

    # Create a local file with a different name but matching displayName and scope
    local_file = tmp_path / "Test_Field_alertss.yaml"
    local_file.write_text(
        yaml.dump({
            "displayName": "Test Field",
            "scopes": "Alert",
            "description": "Old Local Description",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "Test Field"])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(1)

    # Verify that the renamed file was updated instead of generating Test_Field_alert.yaml
    assert local_file.exists()
    with local_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["description"] == "Downloaded Description"

    assert not (tmp_path / "alert" / "Test_Field_alert.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_custom_field_by_local_filename_without_suffix(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Test Field",
            "scopes": "Alert",
        },
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/1",
        "id": 1,
        "displayName": "Test Field",
        "scopes": "Alert",
        "description": "Downloaded Description",
    }

    # Create a local file with a custom name
    local_file = tmp_path / "Test_Field_alertss.yaml"
    local_file.write_text(
        yaml.dump({
            "displayName": "Test Field",
            "scopes": "Alert",
            "description": "Old Local Description",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "Test_Field_alertss"])

    assert result.exit_code == 0
    mock_api.download_custom_field.assert_called_once_with(1)

    # Verify that the custom renamed file was updated
    assert local_file.exists()
    with local_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["description"] == "Downloaded Description"


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_all_custom_fields_with_scope_filtering(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Field 1",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Field 2",
            "scopes": "Case",
        },
        {
            "name": "projects//locations//instances//customFields/3",
            "id": 3,
            "displayName": "Field 3",
            "scopes": ["Alert", "Case"],
        },
    ]

    mock_api.download_custom_field.side_effect = lambda x: {
        "name": f"projects//locations//instances//customFields/{x}",
        "id": x,
        "displayName": f"Field {x}",
        "scopes": "Case" if x == 2 else ["Alert", "Case"],
    }

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "--all", "--scope", "case"])

    assert result.exit_code == 0
    # Field 1 (Alert scope only) should NOT be downloaded
    # Field 2 (Case) and Field 3 (Alert/Case) should be downloaded
    assert mock_api.download_custom_field.call_count == 2
    mock_api.download_custom_field.assert_any_call(2)
    mock_api.download_custom_field.assert_any_call(3)

    assert (tmp_path / "case" / "Field_2_case.yaml").exists()
    assert (tmp_path / "shared" / "Field_3_alert_case.yaml").exists()
    assert not (tmp_path / "alert" / "Field_1_alert.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_all_custom_fields_or_scope_matching(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Field 1",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Field 2",
            "scopes": "Case",
        },
        {
            "name": "projects//locations//instances//customFields/3",
            "id": 3,
            "displayName": "Field 3",
            "scopes": ["Alert", "Case"],
        },
    ]

    mock_api.download_custom_field.side_effect = lambda x: {
        "name": f"projects//locations//instances//customFields/{x}",
        "id": x,
        "displayName": f"Field {x}",
        "scopes": "Alert" if x == 1 else ("Case" if x == 2 else ["Alert", "Case"]),
    }

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "--all", "--scope", "alert,case"])

    assert result.exit_code == 0
    # Field 1, Field 2, Field 3 should all be downloaded (OR condition)
    assert mock_api.download_custom_field.call_count == 3
    mock_api.download_custom_field.assert_any_call(1)
    mock_api.download_custom_field.assert_any_call(2)
    mock_api.download_custom_field.assert_any_call(3)

    assert (tmp_path / "alert" / "Field_1_alert.yaml").exists()
    assert (tmp_path / "case" / "Field_2_case.yaml").exists()
    assert (tmp_path / "shared" / "Field_3_alert_case.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.custom_field.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.custom_field.pull.get_backend_api")
def test_pull_all_custom_fields_shared_scope(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_custom_fields.return_value = [
        {
            "name": "projects//locations//instances//customFields/1",
            "id": 1,
            "displayName": "Field 1",
            "scopes": "Alert",
        },
        {
            "name": "projects//locations//instances//customFields/2",
            "id": 2,
            "displayName": "Field 2",
            "scopes": "Case",
        },
        {
            "name": "projects//locations//instances//customFields/3",
            "id": 3,
            "displayName": "Field 3",
            "scopes": ["Alert", "Case"],
        },
    ]

    mock_api.download_custom_field.return_value = {
        "name": "projects//locations//instances//customFields/3",
        "id": 3,
        "displayName": "Field 3",
        "scopes": ["Alert", "Case"],
    }

    with mock.patch(
        "mp.core.file_utils.create_or_get_custom_fields_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["custom-field", "--all", "--scope", "shared"])

    assert result.exit_code == 0
    # ONLY Field 3 (which has both alert and case scopes) should be downloaded
    assert mock_api.download_custom_field.call_count == 1
    mock_api.download_custom_field.assert_called_once_with(3)

    assert (tmp_path / "shared" / "Field_3_alert_case.yaml").exists()
    assert not (tmp_path / "alert" / "Field_1_alert.yaml").exists()
    assert not (tmp_path / "case" / "Field_2_case.yaml").exists()
