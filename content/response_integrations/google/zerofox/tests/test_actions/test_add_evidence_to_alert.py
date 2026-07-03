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
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.types import SingleJson

from ...actions import AddEvidenceToAlert
from ...core.constants import ADD_EVIDENCE_TO_ALERT_SCRIPT_NAME
from ...tests import common
from ...tests.core.product import Zerofox
from ...tests.core.session import ZerofoxSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


FILE_PATH: str = common.create_temp_file()
ALERT: SingleJson = common.LIST_ALERTS["alerts"][0]
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully added evidence to the alert with ID {ALERT['id']}."
)
FAILED_OUTPUT_MESSAGE: str = (
    f'Error executing action "{ADD_EVIDENCE_TO_ALERT_SCRIPT_NAME}".\nReason: Alert '
    f"with ID {common.INVALID_ALERT_ID} wasn't found in Zerofox."
)

DEFAULT_PARAMETERS: dict[str, str] = {
    "Alert ID": ALERT["id"],
    "Filepath": FILE_PATH,
}
FAILED_PARAMETERS: dict[str, str] = {
    "Alert ID": common.INVALID_ALERT_ID,
    "Filepath": FILE_PATH,
}


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_add_evidence_to_alert_success(
    zerofox: Zerofox,
    script_session: ZerofoxSession,
    action_output: MockActionOutput,
) -> None:
    zerofox.cleanup_alerts()
    alert = ALERT.copy()
    zerofox.add_alert(alert)
    AddEvidenceToAlert.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=SUCCESS_OUTPUT_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


@set_metadata(integration_config=common.CONFIG, parameters=FAILED_PARAMETERS)
def test_add_evidence_to_alert_failure(
    zerofox: Zerofox,
    script_session: ZerofoxSession,
    action_output: MockActionOutput,
) -> None:
    zerofox.cleanup_alerts()
    alert = ALERT.copy()
    alert["id"] = common.INVALID_ALERT_ID
    zerofox.add_alert(alert)
    AddEvidenceToAlert.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
