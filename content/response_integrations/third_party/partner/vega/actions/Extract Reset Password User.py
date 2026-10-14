from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def _alert_events(alert) -> list:
    if alert is None:
        return []
    return list(getattr(alert, "security_events", None) or getattr(alert, "events", None) or [])


def _alert_key(alert) -> object:
    return (
        getattr(alert, "identifier", None)
        or getattr(alert, "alert_identifier", None)
        or getattr(alert, "ticket_id", None)
        or id(alert)
    )


def _case_alerts(siemplify) -> list:
    alerts = []
    seen = set()

    def _add(alert) -> None:
        if alert is None:
            return
        marker = _alert_key(alert)
        if marker in seen:
            return
        seen.add(marker)
        alerts.append(alert)

    case = getattr(siemplify, "case", None)
    if case is not None:
        for attr in ("alerts", "open_alerts", "cyber_alerts"):
            group = getattr(case, attr, None)
            if callable(group):
                try:
                    group = group()
                except Exception:
                    group = None
            if isinstance(group, list) and group:
                for alert in group:
                    _add(alert)
                break
    _add(getattr(siemplify, "current_alert", None))
    return alerts


def _case_events(siemplify) -> list:
    events = []
    for alert in _case_alerts(siemplify):
        events.extend(_alert_events(alert))
    return events


def _event_payload(event) -> dict:
    if isinstance(event, dict):
        payload = dict(event)
    else:
        payload = {}
        extra = getattr(event, "additional_properties", None)
        if isinstance(extra, dict):
            payload.update(extra)
        for key in (
            "recommended_actions",
            "recommendedActions",
            "vega_reset_password_user",
            "details",
            "user",
        ):
            value = getattr(event, key, None)
            if value not in (None, ""):
                payload.setdefault(key, value)
    extra = payload.get("additional_properties") or payload.get("additionalProperties")
    if isinstance(extra, dict):
        merged = dict(extra)
        merged.update(payload)
        return merged
    return payload


@output_handler
def main():
    siemplify = SiemplifyAction()
    from ..core.constants import EXTRACT_RESET_PASSWORD_USER_SCRIPT_NAME
    from ..core.mapping import reset_password_users_from_payload
    from ..core.utils import format_user_facing_error

    siemplify.script_name = EXTRACT_RESET_PASSWORD_USER_SCRIPT_NAME
    try:
        users: list[str] = []
        for event in _case_events(siemplify):
            for user in reset_password_users_from_payload(_event_payload(event)):
                if user not in users:
                    users.append(user)
        result = {"user_id": ",".join(users), "users": users}
        siemplify.result.add_result_json(result)
        if not users:
            siemplify.end(
                "No reset_user_password target email was found on this case.",
                False,
                EXECUTION_STATE_COMPLETED,
            )
            return
        siemplify.end(
            f"Found Okta reset target(s): {', '.join(users)}.",
            True,
            EXECUTION_STATE_COMPLETED,
        )
    except Exception as error:
        message = f'Error executing action "Extract Reset Password User". Reason: {format_user_facing_error(error)}'
        siemplify.LOGGER.error(message)
        siemplify.end(message, False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
