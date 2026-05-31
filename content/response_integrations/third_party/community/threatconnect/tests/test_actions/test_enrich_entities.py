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

"""Tests for Enrich Entities action."""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from threatconnect.actions import enrich_entities
from threatconnect.core.data_models import IndicatorData
from threatconnect.tests.common import CONFIG_PATH, INDICATOR_MOCK_RAW

if TYPE_CHECKING:
    from threatconnect.tests.core.product import ThreatConnectProduct
    from threatconnect.tests.core.session import ThreatConnectSession

URL_VAL = "http://markossolomon.com/f1q7qx.php"
URL_ENTITY = create_entity(URL_VAL, EntityTypesEnum.URL)
IP_ENTITY = create_entity("1.1.1.1", EntityTypesEnum.ADDRESS)
HOST_ENTITY = create_entity("test.com", EntityTypesEnum.HOST_NAME)
FILE_ENTITY = create_entity(
    "f5a2496cf66cb8cffe66cb1b27d7dede",
    EntityTypesEnum.FILE_HASH
)


def get_future_deadline_context() -> dict[str, int]:
    """Get a fresh script context with a future execution deadline."""
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=10)
    ms_val = int(deadline.timestamp() * NUM_OF_MILLI_IN_SEC)
    return {"execution_deadline_unix_time_ms": ms_val}


class TestEnrichEntities:
    """Test cases for Enrich Entities action."""

    @set_metadata(
        parameters={"Owner Name": "S"},
        integration_config_file_path=CONFIG_PATH,
        entities=[URL_ENTITY, IP_ENTITY],
        input_context=get_future_deadline_context(),
    )
    def test_enrich_entities_success(
        self,
        script_session: ThreatConnectSession,
        action_output: MockActionOutput,
        threatconnect: ThreatConnectProduct,
    ) -> None:
        """Test successful execution of Enrich Entities action."""
        url_raw = INDICATOR_MOCK_RAW.copy()
        url_raw["summary"] = "http://markossolomon.com/f1q7qx.php"
        url_raw["type"] = "URL"
        threatconnect.add_indicator(
            "http://markossolomon.com/f1q7qx.php",
            IndicatorData.from_json(url_raw),
        )

        ip_raw = INDICATOR_MOCK_RAW.copy()
        ip_raw["summary"] = "1.1.1.1"
        ip_raw["type"] = "Address"
        threatconnect.add_indicator("1.1.1.1", IndicatorData.from_json(ip_raw))

        enrich_entities.main()

        tc_requests = [
            rec
            for rec in script_session.request_history
            if "/api/v3/" in rec.request.url.path
        ]
        assert len(tc_requests) == 2

        url_req = tc_requests[0].request
        expected_path = (
            "/api/v3/indicators/"
            "http%3A%2F%2Fmarkossolomon.com%2Ff1q7qx.php"
        )
        assert url_req.url.path == expected_path
        assert url_req.kwargs.get("params") == {
            "fields": [
                "tags",
                "attributes",
                "securityLabels",
                "associatedGroups",
                "associatedGroups.tags",
                "associatedGroups.attributes",
                "associatedGroups.securityLabels",
                "associatedIndicators",
                "associatedIndicators.threatAssess",
                "threatAssess",
            ],
            "owner": "S",
        }

        ip_req = tc_requests[1].request
        assert ip_req.url.path == "/api/v3/indicators/1.1.1.1"

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        msg = action_output.results.output_message
        assert "Following entities were enriched by ThreatConnect." in msg
        assert (
            re.search(
                r"HTTP://MARKOSSOLOMON\.COM/F1Q7QX\.PHP",
                action_output.results.output_message,
            )
            is not None
        )
        assert "1.1.1.1" in action_output.results.output_message

    @set_metadata(
        parameters={"Owner Name": ""},
        integration_config_file_path=CONFIG_PATH,
        entities=[URL_ENTITY, IP_ENTITY],
        input_context=get_future_deadline_context(),
    )
    def test_enrich_entities_no_indicator_found(
        self,
        script_session: ThreatConnectSession,
        action_output: MockActionOutput,
        threatconnect: ThreatConnectProduct,
    ) -> None:
        """Test execution when no matching indicator is found.

        Checks backend response.
        """
        enrich_entities.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "No entities were enriched." in action_output.results.output_message
        assert action_output.results.result_value is False

    @set_metadata(
        parameters={"Owner Name": ""},
        integration_config_file_path=CONFIG_PATH,
        entities=[URL_ENTITY, IP_ENTITY],
        input_context=get_future_deadline_context(),
    )
    def test_enrich_entities_partial_success(
        self,
        script_session: ThreatConnectSession,
        action_output: MockActionOutput,
        threatconnect: ThreatConnectProduct,
    ) -> None:
        """Test execution with partial enrichment.

        Test execution when only a subset is successfully enriched.
        """
        url_raw = INDICATOR_MOCK_RAW.copy()
        url_raw["summary"] = "http://markossolomon.com/f1q7qx.php"
        url_raw["type"] = "URL"
        threatconnect.add_indicator(
            "http://markossolomon.com/f1q7qx.php",
            IndicatorData.from_json(url_raw),
        )

        enrich_entities.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        msg = action_output.results.output_message
        assert "Following entities were enriched by ThreatConnect." in msg
        assert (
            re.search(
                r"HTTP://MARKOSSOLOMON\.COM/F1Q7QX\.PHP",
                action_output.results.output_message,
            )
            is not None
        )
        assert "1.1.1.1" not in action_output.results.output_message
        assert action_output.results.result_value is True

    @set_metadata(
        parameters={"Owner Name": ""},
        integration_config_file_path=CONFIG_PATH,
        entities=[HOST_ENTITY],
        input_context=get_future_deadline_context(),
    )
    def test_enrich_entities_suspicious_threshold(
        self,
        script_session: ThreatConnectSession,
        action_output: MockActionOutput,
        threatconnect: ThreatConnectProduct,
    ) -> None:
        """Test that entities are flagged based on threatAssessRating."""
        host_raw = INDICATOR_MOCK_RAW.copy()
        host_raw["summary"] = "test.com"
        host_raw["type"] = "Host"
        host_raw["rating"] = 4.5
        threatconnect.add_indicator("test.com", IndicatorData.from_json(host_raw))

        enrich_entities.main()

        assert action_output.results is not None
        assert (
            re.search(r"TEST\.COM", action_output.results.output_message)
            is not None
        )

        req_history = script_session.request_history[-1]
        updated_entities = req_history.request.kwargs.get("json", [])
        assert len(updated_entities) > 0
        assert updated_entities[0].get("is_suspicious") is True
