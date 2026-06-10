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
    "Environments": False,
    "Case Stages": True,
    "Case Title Settings": True,
    "Case Close Reasons": True,
    "Commit Author": "Test Author <test@example.com>",
}

@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_pull_content_stages_and_titles(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    import soar_sdk.SiemplifyJob
    soar_sdk.SiemplifyJob.SiemplifyJob.debug_mode = False
    import git_sync.core.GitSyncManager
    monkeypatch.setattr(git_sync.core.GitSyncManager.GitSyncManager, "__del__", lambda self: None)

    mock_git_case_titles = [
        {"value": "[Alert.Product]", "order": 1},
        {"value": "[Alert.RuleGenerator]", "order": 2}
    ]

    mock_git_case_stages = [
        {"id": 1, "displayName": "Triage", "order": 1},
        {"id": 2, "displayName": "Research", "order": 2}
    ]

    mock_git_close_reasons = [
        {"id": 1, "rootCause": "External attack", "closeReason": "Malicious"},
        {"id": 2, "rootCause": "Human error", "closeReason": "NotMalicious"}
    ]

    def mock_get_file_or_default(self_obj, file_path, default):
        if "caseTitles.json" in file_path:
            return json.dumps(mock_git_case_titles)
        if "caseStages.json" in file_path:
            return json.dumps(mock_git_case_stages)
        if "closeReasons.json" in file_path:
            return json.dumps(mock_git_close_reasons)
        return default

    import git_sync.core.GitContentManager
    monkeypatch.setattr(git_sync.core.GitContentManager.GitContentManager, "_get_file_or_default", mock_get_file_or_default)

    pull_job = PullContent.PullContent()
    
    script_session.enable_1p_platform()

    pull_job.execute()

    # Verify requests
    assert any(
        req.url.endswith("moduleSettings/CaseTitleSettings/properties/1")
        and req.json.get("value") == "[Alert.Product]"
        for req in script_session.request_history
    )
    
    assert any(
        req.url.endswith("system/settings/caseStageDefinitions")
        and req.json.get("displayName") == "Triage"
        for req in script_session.request_history
    )

    assert any(
        req.url.endswith("system/settings/caseCloseDefinitions")
        and req.json.get("rootCause") == "External attack"
        for req in script_session.request_history
    )


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_content_stages_and_titles(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GitSyncMockSession,
    git_sync_product: GitSyncProduct,
) -> None:
    import soar_sdk.SiemplifyJob
    soar_sdk.SiemplifyJob.SiemplifyJob.debug_mode = False
    import git_sync.core.GitSyncManager
    monkeypatch.setattr(git_sync.core.GitSyncManager.GitSyncManager, "__del__", lambda self: None)

    push_job = PushContent.PushContent()
    
    script_session.enable_1p_platform()

    mock_pushed_files = {}

    def mock_push_file(self_obj, file_path, data):
        mock_pushed_files[file_path] = data

    import git_sync.core.GitContentManager
    monkeypatch.setattr(git_sync.core.GitContentManager.GitContentManager, "_push_file", mock_push_file)

    script_session.add_mock_response(
        url="system/settings/caseStageDefinitions?pageSize=100",
        method="GET",
        json_response={"caseStageDefinitions": [{"id": 1, "displayName": "1P Stage", "order": 1}]}
    )

    script_session.add_mock_response(
        url="system/settings/caseCloseDefinitions?pageSize=100",
        method="GET",
        json_response={"caseCloseDefinitions": [{"id": 1, "rootCause": "1P Attack", "closeReason": "Malicious"}]}
    )

    script_session.add_mock_response(
        url="moduleSettings/CaseTitleSettings/properties/",
        method="GET",
        json_response={"properties": [{"displayName": "1", "value": "[1P.Field]"}]}
    )

    push_job.execute()

    assert any("caseTitles.json" in fp for fp in mock_pushed_files)
    titles_data = mock_pushed_files[[fp for fp in mock_pushed_files if "caseTitles.json" in fp][0]]
    assert any(t.get("value") == "[1P.Field]" and t.get("order") == 1 for t in titles_data)

    assert any("caseStages.json" in fp for fp in mock_pushed_files)
    stages_data = mock_pushed_files[[fp for fp in mock_pushed_files if "caseStages.json" in fp][0]]
    assert any(s.get("displayName") == "1P Stage" for s in stages_data)

    assert any("closeReasons.json" in fp for fp in mock_pushed_files)
    reasons_data = mock_pushed_files[[fp for fp in mock_pushed_files if "closeReasons.json" in fp][0]]
    assert any(r.get("rootCause") == "1P Attack" for r in reasons_data)
