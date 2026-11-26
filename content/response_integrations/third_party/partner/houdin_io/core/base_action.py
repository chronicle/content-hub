from __future__ import annotations

from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from .houdin import HoudinManager
from .houdin_constants import INTEGRATION_NAME


class HoudinAction(Action, ABC):
    """Base of the three actions: the instance configuration becomes the HoudinManager."""

    def _init_api_clients(self) -> HoudinManager:
        api_root: str = extract_configuration_param(self.soar_action, INTEGRATION_NAME, param_name="API Root")
        api_key: str = extract_configuration_param(self.soar_action, INTEGRATION_NAME, param_name="API Key")
        verify_ssl: bool = extract_configuration_param(
            self.soar_action,
            INTEGRATION_NAME,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
        )
        return HoudinManager(api_key, api_root, verify_ssl)

    @property
    def result_value(self) -> bool | str:
        """The result value; a run that ends IN_PROGRESS hands its state to the next run through it."""
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool | str) -> None:
        self._result_value = value
