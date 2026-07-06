from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.types import SingleJson

from Integrations.MicrosoftGraphMailDelegated.ActionsScripts import GetAuthorization
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata


DEFAULT_REDIRECT_URL: str = "http://localhost"
PARAMETERS: SingleJson = {"Redirect URL": DEFAULT_REDIRECT_URL}
GENERATE_TOKEN_SUCCESS_OUTPUT: ActionOutput = ActionOutput(
    output_message=(
        "Authorization URL generated successfully. To obtain a URL with access code, "
        "navigate to the link below as the user that you want to run the integration "
        "with. Provide the URL with the access code should be provided next in the "
        "Generate Token action."
    ),
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=None,
)


@set_metadata(
    parameters=PARAMETERS,
    integration_config_file_path=CONFIG_PATH
)
def test_generate_token_success(
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    GetAuthorization.main()

    assert len(script_session.request_history) == 0
    assert action_output.results == GENERATE_TOKEN_SUCCESS_OUTPUT
