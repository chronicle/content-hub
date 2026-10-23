"""Shared TIPCommon Action helpers for Vega scripts."""

from __future__ import annotations

from TIPCommon.base.action import Action

from .constants import INTEGRATION_NAME, PARAM_ACCESS_KEY, PARAM_ACCESS_KEY_ID, PARAM_API_ROOT
from .VegaManager import VegaManager


class VegaApiAction(Action):
    """Action that talks to Vega GraphQL via VegaManager."""

    def _init_api_clients(self) -> VegaManager:
        soar = self.soar_action
        return VegaManager(
            api_root=soar.extract_configuration_param(INTEGRATION_NAME, PARAM_API_ROOT),
            access_key_id=soar.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY_ID),
            access_key=soar.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY),
            logger_instance=soar.LOGGER,
        )
