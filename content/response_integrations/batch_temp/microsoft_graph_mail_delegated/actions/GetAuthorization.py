from __future__ import annotations
from typing import NoReturn

from urllib.parse import urlencode
from TIPCommon.base.action import Action
from ..core import constants
from ..core import MicrosoftGraphMailDelegatedManager as api_manager
from ..core import utils


class GetAuthorization(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.GET_AUTHORIZATION_SCRIPT_NAME)
        self.error_output_message = "Failed to generate the authorization URL!"
        self.output_message = (
            "Authorization URL generated successfully. To obtain a URL with access "
            "code, navigate to the link below as the user that you want to run the "
            "integration with. Provide the URL with the access code should be provided "
            "next in the Generate Token action."
        )

    def _init_api_clients(self) -> api_manager.ApiManager:
        pass

    def _extract_action_parameters(self) -> None:
        pass

    def _validate_params(self) -> None:
        pass

    def _perform_action(self, _) -> None:
        params = utils.get_integration_parameters(self.soar_action)
        url = self._get_authorization_url(
            tenant_id=params.tenant,
            client_id=params.client_id,
            redirect_url=params.redirect_url,
        )
        self.soar_action.result.add_link("Browse to this authorization link", url)

    def _get_authorization_url(
        self,
        tenant_id: str,
        client_id: str,
        redirect_url: str,
    ) -> str:
        """Constructs the authorization URL for OAuth 2.0 flow.

        Args:
            redirect_url (str): The redirect URL for the authorization request.

        Returns:
            str: The authorization URL.
        """
        root_url = constants.ENDPOINTS["authorize_url"].format(tenant=tenant_id)
        scopes = " ".join(constants.OAUTH_SCOPE)
        params = {
            "client_id": client_id,
            "redirect_uri": f"{redirect_url}",
            "response_type": "code",
            "response_mode": "query",
            "scope": f"{scopes}",
        }
        url = f"{root_url}?{urlencode(params)}"

        return url


def main() -> NoReturn:
    action: GetAuthorization = GetAuthorization()
    action.run()


if __name__ == "__main__":
    main()
