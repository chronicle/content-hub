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
from ...jobs import PullContent, PushContent
from ..common import CONFIG_PATH, MOCKS_PATH
from ..core.product import GitSyncProduct
from ..core.session import GitSyncMockSession

DEFAULT_PARAMETERS = {
    "Repo URL": "https://github.com/example/repo.git",
    "Branch": "main",
    "Git Password/Token/SSH Key": "secret-token",
    "Siemplify Verify SSL": True,
    "Git Verify SSL": True,
    "Environments": True,
    "Commit Author": "Test Author <test@example.com>",
}

@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_pull_content_environments(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    import soar_sdk.SiemplifyJob
    soar_sdk.SiemplifyJob.SiemplifyJob.debug_mode = False
    import git_sync.core.GitSyncManager
    monkeypatch.setattr(git_sync.core.GitSyncManager.GitSyncManager, "__del__", lambda self: None)

    mock_git_environments = [
        {
            "id": 0,
            "name": "projects/unknown/locations/unknown/instances/unknown/environments/1",
            "displayName": "Default Environment",
            "system": True,
        },
        {
            "id": 0,
            "name": "New Legacy Environment",
            "isSystem": False,
        }
    ]

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {"update_root_readme": true}}'
            if path == "Settings/environments.json":
                return json.dumps(mock_git_environments).encode("utf-8")
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path):
            return []

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)
    
    # Mock the API responses
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.get_environment_names",
        lambda self: ["Default Environment"]
    )
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.get_environments",
        lambda self: [{"id": 1, "name": "Default Environment"}]
    )
    
    import_calls = []
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.import_environment",
        lambda self, env: import_calls.append(env) or True
    )

    try:
        PullContent.main()
    except SystemExit:
        pass

    assert len(import_calls) == 2
    
    # First call: Default Environment (Update)
    call_1_args = import_calls[0]
    assert call_1_args["id"] == 1
    assert call_1_args["displayName"] == "Default Environment"

    # Second call: New Legacy Environment (Add)
    call_2_args = import_calls[1]
    assert call_2_args["id"] == 0
    assert call_2_args["name"] == "New Legacy Environment"

@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_content_environments(
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
                if obj.path == "Settings/environments.json":
                    import json
                    self.pushed_envs = json.loads(obj.content)

        def __getattr__(self, name):
            if name in ("update_calls", "pushed_envs"):
                raise AttributeError(name)
            def mock_func(*args, **kwargs):
                pass
            return mock_func

        def cleanup(self):
            pass
            
    mock_git = MockGit()
    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", lambda *args, **kwargs: mock_git)
    
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.SiemplifyApiClient.get_environments",
        lambda self: [{"id": 1, "name": "Default Environment"}]
    )

    try:
        PushContent.main()
    except SystemExit:
        pass

    assert hasattr(mock_git, "update_calls"), f"update_file never called. calls: {getattr(mock_git, 'update_calls', 'none')}"
    assert hasattr(mock_git, "pushed_envs"), f"pushed_envs not set. update_calls: {mock_git.update_calls}"
    assert len(mock_git.pushed_envs) == 1
    assert mock_git.pushed_envs[0]["id"] == 0
    assert mock_git.pushed_envs[0]["name"] == "Default Environment"
