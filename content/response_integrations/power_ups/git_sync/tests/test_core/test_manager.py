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
from unittest.mock import MagicMock

from TIPCommon.types import ChronicleSOAR

from ...core.definitions import Workflow
from ...core.GitSyncManager import WorkflowInstaller
from ..common import MOCKS_PATH
from ..core.product import GitSyncProduct

with open(MOCKS_PATH / "mock_data.json", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)

GIT_PLAYBOOK_DATA = MOCK_DATA["git_playbook"]
LOCAL_PLAYBOOK_DATA = MOCK_DATA["local_playbook"]


def test_duplicate_step_names_matching_prevention() -> None:
    """Tests that if there are multiple steps with the exact same instance name (e.g., multiple
    containers named 'Parallel Actions 4'), they are matched to different, unique local steps
    rather than mapping to the same step, preventing structural collapse.
    """
    # Arrange
    git_workflow = Workflow(GIT_PLAYBOOK_DATA)

    git_sync_product = GitSyncProduct()
    git_sync_product.local_playbook = LOCAL_PLAYBOOK_DATA

    mock_cache = MagicMock()
    mock_cache.get.return_value = -1

    chronicle_soar = MagicMock(spec=ChronicleSOAR)
    installer = WorkflowInstaller(
        chronicle_soar=chronicle_soar,
        api=git_sync_product,
        logger=MagicMock(),
        mod_time_cache=mock_cache,
    )

    # Act
    installer.update_local_workflow(git_workflow)

    # Assert
    assert git_sync_product.saved_playbook is not None
    steps = git_sync_product.saved_playbook["steps"]
    step_1 = next(x for x in steps if x["identifier"] == "local_PA4_1")
    step_2 = next(x for x in steps if x["identifier"] == "local_PA4_2")

    # Assert that each step matched a DIFFERENT, UNIQUE local step ID using pytest asserts
    assert step_1["identifier"] != step_2["identifier"]
    assert {step_1["identifier"], step_2["identifier"]} == {
        "local_PA4_1",
        "local_PA4_2",
    }


def test_push_block_writes_to_playbooks_path() -> None:
    """Test that GitContentManager.push_block writes to Playbooks/ path."""
    from ...core.GitContentManager import PLAYBOOKS_PATH, GitContentManager

    mock_git = MagicMock()
    mock_git.get_file_contents_from_path.return_value = "{}"
    mock_api = MagicMock()
    content_mgr = GitContentManager(mock_git, mock_api)

    block_data = {
        "name": "TestBlock",
        "categoryName": "CustomCat",
        "playbookType": 1,
    }
    block = Workflow(block_data)

    content_mgr.push_block(block)

    mock_git.update_objects.assert_called_once()
    call_args, call_kwargs = mock_git.update_objects.call_args
    assert call_kwargs.get("base_path") == f"{PLAYBOOKS_PATH}/CustomCat/TestBlock"


def test_get_mapping_rule_single_argument() -> None:
    """Test get_mapping_rule extracts mappingRule dict from single argument."""
    from ...core.definitions import get_mapping_rule

    assert get_mapping_rule({"mappingRule": {"source": "TestSrc"}}) == {
        "source": "TestSrc"
    }
    assert get_mapping_rule({"source": "DirectSrc"}) == {"source": "DirectSrc"}


def test_metadata_readme_addons_isolation() -> None:
    """Test that Metadata instances do not share mutable nested dicts."""
    from ...core.definitions import Metadata

    m1 = Metadata()
    m2 = Metadata()

    m1.set_readme_addon("Integration", "TestIntegration", "Custom Readme")
    assert m1.get_readme_addon("Integration", "TestIntegration") == "Custom Readme"
    assert m2.get_readme_addon("Integration", "TestIntegration") is None


def test_integration_generate_readme_custom_filtering() -> None:
    """Test that non-custom integrations only include custom actions/jobs/connectors in README."""
    import io
    import zipfile
    from ...core.definitions import Integration

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-CommercialTest.def",
            json.dumps(
                {
                    "Identifier": "CommercialTest",
                    "Description": "desc",
                    "PythonVersion": "3.11",
                }
            ),
        )
        zf.writestr(
            "Actions/BuiltInAction.json",
            json.dumps(
                {
                    "Name": "BuiltIn",
                    "Description": "builtin",
                    "TimeoutSeconds": 60,
                    "IsCustom": False,
                }
            ),
        )
        zf.writestr(
            "Actions/LegacyCustomAction.json",
            json.dumps(
                {
                    "Name": "LegacyCustomAct",
                    "Description": "custom",
                    "TimeoutSeconds": 60,
                    "IsCustom": True,
                }
            ),
        )
        zf.writestr(
            "Actions/OnePlatformCustomAction.json",
            json.dumps(
                {
                    "Name": "OnePlatformCustomAct",
                    "Description": "custom 1p",
                    "TimeoutSeconds": 60,
                    "Custom": True,
                }
            ),
        )
    zip_buf.seek(0)

    integration = Integration(
        {"identifier": "CommercialTest", "isCustomIntegration": False},
        zip_buf,
    )
    integration.generate_readme()

    assert "LegacyCustomAct" in integration.readme
    assert "OnePlatformCustomAct" in integration.readme
    assert "BuiltIn" not in integration.readme
