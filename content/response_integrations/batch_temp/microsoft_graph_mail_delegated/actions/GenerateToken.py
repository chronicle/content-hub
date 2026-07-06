from __future__ import annotations
from typing import NoReturn

from urllib.parse import urlparse, parse_qs

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.types import SingleJson
from TIPCommon.base.utils import CreateSession
from ..core import constants
from ..core.exceptions import MicrosoftGraphMailManagerError, RefreshTokenRetrievalError
from ..core import MicrosoftGraphMailDelegatedManager as api_manager
from ..core import AuthenticationManager as auth_manager
from ..core import utils


def _extract_code_from_url(url: str) -> str:
    """Extracts the 'code' parameter from the provided URL.

    Args:
        url(str): The URL to extract the code from.

    Returns:
        str: The code value if found, otherwise None.
    """
    parsed_url: urlparse = urlparse(url)
    query: SingleJson = parse_qs(parsed_url.query)

    return query.get("code")[0] if "code" in query else ""


class GenerateToken(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.GENERATE_TOKEN_SCRIPT_NAME)
        self.output_message = ""
        self.result_value = False
        self.error_output_message = (
            f"Error executing action \"{constants.GENERATE_TOKEN_SCRIPT_NAME}\"."
        )
        self.session = CreateSession.create_session()

    def _init_api_clients(self) -> api_manager.ApiManager:
        pass

    def _extract_action_parameters(self) -> None:
        self.params.authorization_url = extract_action_param(
            self.soar_action,
            param_name="Authorization URL",
            is_mandatory=True,
            print_value=True,
        )
        self.params.integration_parameters = utils.get_integration_parameters(
            self.soar_action
        )

    def _get_session_parameters(self) -> None:
        return auth_manager.SessionAuthenticationParameters(
            azure_ad_endpoint=self.params.integration_parameters.azure_ad_endpoint,
            client_id=self.params.integration_parameters.client_id,
            client_secret=self.params.integration_parameters.secret_id,
            tenant=self.params.integration_parameters.tenant,
            refresh_token=self.params.integration_parameters.refresh_token,
            verify_ssl=self.params.integration_parameters.verify_ssl,
        )

    def _validate_params(self) -> None:
        pass

    def _perform_action(self, _) -> None:
        code: str = _extract_code_from_url(self.params.authorization_url)
        if code:
            try:
                refresh_token: str = self._generate_refresh_token(code)
                self._set_success_message(refresh_token)
                self.result_value = True

            except (RefreshTokenRetrievalError, MicrosoftGraphMailManagerError) as e:
                self._set_failure_message(e)
        else:
            self._set_failure_message()

    def _generate_refresh_token(self, code: str) -> str:
        return auth_manager.get_refresh_token_from_code(
            session=self.session,
            session_parameters=self._get_session_parameters(),
            code=code,
            redirect_url=self.params.integration_parameters.redirect_url,
        )

    def _set_success_message(self, refresh_token: str) -> None:
        self.output_message: str = (
            f"Successfully fetched the refresh token: \n{refresh_token}\n"
            "Enter this token in the integration configuration to enable the "
            "integration authenticate with delegated permissions on behalf of the user "
            "that performed the configuration steps.\nNote: We recommended you to "
            "configure a “Refresh Token Renewal Job” after you generate the initial "
            "refresh token so the job automatically renews and keeps the token valid."
        )

    def _set_failure_message(self, error: Exception | None = None) -> None:
        if error:
            raise RefreshTokenRetrievalError(
                f"Failed to get the refresh token! {error}"
            )
        raise RefreshTokenRetrievalError(
            "Failed to generate a token because the authorization URL "
            "that you provided is incorrect. The \"code\" parameter is missing. Please "
            "check, if you copied the whole URL properly."
        )


def main() -> NoReturn:
    action: GenerateToken = GenerateToken()
    action.run()


if __name__ == "__main__":
    main()
