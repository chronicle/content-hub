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

import pytest
from integration_testing.set_meta import set_metadata

from ...core.definitions import File
from ...jobs import PullPlaybook
from ..common import CONFIG_PATH, MOCKS_PATH
from ..core.product import GitSyncProduct
from ..core.session import GitSyncMockSession

with open(MOCKS_PATH / "mock_data.json", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)

GIT_PLAYBOOK_DATA = MOCK_DATA["git_playbook"]
LOCAL_PLAYBOOK_DATA = MOCK_DATA["local_playbook"]

DEFAULT_PARAMETERS = {
    "Repo URL": "https://github.com/example/repo.git",
    "Branch": "main",
    "Git Password/Token/SSH Key": "secret-token",
    "Siemplify Verify SSL": True,
    "Git Verify SSL": True,
    "Playbook Whitelist": "Test Playbook",
    "Include Playbook Blocks": False,
    "Commit Author": "Test Author <test@example.com>",
}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_pull_playbook_success(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    """Tests PullPlaybook job as a black box. Verifies that when importing (Pulling)
    playbooks with duplicate-named steps, they map to unique local step IDs.
    """
    # Arrange
    git_sync_product.local_playbook = LOCAL_PLAYBOOK_DATA

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {}}'
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path):
            if path == "Playbooks":
                return [
                    File(
                        "Playbooks/Default/Test Playbook.json",
                        json.dumps(GIT_PLAYBOOK_DATA),
                    ),
                ]
            raise KeyError(f"Directory not found: {path}")

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)

    # Act
    PullPlaybook.main()

    # Assert
    saved_playbook = git_sync_product.saved_playbook
    assert saved_playbook is not None

    steps = saved_playbook["steps"]
    step_1 = next(x for x in steps if x["identifier"] == "local_PA4_1")
    step_2 = next(x for x in steps if x["identifier"] == "local_PA4_2")

    # Assert that duplicate steps matched DIFFERENT, UNIQUE local step IDs
    assert step_1["identifier"] != step_2["identifier"]
    assert {step_1["identifier"], step_2["identifier"]} == {
        "local_PA4_1",
        "local_PA4_2",
    }


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_pull_deconstructed_playbook_success(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    """Tests PullPlaybook job with deconstructed YAML structure."""
    # Arrange
    git_sync_product.local_playbook = LOCAL_PLAYBOOK_DATA

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {}}'
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path):
            if path == "Playbooks":
                from ...core.PlaybookYAMLConverter import PlaybookYAMLConverter
                import copy
                test_playbook_data = copy.deepcopy(GIT_PLAYBOOK_DATA)
                test_playbook_data["steps"][0]["identifier"] = "1_git_PA4"
                test_playbook_data["steps"][0]["originalStepIdentifier"] = "1_git_PA4"
                test_playbook_data["steps"][1]["identifier"] = "2_git_PA4"
                test_playbook_data["steps"][1]["originalStepIdentifier"] = "2_git_PA4"

                deconstructed = PlaybookYAMLConverter.deconstruct_playbook(test_playbook_data)
                for f in deconstructed:
                    f.path = f"Playbooks/Default/Test Playbook/{f.path}"
                return deconstructed
            raise KeyError(f"Directory not found: {path}")

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)

    # Act
    PullPlaybook.main()

    # Assert
    saved_playbook = git_sync_product.saved_playbook
    assert saved_playbook is not None

    steps = saved_playbook["steps"]
    step_1 = next(x for x in steps if x["identifier"] == "local_PA4_1")
    step_2 = next(x for x in steps if x["identifier"] == "local_PA4_2")

    assert step_1["identifier"] != step_2["identifier"]
    assert {step_1["identifier"], step_2["identifier"]} == {
        "local_PA4_1",
        "local_PA4_2",
    }
