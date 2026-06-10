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

from ...jobs import PullContent, PushContent
from ..common import CONFIG_PATH
from ..core.product import GitSyncProduct
from ..core.session import GitSyncMockSession

DEFAULT_PARAMETERS = {
    "Repo URL": "https://github.com/example/repo.git",
    "Branch": "main",
    "Git Password/Token/SSH Key": "secret-token",
    "Siemplify Verify SSL": True,
    "Git Verify SSL": True,
    "Case Tags": True,
    "Custom Lists": True,
    "Commit Author": "Test Author <test@example.com>",
}

@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_pull_tags_and_lists(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    import soar_sdk.SiemplifyJob
    soar_sdk.SiemplifyJob.SiemplifyJob.debug_mode = False
    import git_sync.core.GitSyncManager
    monkeypatch.setattr(git_sync.core.GitSyncManager.GitSyncManager, "__del__", lambda self: None)

    mock_git_tags = [
        {
            "id": 0,
            "name": "projects/unknown/locations/unknown/instances/unknown/caseTagDefinitions/1",
            "displayName": "1P Case Tag",
        },
        {
            "id": 0,
            "tagName": "Legacy Case Tag",
            "color": "#FFFFFF",
        }
    ]

    mock_git_lists = [
        {
            "id": 0,
            "name": "projects/unknown/locations/unknown/instances/unknown/customLists/1",
            "entityIdentifier": "1P Custom List",
            "category": "General",
            "environments": "*",
        },
        {
            "id": 0,
            "name": "Legacy Custom List",
            "category": "General",
            "description": "desc",
            "records": [{"key": "1", "value": "1"}],
        }
    ]

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {"update_root_readme": true}}'
            if path == "Settings/tags.json":
                return json.dumps(mock_git_tags).encode("utf-8")
            if path == "Settings/customLists.json":
                return json.dumps(mock_git_lists).encode("utf-8")
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path):
            return []

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)
    
    # Mock the API responses
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.get_case_tags",
        lambda self: [{"id": 1, "displayName": "1P Case Tag"}]
    )
    
    tag_calls = []
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.add_case_tag",
        lambda self, tag: tag_calls.append(tag) or True
    )

    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.get_custom_lists",
        lambda self: []
    )
    
    list_calls = []
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.update_custom_list",
        lambda self, lst: list_calls.append(lst) or True
    )

    try:
        PullContent.main()
    except SystemExit:
        pass

    assert len(tag_calls) == 2
    # 1P tag should be matched and given ID 1
    assert tag_calls[0]["id"] == 1
    assert tag_calls[0]["displayName"] == "1P Case Tag"
    
    # Legacy tag should not be matched and given ID 0, translated via TIPCommon models dynamically
    assert tag_calls[1]["id"] == 0
    assert tag_calls[1].get("tagName") == "Legacy Case Tag" or tag_calls[1].get("displayName") == "Legacy Case Tag"

    assert len(list_calls) == 2
    assert list_calls[0].get("entityIdentifier") == "1P Custom List" or list_calls[0].get("name") == "1P Custom List"
    assert list_calls[1].get("name") == "Legacy Custom List" or list_calls[1].get("entityIdentifier") == "Legacy Custom List"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_tags_and_lists(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    import soar_sdk.SiemplifyJob
    soar_sdk.SiemplifyJob.SiemplifyJob.debug_mode = False
    import git_sync.core.GitSyncManager
    monkeypatch.setattr(git_sync.core.GitSyncManager.GitSyncManager, "__del__", lambda self: None)

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {"update_root_readme": true}}'
            raise KeyError(f"File not found: {path}")

        def get_raw_object_from_path(self, path):
            raise KeyError(f"Path not found: {path}")

        def get_file_objects_from_path(self, path):
            return []

        def update_objects(self, objects, **kwargs):
            if not hasattr(self, "update_calls"):
                self.update_calls = []
            for obj in objects:
                self.update_calls.append(obj.path)
                if obj.path == "Settings/tags.json":
                    import json
                    self.pushed_tags = json.loads(obj.content)
                if obj.path == "Settings/customLists.json":
                    import json
                    self.pushed_lists = json.loads(obj.content)

        def __getattr__(self, name):
            if name in ["commit_and_push", "cleanup"]:
                return lambda *args, **kwargs: None
            raise AttributeError(name)

    mock_git = MockGit()
    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", lambda *args, **kwargs: mock_git)

    # Return native 1P tags and lists from API
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.get_case_tags",
        lambda self: [{"id": 1, "displayName": "1P Tag"}]
    )
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.get_custom_lists",
        lambda self: [{"name": "projects/x/customLists/1", "entityIdentifier": "1P List"}]
    )

    try:
        PushContent.main()
    except SystemExit:
        pass

    assert "Settings/tags.json" in mock_git.update_calls
    assert "Settings/customLists.json" in mock_git.update_calls

    assert len(mock_git.pushed_tags) == 1
    assert mock_git.pushed_tags[0]["displayName"] == "1P Tag"

    assert len(mock_git.pushed_lists) == 1
    assert mock_git.pushed_lists[0]["entityIdentifier"] == "1P List"
