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

from pathlib import Path  # ruff:ignore[typing-only-standard-library-import]
from unittest import mock

import pytest  # ruff:ignore[typing-only-third-party-import]
import yaml
from typer.testing import CliRunner

from mp.dev_env.sub_commands.pull import pull_app
from mp.dev_env.sub_commands.push import push_app

runner = CliRunner()


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_alert_grouping_rule(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "category": "All"},
    ]

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "All"])

    assert result.exit_code == 0

    saved_file = tmp_path / "All.yaml"
    assert saved_file.exists()
    with saved_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert "id" not in data
        assert "name" not in data
        assert data["category"] == "All"


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_all_alert_grouping_rules(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "category": "All"},
    ]

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "--all"])

    assert result.exit_code == 0
    saved_file = tmp_path / "All.yaml"
    assert saved_file.exists()
    with saved_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert "id" not in data
        assert "name" not in data


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.get_backend_api")
def test_push_alert_grouping_rule_update(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "category": "All"},
    ]

    rule_file = tmp_path / "All.yaml"
    rule_file.write_text(
        yaml.dump({
            "category": "All",
            "groupingType": "Entities",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["alert-grouping-rule", "All"])

    assert result.exit_code == 0
    mock_api.update_alert_grouping_rule.assert_called_once_with(
        1,
        {
            "category": "All",
            "groupingType": "Entities",
            "id": 1,
            "name": "projects//locations//instances//alertGroupingRules/1",
        },
    )
    mock_api.create_alert_grouping_rule.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.get_backend_api")
def test_push_alert_grouping_rule_create(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = []

    rule_file = tmp_path / "AlertType.yaml"
    rule_file.write_text(
        yaml.dump({
            "category": "AlertType",
            "groupingType": "Entities",
        })
    )

    result = runner.invoke(push_app, ["alert-grouping-rule", str(rule_file), "--force"])

    assert result.exit_code == 0
    mock_api.create_alert_grouping_rule.assert_called_once_with(
        {"category": "AlertType", "groupingType": "Entities"},
    )
    mock_api.update_alert_grouping_rule.assert_not_called()


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_alert_grouping_rule_with_custom_missing_dirs(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "category": "All"},
    ]

    custom_dir = tmp_path / "missing" / "dirs"
    custom_path = custom_dir / "rule.yaml"

    result = runner.invoke(pull_app, ["alert-grouping-rule", "All", "--custom", str(custom_path)])

    assert result.exit_code == 0
    assert custom_path.exists()


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_multiple_rules_same_category(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "name": "projects//locations//instances//alertGroupingRules/1",
            "id": 1,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
        },
        {
            "name": "projects//locations//instances//alertGroupingRules/2",
            "id": 2,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Brute Force", "displayName": "Brute Force"}],
        },
    ]

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "Alert Type"])

    assert result.exit_code == 0

    file_1 = tmp_path / "AlertType_phishing.yaml"
    file_2 = tmp_path / "AlertType_brute_force.yaml"
    assert file_1.exists()
    assert file_2.exists()


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.get_backend_api")
def test_push_multiple_rules_same_category(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "name": "projects//locations//instances//alertGroupingRules/1",
            "id": 1,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
        },
        {
            "name": "projects//locations//instances//alertGroupingRules/2",
            "id": 2,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Brute Force", "displayName": "Brute Force"}],
        },
    ]

    # Create two files
    file_1 = tmp_path / "AlertType_phishing.yaml"
    file_1.write_text(
        yaml.dump({
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["alert-grouping-rule", "AlertType"])

    assert result.exit_code == 0
    mock_api.update_alert_grouping_rule.assert_called_once_with(
        1,
        {
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
            "id": 1,
            "name": "projects//locations//instances//alertGroupingRules/1",
        },
    )


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_alert_grouping_rule_list(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "id": 1,
            "category": "ProductName",
            "categoryDetails": [{"identifier": "Cortex XDR", "displayName": "Cortex XDR"}],
        },
    ]

    with caplog.at_level("INFO"):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "--list"])

    assert result.exit_code == 0
    assert "Category: 'ProductName' (Subcategories: Cortex XDR)" in caplog.text


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_alert_grouping_rule_by_exact_filename(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "name": "projects//locations//instances//alertGroupingRules/1",
            "id": 1,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
        },
        {
            "name": "projects//locations//instances//alertGroupingRules/2",
            "id": 2,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Brute Force", "displayName": "Brute Force"}],
        },
    ]

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "AlertType_phishing"])

    assert result.exit_code == 0
    saved_file = tmp_path / "AlertType_phishing.yaml"
    assert saved_file.exists()
    assert not (tmp_path / "AlertType_brute_force.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.get_backend_api")
def test_push_alert_grouping_rule_by_exact_filename(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "name": "projects//locations//instances//alertGroupingRules/1",
            "id": 1,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
        },
        {
            "name": "projects//locations//instances//alertGroupingRules/2",
            "id": 2,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Brute Force", "displayName": "Brute Force"}],
        },
    ]

    # Create two files
    file_1 = tmp_path / "AlertType_phishing.yaml"
    file_1.write_text(
        yaml.dump({
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
        })
    )

    file_2 = tmp_path / "AlertType_brute_force.yaml"
    file_2.write_text(
        yaml.dump({
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Brute Force", "displayName": "Brute Force"}],
            "groupingType": "Entities",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["alert-grouping-rule", "AlertType_phishing"])

    assert result.exit_code == 0
    mock_api.update_alert_grouping_rule.assert_called_once_with(
        1,
        {
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
            "id": 1,
            "name": "projects//locations//instances//alertGroupingRules/1",
        },
    )


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_alert_grouping_rule_overwrites_matching_renamed_file(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "name": "projects//locations//instances//alertGroupingRules/1",
            "id": 1,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
        },
    ]

    # Create a local file with a custom name but matching category and details
    local_file = tmp_path / "AlertType_phishing_custom.yaml"
    local_file.write_text(
        yaml.dump({
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
            "description": "Old Local Description",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "AlertType_phishing"])

    assert result.exit_code == 0

    # Verify that the renamed file was updated instead of generating AlertType_phishing.yaml
    assert local_file.exists()
    with local_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["groupingType"] == "Entities"
        assert "id" not in data

    assert not (tmp_path / "AlertType_phishing.yaml").exists()


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.pull.get_backend_api")
def test_pull_alert_grouping_rule_by_local_filename_without_suffix(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "name": "projects//locations//instances//alertGroupingRules/1",
            "id": 1,
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
        },
    ]

    # Create a local file with a custom name
    local_file = tmp_path / "AlertType_phishing_custom.yaml"
    local_file.write_text(
        yaml.dump({
            "category": "AlertType",
            "categoryDetails": [{"identifier": "Phishing", "displayName": "Phishing"}],
            "groupingType": "Entities",
            "description": "Old Local Description",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "AlertType_phishing_custom"])

    assert result.exit_code == 0

    # Verify that the custom renamed file was updated
    assert local_file.exists()
    with local_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["groupingType"] == "Entities"
        assert "id" not in data


@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.load_dev_env_config")
@mock.patch("mp.dev_env.sub_commands.alert_grouping_rule.push.get_backend_api")
def test_push_alert_grouping_rule_modified_category_details(
    mock_get_backend_api: mock.MagicMock,
    mock_load_config: mock.MagicMock,
    tmp_path: Path,
) -> None:
    mock_api = mock.MagicMock()
    mock_get_backend_api.return_value = mock_api

    mock_api.list_alert_grouping_rules.return_value = [
        {
            "name": "projects//locations//instances//alertGroupingRules/10",
            "id": 10,
            "category": "DataSource",
            "categoryDetails": [{"identifier": "jira", "displayName": "jira"}],
            "groupingType": "Entities",
        },
    ]

    rule_file = tmp_path / "DataSource_jira.yaml"
    rule_file.write_text(
        yaml.dump({
            "category": "DataSource",
            "categoryDetails": [
                {"identifier": "jira", "displayName": "jira"},
                {"identifier": "microsoft_casb", "displayName": "microsoft_casb"},
            ],
            "groupingType": "Entities",
        })
    )

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["alert-grouping-rule", str(rule_file)])

    assert result.exit_code == 0
    mock_api.update_alert_grouping_rule.assert_called_once_with(
        10,
        {
            "category": "DataSource",
            "categoryDetails": [
                {"identifier": "jira", "displayName": "jira"},
                {"identifier": "microsoft_casb", "displayName": "microsoft_casb"},
            ],
            "groupingType": "Entities",
            "id": 10,
            "name": "projects//locations//instances//alertGroupingRules/10",
        },
    )
    mock_api.create_alert_grouping_rule.assert_not_called()
