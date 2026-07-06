from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts import Ping
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG,
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.request import MockRequest
from Tests.mocks.set_meta import set_metadata


PING_SUCCESS_OUTPUT = ActionOutput(
    output_message=(
        "Successfully connected to the MicrosoftGraphMailDelegated service with the"
        " provided connection parameters!"
    ),
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=None,
)
PING_FAILED_OUTPUT = ActionOutput(
    output_message=(
        "Failed to connect to the MicrosoftGraphMailDelegated server!\nReason: An error"
        " occurred: Failed to authenticate to MicrosoftGraphMailDelegated"
    ),
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)
FAILED_CONFIG = CONFIG.copy()
FAILED_CONFIG["Client ID"] = "raise_error"


@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_ping_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    Ping.main()
    assert action_output.results == PING_SUCCESS_OUTPUT
    assert_ping_request(script_session)


@set_metadata(integration_config=FAILED_CONFIG)
def test_ping_400_failure(
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    Ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == PING_FAILED_OUTPUT


def assert_ping_request(script_session: MsGraphSession) -> None:
    assert len(script_session.request_history) == 3
    req: MockRequest = script_session.request_history[0].request
    sent_request: str = f"{req.url.scheme}://{req.url.netloc}{req.url.path}"
    assert "/oauth2/v2.0/token" in sent_request
