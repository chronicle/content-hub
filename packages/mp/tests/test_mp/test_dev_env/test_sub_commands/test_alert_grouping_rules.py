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
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "displayName": "Rule One"},
    ]

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "Rule One"])

    assert result.exit_code == 0

    saved_file = tmp_path / "Rule_One.yaml"
    assert saved_file.exists()


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
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "displayName": "Rule One"},
    ]

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(pull_app, ["alert-grouping-rule", "--all"])

    assert result.exit_code == 0
    assert (tmp_path / "Rule_One.yaml").exists()


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
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "displayName": "Rule One"},
    ]

    rule_file = tmp_path / "Rule_One.yaml"
    rule_file.write_text(yaml.dump({
        "name": "projects//locations//instances//alertGroupingRules/1",
        "displayName": "Rule One",
    }))

    with mock.patch(
        "mp.core.file_utils.create_or_get_alert_grouping_rules_root_dir",
        return_value=tmp_path,
    ):
        result = runner.invoke(push_app, ["alert-grouping-rule", "Rule One"])

    assert result.exit_code == 0
    mock_api.update_alert_grouping_rule.assert_called_once_with(
        1,
        {"name": "projects//locations//instances//alertGroupingRules/1", "displayName": "Rule One"},
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

    rule_file = tmp_path / "Rule_New.yaml"
    rule_file.write_text(yaml.dump({
        "name": "projects//locations//instances//alertGroupingRules/new",
        "displayName": "Rule New",
    }))

    result = runner.invoke(push_app, ["alert-grouping-rule", str(rule_file)])

    assert result.exit_code == 0
    mock_api.create_alert_grouping_rule.assert_called_once_with(
        {"name": "projects//locations//instances//alertGroupingRules/new", "displayName": "Rule New"},
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
        {"name": "projects//locations//instances//alertGroupingRules/1", "id": 1, "displayName": "Rule One"},
    ]

    custom_dir = tmp_path / "missing" / "dirs"
    custom_path = custom_dir / "rule.yaml"

    result = runner.invoke(pull_app, ["alert-grouping-rule", "Rule One", "--custom", str(custom_path)])

    assert result.exit_code == 0
    assert custom_path.exists()
