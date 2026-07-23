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

import pathlib
from copy import deepcopy

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from ...actions import UpdateDetection
from ...core.constants import (
    INTEGRATION_NAME,
    UPDATE_DETECTION_SCRIPT_NAME,
)
from ...core.datamodels import Detection
from ...tests import common
from ...tests.core.product import Extrahop
from ...tests.core.session import ExtrahopSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


DETECTION: Detection = common.DETECTION
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully updated detection with ID {DETECTION.id} in {INTEGRATION_NAME}."
)
FAILED_OUTPUT_MESSAGE: str = (
    f'Error executing action "{UPDATE_DETECTION_SCRIPT_NAME}".\nReason: '
    "Detection with ID \"999999\" wasn't found in Extrahop. Please check the spelling."
)

DEFAULT_PARAMETERS: dict[str, str] = {
    "Detection ID": DETECTION.id,
    "Status": "Closed",
    "Resolution": "Action Taken",
}
FAILED_PARAMETERS: dict[str, str] = {
    "Detection ID": 999999,
    "Status": "Closed",
    "Resolution": "Action Taken",
}


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_update_detection_action_success(
    extrahop: Extrahop,
    script_session: ExtrahopSession,
    action_output: MockActionOutput,
) -> None:
    extrahop.cleanup_detections()
    detection: Detection = deepcopy(common.DETECTION)
    extrahop.add_detection(detection)
    UpdateDetection.main()
    assert len(script_session.request_history) == 3
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=common.CONFIG, parameters=FAILED_PARAMETERS)
def test_update_detection_action_failure(
    extrahop: Extrahop,
    script_session: ExtrahopSession,
    action_output: MockActionOutput,
) -> None:
    extrahop.cleanup_detections()
    detection: Detection = deepcopy(common.DETECTION)
    detection.id = "999999"
    detection.raw_data["id"] = "999999"
    extrahop.add_detection(detection)
    UpdateDetection.main()
    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
