from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def _current_vega_id(siemplify):
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


@output_handler
def main():
    siemplify = SiemplifyAction()
    from ..core.constants import (
        GET_INCIDENT_TIMELINE_SCRIPT_NAME,
        INTEGRATION_NAME,
        PARAM_ACCESS_KEY,
        PARAM_ACCESS_KEY_ID,
        PARAM_API_ROOT,
    )
    from ..core.utils import format_user_facing_error
    from ..core.VegaManager import VegaManager

    siemplify.script_name = GET_INCIDENT_TIMELINE_SCRIPT_NAME
    incident_id = siemplify.extract_action_param("Incident ID", default_value="")
    if not str(incident_id).strip():
        incident_id = _current_vega_id(siemplify)
    try:
        if not str(incident_id).strip():
            raise ValueError("Incident ID is required.")
        manager = VegaManager(
            api_root=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_API_ROOT),
            access_key_id=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY_ID),
            access_key=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY),
            logger_instance=siemplify.LOGGER,
        )
        events = manager.get_all_incident_timeline(str(incident_id).strip())
        result = {
            "events": events,
            "total": len(events),
            "limit": len(events),
            "offset": 0,
        }
        siemplify.result.add_result_json(result)
        siemplify.end(
            f"Fetched {len(events)} timeline event(s) for Vega incident {incident_id}.",
            True,
            EXECUTION_STATE_COMPLETED,
        )
    except Exception as error:
        message = f'Error executing action "Get Incident Timeline". Reason: {format_user_facing_error(error)}'
        siemplify.LOGGER.error(message)
        siemplify.end(message, False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
