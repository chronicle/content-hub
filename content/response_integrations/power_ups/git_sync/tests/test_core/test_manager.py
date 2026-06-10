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
