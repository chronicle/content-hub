# Copyright 2026 RansomLeak
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
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ransomleak.actions import (
    assign_training,
    enrich_users,
    get_training_status,
    list_learning_paths,
    ping,
)
from ransomleak.tests.common import CONFIG_PATH, INTEGRATION_PATH
from ransomleak.tests.core.product import RansomLeak
from ransomleak.tests.core.session import RansomLeakSession

JANE = "jane.doe@example.com"
JOHN = "john.smith@example.com"
JANE_ID = "3f1c2a9e-7b4d-4e2a-9c1f-0a1b2c3d4e5f"
JOHN_ID = "4a2b3c4d-5e6f-4a1b-8c2d-3e4f5a6b7c8d"
LP_ID = "123e4567-e89b-12d3-a456-426614174000"
EXAMPLE_RESULT = json.loads((INTEGRATION_PATH / "resources" / "assign_training_JsonResult_example.json").read_text())
USER_ITEM_KEYS = set(EXAMPLE_RESULT["users"][0])


@pytest.fixture(autouse=True)
def seeded(ransomleak: RansomLeak) -> RansomLeak:
    ransomleak.add_user(
        {
            "id": JANE_ID,
            "email": JANE,
            "firstName": "Jane",
            "lastName": "Doe",
            "externalId": "emp-1",
            "isDisabled": False,
        },
        {
            "exercisesCompleted": 12,
            "totalLearningTimeMinutes": 180,
            "campaignsCompleted": 3,
            "campaignsInProgress": 1,
            "campaignsOverdue": 0,
            "averageQuizScore": 87.5,
            "exerciseHistory": [
                {"exerciseId": "e1", "exerciseName": "Old", "completedAt": "2026-01-01T00:00:00.000Z"},
                {"exerciseId": "e2", "exerciseName": "Email Phishing 101", "completedAt": "2026-10-28T14:30:00.000Z"},
            ],
        },
    )
    ransomleak.risks[JANE_ID] = {
        "score": 58,
        "level": "high",
        "confidence": "medium",
        "subScores": {"susceptibility": 62, "remediation": 40, "training": 25, "external": None, "knowledge": None},
        "computedAt": "2026-11-14T03:00:00.000Z",
    }
    # No externalId: learning path enrollment matches by email, so this does not matter.
    ransomleak.add_user({"id": JOHN_ID, "email": JOHN, "firstName": "John", "lastName": "Smith", "isDisabled": False})
    ransomleak.learning_paths.extend([
        {"id": LP_ID, "name": "Phishing Fundamentals", "description": "Basics"},
        {"id": "8d7e6f5a-4b3c-4d2e-9f1a-0b9c8d7e6f5a", "name": "Password Hygiene", "description": None},
    ])
    ransomleak.exercises.add("phishing-introduction")
    return ransomleak


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success(self, action_output: MockActionOutput) -> None:
        ping.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully connected to the RansomLeak server" in action_output.results.output_message

    @set_metadata(integration_config={"API Root": "https://acme.ransomleak.com", "API Key": "bad", "Verify SSL": True})
    def test_bad_key_fails(self, action_output: MockActionOutput) -> None:
        ping.main()
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to connect to the RansomLeak server" in action_output.results.output_message

    @set_metadata(
        integration_config={"API Root": "http://acme.ransomleak.com", "API Key": "rl_acme.x", "Verify SSL": True},
    )
    def test_plain_http_api_root_fails_without_request(
        self, action_output: MockActionOutput, script_session: RansomLeakSession
    ) -> None:
        ping.main()
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "https" in action_output.results.output_message
        assert script_session.request_history == []


class TestEnrichUsers:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Create Insight": True},
        entities=[
            create_entity(JANE, EntityTypesEnum.USER),
            create_entity("nobody@example.com", EntityTypesEnum.USER),
            create_entity("CORP\\jdoe", EntityTypesEnum.USER),
        ],
    )
    def test_enriches_found_users_and_reports_the_rest(self, action_output: MockActionOutput) -> None:
        enrich_users.main()
        message = action_output.results.output_message
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        # Messages and results keep the entity's original identifier; lookups are case-insensitive.
        assert f"RansomLeak:\n{JANE}" in message
        assert "not found in RansomLeak:\nnobody@example.com" in message
        assert "not an email address:\nCORP\\jdoe" in message
        result = action_output.results.json_output.json_result
        assert result[0]["Entity"] == JANE
        assert result[0]["EntityResult"]["risk_score"] == 58
        assert result[0]["EntityResult"]["risk_level"] == "high"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[create_entity(JANE, EntityTypesEnum.USER)],
    )
    def test_older_backend_without_risk_still_enriches(
        self, action_output: MockActionOutput, seeded: RansomLeak
    ) -> None:
        seeded.risk_endpoint_available = False
        enrich_users.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.json_output.json_result[0]["EntityResult"]["risk_score"] is None

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[create_entity("nobody@example.com", EntityTypesEnum.USER)],
    )
    def test_no_matches_completes_with_false(self, action_output: MockActionOutput) -> None:
        enrich_users.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False


class TestAssignTraining:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Learning Path": "phishing fundamentals",
            "Email Addresses": f"{JOHN}, ghost@example.com",
            "Due In Days": "14",
        },
        entities=[create_entity(JANE, EntityTypesEnum.USER)],
    )
    def test_learning_path_by_name(self, action_output: MockActionOutput, seeded: RansomLeak) -> None:
        assign_training.main()
        message = action_output.results.output_message
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert seeded.enrollments == [
            {"learningPathId": LP_ID, "userId": JANE_ID, "dueDays": 14},
            {"learningPathId": LP_ID, "userId": JOHN_ID, "dueDays": 14},
        ]
        assert "Newly enrolled: 2" in message
        assert JOHN in message
        assert "not found in RansomLeak:\nghost@example.com" in message
        users = {u["email"]: u for u in action_output.results.json_output.json_result["users"]}
        assert users[JANE.lower()]["status"] == "enrolled"
        assert users[JANE.lower()]["enrollment_id"] == f"enr-{JANE_ID}"
        assert users["ghost@example.com"]["status"] == "not_found"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Exercise Slug": "phishing-introduction", "Email Addresses": f"{JANE},{JOHN}"},
    )
    def test_exercise_assignment_returns_ids(self, action_output: MockActionOutput, seeded: RansomLeak) -> None:
        assign_training.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert len(seeded.assignments) == 2
        result = action_output.results.json_output.json_result
        assert result["training_type"] == "exercise"
        assert result["exercise_slug"] == "phishing-introduction"
        assert result["learning_path"] is None
        assert result["enrollment"] is None
        assert result["due_in_days"] is None
        assert set(result["users"][0]) == USER_ITEM_KEYS
        assert result["users"][0]["assignment_id"] in seeded.assignments
        assert result["users"][0]["enrollment_id"] is None

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Learning Path": LP_ID, "Email Addresses": JANE},
    )
    def test_learning_path_schema_matches_exercise_schema(self, action_output: MockActionOutput) -> None:
        assign_training.main()
        result = action_output.results.json_output.json_result
        assert set(result) == set(EXAMPLE_RESULT)
        assert result["exercise_slug"] is None
        assert set(result["users"][0]) == USER_ITEM_KEYS
        assert result["users"][0]["assignment_id"] is None

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Learning Path": LP_ID, "Email Addresses": JANE},
    )
    def test_null_counters_are_treated_as_zero(self, action_output: MockActionOutput, seeded: RansomLeak) -> None:
        seeded.enrollment_response_overrides = {"alreadyEnrolled": None, "skippedUnlicensed": None}
        assign_training.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result["enrollment"] == {
            "assigned": 1,
            "already_enrolled": 0,
            "skipped_unlicensed": 0,
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Learning Path": LP_ID, "Exercise Slug": "phishing-introduction", "Email Addresses": JANE},
    )
    def test_both_targets_fail(self, action_output: MockActionOutput) -> None:
        assign_training.main()
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "exactly one of" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Learning Path": "Nonexistent", "Email Addresses": JANE},
    )
    def test_unknown_learning_path_fails(self, action_output: MockActionOutput) -> None:
        assign_training.main()
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "List Learning Paths" in action_output.results.output_message


class TestGetTrainingStatus:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Email Addresses": "ghost@example.com", "Assignment IDs": "00000000-0000-0000-0000-000000000000"},
        entities=[create_entity(JANE, EntityTypesEnum.USER)],
    )
    def test_users_and_missing_assignment(self, action_output: MockActionOutput) -> None:
        get_training_status.main()
        message = action_output.results.output_message
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert JANE in message
        assert "ghost@example.com" in message
        assert "00000000-0000-0000-0000-000000000000" in message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_input_fails(self, action_output: MockActionOutput) -> None:
        get_training_status.main()
        assert action_output.results.execution_state == ExecutionState.FAILED


class TestListLearningPaths:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Filter Value": "phish", "Max Results To Return": "10"},
    )
    def test_filter(self, action_output: MockActionOutput) -> None:
        list_learning_paths.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "Successfully found 1 learning path(s) in RansomLeak."

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Filter Value": "zzz"},
    )
    def test_no_match(self, action_output: MockActionOutput) -> None:
        list_learning_paths.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
