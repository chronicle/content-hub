from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    from ..core.constants import (
        ALERT_EVENTS_MAX_FETCH,
        GET_ALERT_EVENTS_SCRIPT_NAME,
        INTEGRATION_NAME,
        PARAM_ACCESS_KEY,
        PARAM_ACCESS_KEY_ID,
        PARAM_API_ROOT,
    )
    from ..core.utils import format_user_facing_error, iter_current_vega_ids
    from ..core.VegaManager import VegaManager

    siemplify.script_name = GET_ALERT_EVENTS_SCRIPT_NAME
    alert_id = siemplify.extract_action_param("Alert ID", default_value="", print_value=True)
    limit = siemplify.extract_action_param("Limit", default_value="100")
    offset = siemplify.extract_action_param("Offset", default_value="0")
    candidates = []
    if str(alert_id).strip():
        candidates.append(str(alert_id).strip())
    else:
        candidates.extend(iter_current_vega_ids(siemplify))
    try:
        if not candidates:
            raise ValueError(
                "Alert ID is required. Enter the Vega alert UUID, or run this action on a Vega Alert case."
            )
        manager = VegaManager(
            api_root=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_API_ROOT),
            access_key_id=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY_ID),
            access_key=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY),
            logger_instance=siemplify.LOGGER,
        )
        page_size = int(limit or 100)
        all_events = []
        used_id = candidates[0]
        last_error = None
        fetched = False
        for candidate in candidates:
            try:
                all_events = manager.get_all_alert_events(
                    candidate,
                    page_size=page_size,
                    max_records=ALERT_EVENTS_MAX_FETCH,
                )
            except Exception as error:
                last_error = error
                continue
            fetched = True
            used_id = candidate
            break
        if not fetched:
            raise last_error or ValueError("Unable to fetch Vega alert events.")
        result = {
            "total": len(all_events),
            "limit": page_size,
            "offset": int(offset or 0),
            "alert_id": used_id,
            "results": all_events,
        }
        siemplify.result.add_result_json(result)
        siemplify.end(
            f"Fetched {len(all_events)} Vega alert event(s) for {used_id}.",
            True,
            EXECUTION_STATE_COMPLETED,
        )
    except Exception as error:
        message = f'Error executing action "Get Alert Events". Reason: {format_user_facing_error(error)}'
        siemplify.LOGGER.error(message)
        siemplify.end(message, False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
