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

import pytest
from integration_testing.requests.response import MockResponse
from integration_testing.set_meta import set_metadata

from ...jobs import PushPlaybook
from ..common import CONFIG_PATH
from ..core.product import GitSyncProduct
from ..core.session import GitSyncMockSession

DEFAULT_PARAMETERS = {
    "Repo URL": "https://github.com/example/repo.git",
    "Branch": "main",
    "Git Password/Token/SSH Key": "secret-token",
    "Siemplify Verify SSL": True,
    "Git Verify SSL": True,
    "Folders Whitelist": "Default",
    "Include Playbook Blocks": False,
    "Commit": "Pushing playbooks",
    "Commit Author": "Test Author <test@example.com>",
}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_playbook_excludes_blocks_when_include_blocks_false(
    monkeypatch: pytest.MonkeyPatch,
    sdk_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    """Verifies that PushPlaybook skips playbook blocks when 'Include Playbook Blocks' is False."""
    # Arrange
    standard_playbook_menu = {
        "identifier": "standard-playbook-uuid",
        "name": "Standard Playbook",
        "playbookType": 0,
        "categoryName": "Default",
    }
    standard_playbook_data = {
        "id": 101,
        "identifier": "standard-playbook-uuid",
        "name": "Standard Playbook",
        "playbookType": 0,
        "categoryName": "Default",
        "categoryId": 10,
        "modificationTimeUnixTimeInMs": 2000,
        "trigger": {
            "id": 99,
            "identifier": "trigger-uuid"
        },
        "steps": [],
        "stepsRelations": []
    }

    block_playbook_menu = {
        "identifier": "block-playbook-uuid",
        "name": "Block Playbook",
        "playbookType": 1,
        "categoryName": "Default",
    }
    block_playbook_data = {
        "id": 102,
        "identifier": "block-playbook-uuid",
        "name": "Block Playbook",
        "playbookType": 1,
        "categoryName": "Default",
        "categoryId": 10,
        "modificationTimeUnixTimeInMs": 2000,
        "trigger": {
            "id": 99,
            "identifier": "trigger-uuid"
        },
        "steps": [],
        "stepsRelations": []
    }

    # Monkeypatch the mock session endpoints directly for this test case
    def mock_get_playbooks(*args, **kwargs):
        return MockResponse(
            content=[standard_playbook_menu, block_playbook_menu],
            status_code=200,
        )

    def mock_get_playbook(request):
        identifier = request.real_url.split("/")[-1]
        playbook_data = {
            "standard-playbook-uuid": standard_playbook_data,
            "block-playbook-uuid": block_playbook_data,
        }.get(identifier)
        return MockResponse(content=playbook_data, status_code=200)

    # Re-route the active SDK session instance directly
    for route_pattern in list(sdk_session.routes["POST"].keys()):
        if "GetWorkflowMenuCards" in route_pattern:
            sdk_session.routes["POST"][route_pattern] = mock_get_playbooks

    for route_pattern in list(sdk_session.routes["GET"].keys()):
        if "GetWorkflowFullInfo" in route_pattern:
            sdk_session.routes["GET"][route_pattern] = mock_get_playbook

    updated_files = []

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {"update_root_readme": false}}'
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path):
            return []

        def update_objects(self, files, base_path=""):
            for f in files:
                updated_files.append((f, base_path))

        def commit_and_push(self, message):
            pass

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)

    # Act
    PushPlaybook.main()

    # Assert
    pushed_paths = [f.path for f, _ in updated_files]

    # Standard playbook should be pushed
    assert "Standard Playbook.json" in pushed_paths

    # Block playbook should NOT be pushed (since include_blocks=False)
    assert "Block Playbook.json" not in pushed_paths
