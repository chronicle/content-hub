"""Shared TIPCommon Action helpers for Vega scripts."""

from __future__ import annotations

from typing import Any

from TIPCommon.base.action import Action

from .constants import INTEGRATION_NAME, PARAM_ACCESS_KEY, PARAM_ACCESS_KEY_ID, PARAM_API_ROOT
from .VegaManager import VegaManager


def current_vega_id(siemplify: Any) -> str:
    """Return vega_id from the current alert's first event, if present."""
    try:
        alert = siemplify.current_alert
        events = getattr(alert, "security_events", None) or getattr(alert, "events", None) or []
        for event in events:
            additional = getattr(event, "additional_properties", None) or {}
            value = additional.get("vega_id") if isinstance(additional, dict) else None
            if value:
                return str(value)
    except Exception:
        return ""
    return ""


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
