from __future__ import annotations

import os.path
from abc import ABC
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action

from ..core.api.api_client import ApiParameters, SampleApiClient
from ..core.auth import AuthenticatedSession, SessionAuthenticationParameters, build_auth_params

if TYPE_CHECKING:
    import requests


class SampleAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> SampleApiClient:
        """Prepare API client"""
        auth_params = build_auth_params(self.soar_action)
        authenticator: AuthenticatedSession = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            api_root=auth_params.api_root,
            password=auth_params.password,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: requests.Session = authenticator.session

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
        )

        return SampleApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )

    def save_temp_file(self, filename: str, content: str) -> str:
        """Saves content to file in temporary directory

        Args:
            filename (str): File name (Base name)
            content (str): File content

        Returns:
            str: Path to temporary file
        """
        temp_folder = self.soar_action.get_temp_folder_path()
        file_path = os.path.join(temp_folder, filename)
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
