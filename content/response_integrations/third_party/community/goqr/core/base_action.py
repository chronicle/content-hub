from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from TIPCommon.base.action import Action

from ..core.api.api_client import ApiParameters, GOQRApiClient
from ..core.auth import SessionAuthenticationParameters, build_auth_params

if TYPE_CHECKING:
    pass


class GOQRBaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> GOQRApiClient:
        """Prepare API client"""
        auth_params: SessionAuthenticationParameters = build_auth_params(self.soar_action)
        session = requests.Session()
        session.verify = auth_params.verify_ssl

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
        )

        return GOQRApiClient(
            authenticated_session=session,
            configuration=api_params,
            logger=self.logger,
        )

    def save_temp_file(self, filename: str, content: bytes | str) -> Path:
        """Saves content to file in temporary directory

        Args:
            filename (str): File name (Base name)
            content (bytes | str): File content

        Returns:
            str: Path to temporary file
        """
        temp_folder = Path(self.soar_action.get_temp_folder_path())
        file_path = temp_folder / filename
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(file_path, mode) as f:
            f.write(content)

        return file_path

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
