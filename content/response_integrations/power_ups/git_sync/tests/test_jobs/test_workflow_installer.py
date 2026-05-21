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

from unittest.mock import MagicMock
from TIPCommon.types import ChronicleSOAR
from ...core.definitions import Workflow, WorkflowTypes
from ...core.GitSyncManager import WorkflowInstaller


def test_duplicate_step_names_matching_prevention() -> None:
    """Tests that if there are multiple steps with the exact same instance name (e.g., multiple
    containers named 'Parallel Actions 4'), they are matched to different, unique local steps
    rather than mapping to the same step, preventing structural collapse.
    """
    # 1. Define the incoming Git playbook data with two steps named "Parallel Actions 4"
    git_playbook_data = {
        "id": 0,
        "identifier": "git-playbook-uuid",
        "name": "Test Playbook",
        "playbookType": WorkflowTypes.PLAYBOOK.value,
        "priority": 1,
        "isEnabled": True,
        "categoryName": "Default",
        "environments": ["Default Environment"],
        "modificationTimeUnixTimeInMs": 2000,
        "trigger": {
            "id": 0,
            "identifier": "trigger-uuid"
        },
        "steps": [
            {
                "identifier": "git_PA4_1",
                "originalStepIdentifier": "git_PA4_1",
                "instanceName": "Parallel Actions 4",
                "actionProvider": "ParallelActionsContainer",
                "type": 7,
                "parameters": [],
                "parallelActions": []
            },
            {
                "identifier": "git_PA4_2",
                "originalStepIdentifier": "git_PA4_2",
                "instanceName": "Parallel Actions 4",
                "actionProvider": "ParallelActionsContainer",
                "type": 7,
                "parameters": [],
                "parallelActions": []
            }
        ],
        "stepsRelations": []
    }
    git_workflow = Workflow(git_playbook_data)

    # 2. Define the target local playbook on SOAR with two steps named "Parallel Actions 4"
    local_playbook_data = {
        "id": 123,
        "identifier": "local-playbook-uuid",
        "originalPlaybookIdentifier": "local-playbook-uuid",
        "name": "Test Playbook",
        "playbookType": WorkflowTypes.PLAYBOOK.value,
        "categoryName": "Default",
        "categoryId": 10,
        "trigger": {
            "id": 99,
            "identifier": "local-trigger-uuid"
        },
        "steps": [
            {
                "identifier": "local_PA4_1",
                "instanceName": "Parallel Actions 4",
                "actionProvider": "ParallelActionsContainer",
                "type": 7,
                "parameters": [],
                "parallelActions": []
            },
            {
                "identifier": "local_PA4_2",
                "instanceName": "Parallel Actions 4",
                "actionProvider": "ParallelActionsContainer",
                "type": 7,
                "parameters": [],
                "parallelActions": []
            }
        ]
    }

    # 3. Mock the APIs
    mock_api = MagicMock()
    mock_api.get_playbooks.return_value = [local_playbook_data]
    mock_api.get_playbook.return_value = local_playbook_data
    mock_api.get_soc_roles.return_value = []
    mock_api.get_playbook_categories.return_value = [{"id": 10, "name": "Default"}]

    # Mock cache
    mock_cache = MagicMock()
    mock_cache.get.return_value = -1

    # 4. Instantiate installer
    chronicle_soar = MagicMock(spec=ChronicleSOAR)
    installer = WorkflowInstaller(
        chronicle_soar=chronicle_soar,
        api=mock_api,
        logger=MagicMock(),
        mod_time_cache=mock_cache
    )

    # 5. Run update
    installer.update_local_workflow(git_workflow)

    # 6. Capture what was saved
    mock_api.save_playbook.assert_called_once()
    saved_playbook_payload = mock_api.save_playbook.call_args[0][0]

    # 7. Verify results
    steps = saved_playbook_payload["steps"]
    step_1 = next(x for x in steps if x["identifier"] == "local_PA4_1")
    step_2 = next(x for x in steps if x["identifier"] == "local_PA4_2")

    # Assert that each step matched a DIFFERENT, UNIQUE local step ID using pytest asserts
    assert step_1["identifier"] != step_2["identifier"]
    assert {step_1["identifier"], step_2["identifier"]} == {"local_PA4_1", "local_PA4_2"}
