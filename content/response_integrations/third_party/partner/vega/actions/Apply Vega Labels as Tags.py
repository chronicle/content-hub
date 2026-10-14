from __future__ import annotations

from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def _alert_events(alert: Any) -> list[Any]:
    if alert is None:
        return []
    return list(getattr(alert, "security_events", None) or getattr(alert, "events", None) or [])


def _alert_key(alert: Any) -> object:
    return (
        getattr(alert, "identifier", None)
        or getattr(alert, "alert_identifier", None)
        or getattr(alert, "ticket_id", None)
        or id(alert)
    )


def _case_alerts(siemplify: SiemplifyAction) -> list[Any]:
    alerts: list[Any] = []
    seen: set[object] = set()

    def _add(alert: Any) -> None:
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


def _case_events(siemplify: SiemplifyAction) -> list[Any]:
    events = []
    for alert in _case_alerts(siemplify):
        events.extend(_alert_events(alert))
    return events


def _tag_name(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, dict):
        return str(item.get("name") or item.get("Name") or "").strip()
    return str(getattr(item, "name", None) or item).strip()


def _existing_case_tags(siemplify: SiemplifyAction) -> list[str]:
    blobs = []
    case = getattr(siemplify, "case", None)
    if case is not None:
        blobs.append(getattr(case, "tags", None))
        extra = getattr(case, "additional_properties", None)
        if isinstance(extra, dict):
            blobs.append(extra.get("tags") or extra.get("Tags"))
    blobs.append(getattr(siemplify, "tags", None))
    names = []
    for blob in blobs:
        if not blob:
            continue
        if isinstance(blob, str):
            items = [part.strip() for part in blob.split(",") if part.strip()]
        elif isinstance(blob, list):
            items = blob
        else:
            items = [blob]
        for item in items:
            name = _tag_name(item)
            if name:
                names.append(name)
    return names


def _add_case_tag(siemplify: SiemplifyAction, name: str) -> None:
    case = getattr(siemplify, "case", None)
    case_id = getattr(case, "identifier", None) if case is not None else getattr(siemplify, "case_id", None)
    try:
        if case_id:
            siemplify.add_tag(tag=name, case_id=case_id, alert_identifier=None)
        else:
            siemplify.add_tag(tag=name)
    except TypeError:
        siemplify.add_tag(name)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    from ..core.constants import APPLY_VEGA_LABELS_SCRIPT_NAME
    from ..core.mapping import pending_case_tags, tags_from_events
    from ..core.utils import format_user_facing_error

    siemplify.script_name = APPLY_VEGA_LABELS_SCRIPT_NAME
    try:
        events = _case_events(siemplify)
        names = pending_case_tags(tags_from_events(events), _existing_case_tags(siemplify))
        siemplify.LOGGER.info(
            "Found %s event(s) and %s new Vega label tag(s) on this case.",
            len(events),
            len(names),
        )
        if not names:
            siemplify.end(
                "No new Vega label names were found on this case.",
                False,
                EXECUTION_STATE_COMPLETED,
            )
            return
        added = []
        for name in names:
            _add_case_tag(siemplify, name)
            added.append(name)
        siemplify.result.add_result_json({"tags": added})
        siemplify.end(
            f"Created and assigned {len(added)} tag(s): {', '.join(added)}.",
            True,
            EXECUTION_STATE_COMPLETED,
        )
    except Exception as error:
        message = f'Error executing action "Apply Vega Labels as Tags". Reason: {format_user_facing_error(error)}'
        siemplify.LOGGER.error(message)
        siemplify.end(message, False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
