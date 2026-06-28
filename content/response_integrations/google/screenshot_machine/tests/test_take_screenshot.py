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
import pathlib

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from TIPCommon.types import Entity

from screenshot_machine.actions import TakeScreenshot
from screenshot_machine.core.ScreenshotMachineManager import (
    SCREENSHOT_MACHINE_URL,
)
from screenshot_machine.tests.common import CONFIG_FILE
from screenshot_machine.tests.core.session import (
    ScreenshotMachineSession,
)
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.request import MockRequest
from integration_testing.requests.session import HistoryRecord
from integration_testing.set_meta import set_metadata


ACTION_FAILURE_OUTPUT_MSG: str = (
    "Action wasn't able to return screenshot for the provided entities."
)
URL_ENTITY_ID_1: str = "www.mockEntity.com"
URL_ENTITY_ID_2: str = "www.2mockEntity2.com"
MAC_ADDRESS_ENTITY_ID_1: str = "00-B0-D0-63-C2-26"
MAC_ADDRESS_ENTITY_ID_2: str = "11-B0-D0-63-C2-26"
ADDRESS_ENTITY_ID: str = "8.8.8.8"
HOSTNAME_ENTITY_ID: str = "en.wikipedia.org"
DEADLINE_INPUT_CONTEXT: dict[str, int] = {
    "execution_deadline_unix_time_ms": 999_999_999_999_999
}
MAC_ADDRESS_ENTITY_1: Entity = create_entity(
    MAC_ADDRESS_ENTITY_ID_1, EntityTypesEnum.MAC_ADDRESS
)
MAC_ADDRESS_ENTITY_2: Entity = create_entity(
    MAC_ADDRESS_ENTITY_ID_2, EntityTypesEnum.MAC_ADDRESS
)
URL_ENTITY_1: Entity = create_entity(URL_ENTITY_ID_1, EntityTypesEnum.URL)
URL_ENTITY_2: Entity = create_entity(URL_ENTITY_ID_2, EntityTypesEnum.URL)
ADDRESS_ENTITY: Entity = create_entity(ADDRESS_ENTITY_ID, EntityTypesEnum.ADDRESS)
HOSTNAME_ENTITY: Entity = create_entity(HOSTNAME_ENTITY_ID, EntityTypesEnum.HOST_NAME)


class TestGeneralCases:

    @set_metadata(
        integration_config_file_path=CONFIG_FILE,
        entities=[URL_ENTITY_1],
        input_context=DEADLINE_INPUT_CONTEXT,
    )
    def test_happy_path_default_parameter_values_with_one_valid_entity(
        self,
        script_session: ScreenshotMachineSession,
        action_output: MockActionOutput,
    ) -> None:
        TakeScreenshot.main()

        assert action_output.results == ActionOutput(
            output_message=(
                "\n Successfully returned screenshot for the following entities:\n   "
                f"{URL_ENTITY_ID_1}"
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "www.mockEntity.com",
                        "EntityResult": (
                            "b'Q3JlYXRlZCBTY3JlZW5zaG90OiBzb21lQXBpS2V5LCB3d3cubW9ja0Vu"
                            "dGl0eS5jb20sIE5vbmUsIGRlc2t0b3AsIDEwMjR4ZnVsbCwgMCwgMjAw"
                            "MA=='"
                        ),
                    }
                ]
            ),
        )
        assert len(script_session.request_history) == 1
        assert_request(script_session.request_history)

    @set_metadata(
        integration_config_file_path=CONFIG_FILE,
        entities=[URL_ENTITY_1],
    )
    def test_action_timeout(
        self,
        script_session: ScreenshotMachineSession,
        action_output: MockActionOutput,
    ) -> None:
        TakeScreenshot.main()

        assert not script_session.request_history
        assert action_output.results == ActionOutput(
            output_message=ACTION_FAILURE_OUTPUT_MSG,
            result_value=False,
            execution_state=ExecutionState.TIMED_OUT,
            json_output=ActionJsonOutput(json_result=[]),
        )


class TestEntities:

    @set_metadata(integration_config_file_path=CONFIG_FILE)
    def test_no_entities(
        self,
        script_session: ScreenshotMachineSession,
        action_output: MockActionOutput,
    ) -> None:
        TakeScreenshot.main()

        assert not script_session.request_history
        assert action_output.results == ActionOutput(
            output_message=ACTION_FAILURE_OUTPUT_MSG,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[],
            ),
        )

    @set_metadata(
        integration_config_file_path=CONFIG_FILE,
        entities=[MAC_ADDRESS_ENTITY_1],
        input_context=DEADLINE_INPUT_CONTEXT,
    )
    def test_one_invalid_entity_type(
        self,
        script_session: ScreenshotMachineSession,
        action_output: MockActionOutput,
    ) -> None:
        TakeScreenshot.main()

        assert not script_session.request_history
        assert action_output.results == ActionOutput(
            output_message=ACTION_FAILURE_OUTPUT_MSG,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[],
            ),
        )

    @set_metadata(
        integration_config_file_path=CONFIG_FILE,
        entities=[URL_ENTITY_1, MAC_ADDRESS_ENTITY_1],
        input_context=DEADLINE_INPUT_CONTEXT,
    )
    def test_one_valid_entity_type_and_one_invalid_entity_type(
        self,
        script_session: ScreenshotMachineSession,
        action_output: MockActionOutput,
    ) -> None:
        TakeScreenshot.main()

        assert len(script_session.request_history) == 1
        assert action_output.results == ActionOutput(
            output_message=(
                "\n Successfully returned screenshot for the following entities:\n   "
                f"{URL_ENTITY_ID_1}"
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "www.mockEntity.com",
                        "EntityResult": (
                            "b'Q3JlYXRlZCBTY3JlZW5zaG90OiBzb21lQXBpS2V5LCB3d3cubW9ja0Vu"
                            "dGl0eS5jb20sIE5vbmUsIGRlc2t0b3AsIDEwMjR4ZnVsbCwgMCwgMjAwM"
                            "A=='"
                        ),
                    },
                ],
            ),
        )

    @set_metadata(
        integration_config_file_path=CONFIG_FILE,
        entities=[
            URL_ENTITY_1,
            URL_ENTITY_2,
            MAC_ADDRESS_ENTITY_1,
            MAC_ADDRESS_ENTITY_2,
        ],
        input_context=DEADLINE_INPUT_CONTEXT,
    )
    def test_multiple_valid_entity_type_and_multiple_invalid_entity_type(
        self,
        script_session: ScreenshotMachineSession,
        action_output: MockActionOutput,
    ) -> None:
        TakeScreenshot.main()

        assert len(script_session.request_history) == 2
        assert_request(script_session.request_history)
        assert action_output.results == ActionOutput(
            output_message=(
                "\n Successfully returned screenshot for the following entities:\n   "
                f"{URL_ENTITY_ID_1}\n   {URL_ENTITY_ID_2}"
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "www.mockEntity.com",
                        "EntityResult": (
                            "b'Q3JlYXRlZCBTY3JlZW5zaG90OiBzb21lQXBpS2V5LCB3d3cubW9ja0Vu"
                            "dGl0eS5jb20sIE5vbmUsIGRlc2t0b3AsIDEwMjR4ZnVsbCwgMCwgMjAwM"
                            "A=='"
                        ),
                    },
                    {
                        "Entity": "www.2mockEntity2.com",
                        "EntityResult": (
                            "b'Q3JlYXRlZCBTY3JlZW5zaG90OiBzb21lQXBpS2V5LCB3d3cuMm1vY"
                            "2tFbnRpdHkyLmNvbSwgTm9uZSwgZGVza3RvcCwgMTAyNHhmdWxsLCAw"
                            "LCAyMDAw'"
                        ),
                    },
                ],
            ),
        )

    @set_metadata(
        integration_config_file_path=CONFIG_FILE,
        entities=[URL_ENTITY_1, ADDRESS_ENTITY, HOSTNAME_ENTITY],
        input_context=DEADLINE_INPUT_CONTEXT,
    )
    def test_all_supported_entity_types(
        self,
        script_session: ScreenshotMachineSession,
        action_output: MockActionOutput,
    ) -> None:
        TakeScreenshot.main()

        assert len(script_session.request_history) == 3
        assert_request(script_session.request_history)
        assert action_output.results == ActionOutput(
            output_message=(
                "\n Successfully returned screenshot for the following entities:\n   "
                f"{URL_ENTITY_ID_1}\n   {ADDRESS_ENTITY_ID}\n   {HOSTNAME_ENTITY_ID}"
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "www.mockEntity.com",
                        "EntityResult": (
                            "b'Q3JlYXRlZCBTY3JlZW5zaG90OiBzb21lQXBpS2V5LCB3d3cubW9ja0Vu"
                            "dGl0eS5jb20sIE5vbmUsIGRlc2t0b3AsIDEwMjR4ZnVsbCwgMCwgMjAwM"
                            "A=='"
                        ),
                    },
                    {
                        "Entity": "8.8.8.8",
                        "EntityResult": (
                            "b'Q3JlYXRlZCBTY3JlZW5zaG90OiBzb21lQXBpS2V5LCA4LjguOC44L"
                            "CBOb25lLCBkZXNrdG9wLCAxMDI0eGZ1bGwsIDAsIDIwMDA='"
                        ),
                    },
                    {
                        "Entity": "en.wikipedia.org",
                        "EntityResult": (
                            "b'Q3JlYXRlZCBTY3JlZW5zaG90OiBzb21lQXBpS2V5LCBlbi53aWtpcG"
                            "VkaWEub3JnLCBOb25lLCBkZXNrdG9wLCAxMDI0eGZ1bGwsIDAsIDI"
                            "wMDA='"
                        ),
                    },
                ],
            ),
        )


def assert_request(request_history: list[HistoryRecord]) -> None:
    for record in request_history:
        req: MockRequest = record.request
        sent_request: str = f"{req.url.scheme}://{req.url.netloc}{req.url.path}"
        assert sent_request == SCREENSHOT_MACHINE_URL
