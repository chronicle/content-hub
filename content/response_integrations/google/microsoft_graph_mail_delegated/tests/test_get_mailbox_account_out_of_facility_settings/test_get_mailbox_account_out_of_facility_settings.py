from __future__ import annotations

import datetime

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import Entity

from actions import (
    GetMailboxAccountOutOfFacilitySettings,
)
from tests.common import (
    CONFIG_PATH,
    USER_JSON,
    DEFAULT_USER_OOF_SETTINGS,
    FAILED_USER_JSON,
)

from tests.conftest import MsGraphSession
from tests.core.product import (
    MicrosoftGraphMailDelegated,
)
from tests.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = "Successfully returned OOF settings for the:\nabcd@x.com"
FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "MicrosoftGraphMailDelegated - Get Mailbox Account '
    + 'Out Of Facility Settings".\nReason: Failed to execute action because '
    + "no supported entity was found!"
)
USERNAME_ENTITY_ID = "abcd@x.com"
USERNAME_ENTITY_1: Entity = create_entity(USERNAME_ENTITY_ID, EntityTypesEnum.USER)
FAIL_ENTITY_ID = "sample123hostname"
FAIL_ENTITY_1: Entity = create_entity(FAIL_ENTITY_ID, EntityTypesEnum.HOST_NAME)
SCRIPT_DEADLINE_TIME = datetime.datetime.now() + datetime.timedelta(minutes=10)
ACTION_SUCCESS_JSON = [
    {
        "Entity": "abcd@x.com",
        "EntityResult": {
            "@odata.context": "msdata",
            "id": "user-id",
            "availability": "availability",
            "activity": "availability",
            "statusMessage": "msg",
            "outOfOfficeSettings": {"message": "msg", "isOutOfOffice": "false"},
        },
    }
]
ACTION_SUCCESS_OUTPUT = ActionOutput(
    output_message=SUCCESS_OUTPUT_MESSAGE,
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=ActionJsonOutput(json_result=ACTION_SUCCESS_JSON),
)
ACTION_FAILED_OUTPUT = ActionOutput(
    output_message=FAILED_OUTPUT_MESSAGE,
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)


@set_metadata(
    parameters={
        "Base64 Encoded Private Key": "",
        "Base64 Encoded Certificate": "",
        "Base64 Encoded CA certificate": "",
        "Email Exclude Pattern": "",
    },
    integration_config_file_path=CONFIG_PATH,
    entities=[USERNAME_ENTITY_1],
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_get_mailbox_account_out_of_facility_settings_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_user_oof_settings(DEFAULT_USER_OOF_SETTINGS)

    GetMailboxAccountOutOfFacilitySettings.GetMailboxAccountOutOfFacilitySettings().run(
    )
    assert len(script_session.request_history) == 3
    assert action_output.results == ACTION_SUCCESS_OUTPUT


@set_metadata(
    parameters={
        "Base64 Encoded Private Key": "",
        "Base64 Encoded Certificate": "",
        "Base64 Encoded CA certificate": "",
        "Email Exclude Pattern": "",
    },
    integration_config_file_path=CONFIG_PATH,
    entities=[FAIL_ENTITY_1],
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_get_mailbox_account_out_of_facility_settings_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(FAILED_USER_JSON)
    ms_graph_mail.add_user_oof_settings(DEFAULT_USER_OOF_SETTINGS)

    GetMailboxAccountOutOfFacilitySettings.GetMailboxAccountOutOfFacilitySettings().run(
    )
    assert len(script_session.request_history) == 1
    assert action_output.results == ACTION_FAILED_OUTPUT
