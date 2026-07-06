from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from Integrations.MicrosoftGraphMailDelegated.ActionsScripts import GenerateToken
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata

AUTHORIZED_URL: str = (
    "http://localhost/?code=1000.ac445cfb678764b9da88ac5024b767c5.ac445cfb6724b76"
)
WRONG_AUTHORIZED_URL: str = (
    "https://login.com/?"
)
GENERATE_TOKEN_SUCCESS_OUTPUT: ActionOutput = ActionOutput(
    output_message=(
        "Successfully fetched the refresh token: "
        "\n1000.ac445cfb678764b9da88ac5024b767c5.ac445cfb6724b76\n"
        "Enter this token in the integration configuration to enable the integration "
        "authenticate with delegated permissions on behalf of the user that performed "
        "the configuration steps.\nNote: We recommended you to configure "
        "a “Refresh Token Renewal Job” after you generate the initial refresh token "
        "so the job automatically renews and keeps the token valid."
    ),
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=None,
)
GENERATE_TOKEN_FAILED_OUTPUT: ActionOutput = ActionOutput(
    output_message=(
        "Error executing action \"MicrosoftGraphMailDelegated - Generate Token\".\n"
        "Reason: Failed to generate a token because the authorization URL that you "
        "provided is incorrect. The \"code\" parameter is missing. "
        "Please check, if you copied the whole URL properly."
    ),
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)


@set_metadata(
    parameters={"Authorization URL": AUTHORIZED_URL},
    integration_config_file_path=CONFIG_PATH
)
def test_generate_token_success(
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    GenerateToken.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == GENERATE_TOKEN_SUCCESS_OUTPUT


@set_metadata(
    parameters={"Authorization URL": WRONG_AUTHORIZED_URL},
    integration_config_file_path=CONFIG_PATH
)
def test_generate_token_failed(
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    GenerateToken.main()

    assert len(script_session.request_history) == 0
    assert action_output.results == GENERATE_TOKEN_FAILED_OUTPUT
