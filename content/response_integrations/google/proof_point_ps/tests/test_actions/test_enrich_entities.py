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

import datetime
from typing import TYPE_CHECKING

from integration_testing.common import create_entity
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from proof_point_ps.actions import enrich_entities
from proof_point_ps.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput
    from TIPCommon.types import Entity

    from proof_point_ps.tests.core.product import ProofPointPSProduct
    from proof_point_ps.tests.core.session import ProofPointPSSession

USER_ENTITY: Entity = create_entity("test_user@example.com", EntityTypesEnum.USER)
HOST_ENTITY: Entity = create_entity("example.com", EntityTypesEnum.HOST_NAME)


def get_deadline_context() -> dict:
    """Return an input context dict with a future execution deadline."""
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=10)
    return {
        "execution_deadline_unix_time_ms": int(
            deadline.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    }


class TestEnrichEntities:
    """Unit tests for EnrichEntities action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[USER_ENTITY],
        input_context=get_deadline_context(),
    )
    def test_enrich_user_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test user entity enrichment success."""
        record = {
            "processingserver": "pps-server-01",
            "date": "2026-06-16T12:00:00Z",
            "subject": "Phishing test",
            "messageid": "msg-111",
            "folder": "Quarantine",
            "size": 1000,
            "rcpts": ["test_user@example.com"],
            "from": "malicious@bad.com",
            "spamscore": 90,
            "guid": "guid-111",
            "host_ip": "1.1.1.1",
            "localguid": "local-guid-111",
        }
        proofpoint.add_record("Quarantine", record)

        enrich_entities.main()

        assert len(script_session.request_history) >= 1
        success_msg = (
            "Successfully enriched the following entities using "
            "Proofpoint Email Protection: TEST_USER@EXAMPLE.COM"
        )
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED

        json_results = action_output.results.json_output.json_result
        assert len(json_results) == 1
        assert json_results[0]["Entity"] == "TEST_USER@EXAMPLE.COM"
        assert len(json_results[0]["EntityResult"]) == 1
        assert json_results[0]["EntityResult"][0]["guid"] == "guid-111"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[HOST_ENTITY],
        input_context=get_deadline_context(),
    )
    def test_enrich_host_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test hostname entity enrichment success."""
        record = {
            "processingserver": "pps-server-02",
            "date": "2026-06-16T12:00:00Z",
            "subject": "Domain test",
            "messageid": "msg-222",
            "folder": "Spam",
            "size": 2000,
            "rcpts": ["some_user@example.com"],
            "from": "attacker@spam.com",
            "spamscore": 99,
            "guid": "guid-222",
            "host_ip": "2.2.2.2",
            "localguid": "local-guid-222",
        }
        proofpoint.add_record("Spam", record)

        enrich_entities.main()

        success_msg = (
            "Successfully enriched the following entities using "
            "Proofpoint Email Protection: EXAMPLE.COM"
        )
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[USER_ENTITY],
        input_context=get_deadline_context(),
    )
    def test_enrich_no_results(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test case where no matching records are returned."""
        enrich_entities.main()

        assert (
            action_output.results.output_message
            == "None of the provided entities were enriched."
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
