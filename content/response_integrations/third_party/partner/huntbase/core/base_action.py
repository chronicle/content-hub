from __future__ import annotations

from TIPCommon.base.action import Action

from .huntbase_manager import HuntbaseManager
from .utils import create_manager


class HuntbaseAction(Action):
    """Common setup for Huntbase actions: one API client built from the integration config."""

    def _init_api_clients(self) -> HuntbaseManager:
        return create_manager(self.soar_action, self.logger)

    @Action.result_value.setter
    def result_value(self, value: object) -> None:
        """Allow string result values: async actions pass their state in it."""
        self._result_value = value

    @property
    def manager(self) -> HuntbaseManager:
        return self.api_client
