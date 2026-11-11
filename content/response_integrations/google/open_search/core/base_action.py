from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from open_search.core.auth import build_auth_params
from open_search.core.os_client import OpenSearchManager
from TIPCommon.base.action import Action

if TYPE_CHECKING:
    from open_search.core.data_models import IntegrationParameters


class BaseAction(Action, ABC):
    """Base action class for OpenSearch integration."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _init_api_clients(self) -> OpenSearchManager:
        """
        Initializes the OpenSearchManager.
        This method is called by the Action's run method and its return value
        is used to set the api_client property.
        """
        integration_parameters: IntegrationParameters = build_auth_params(
            self.soar_action
        )
        return OpenSearchManager(
            integration_parameters=integration_parameters,
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
