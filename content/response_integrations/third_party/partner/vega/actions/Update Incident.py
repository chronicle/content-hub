from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def _current_vega_id(siemplify: SiemplifyAction) -> str:
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
def main() -> None:
    siemplify = SiemplifyAction()
    from ..core.constants import (
        INTEGRATION_NAME,
        PARAM_ACCESS_KEY,
        PARAM_ACCESS_KEY_ID,
        PARAM_API_ROOT,
        UPDATE_INCIDENT_SCRIPT_NAME,
    )
    from ..core.utils import format_user_facing_error, parse_csv_list, to_graphql_enum
    from ..core.VegaManager import VegaManager

    siemplify.script_name = UPDATE_INCIDENT_SCRIPT_NAME
    incident_ids = parse_csv_list(siemplify.extract_action_param("Incident IDs", default_value=""))
    if not incident_ids:
        current = _current_vega_id(siemplify)
        if current:
            incident_ids = [current]
    payload = {"incidentIds": incident_ids}
    user_status = str(siemplify.extract_action_param("User Status", default_value="") or "").strip()
    severity = str(siemplify.extract_action_param("Severity", default_value="") or "").strip()
    verdict = str(siemplify.extract_action_param("Verdict", default_value="") or "").strip()
    reasoning = str(siemplify.extract_action_param("Verdict Reasoning", default_value="") or "").strip()
    comment = str(siemplify.extract_action_param("Comment", default_value="") or "").strip()
    emails = parse_csv_list(siemplify.extract_action_param("Assignee Emails", default_value=""))
    if user_status:
        payload["userStatus"] = to_graphql_enum(user_status)
    if severity:
        payload["severity"] = severity
    if verdict or reasoning:
        payload["verdict"] = {"value": verdict or "NA", "reasoning": reasoning}
    if comment:
        payload["comment"] = comment
    if emails:
        payload["assigneeEmails"] = emails
    try:
        if not incident_ids:
            raise ValueError("Incident IDs are required.")
        manager = VegaManager(
            api_root=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_API_ROOT),
            access_key_id=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY_ID),
            access_key=siemplify.extract_configuration_param(INTEGRATION_NAME, PARAM_ACCESS_KEY),
            logger_instance=siemplify.LOGGER,
        )
        result = manager.update_incidents(payload)
        siemplify.result.add_result_json(result)
        siemplify.end(
            f"Updated {len(incident_ids)} Vega incident(s).",
            True,
            EXECUTION_STATE_COMPLETED,
        )
    except Exception as error:
        message = f'Error executing action "Update Incident". Reason: {format_user_facing_error(error)}'
        siemplify.LOGGER.error(message)
        siemplify.end(message, False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
