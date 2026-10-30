"""Read events off the current SOAR case."""

from __future__ import annotations

from typing import Any


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


def _case_alerts(siemplify: Any) -> list[Any]:
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
                except Exception as error:
                    siemplify.LOGGER.warn(
                        "Failed to load case.%s while collecting alerts: %s",
                        attr,
                        error,
                    )
                    group = None
            if isinstance(group, list) and group:
                for alert in group:
                    _add(alert)
                break
    _add(getattr(siemplify, "current_alert", None))
    return alerts


def case_events(siemplify: Any) -> list[Any]:
    """Return security events from the alerts on this SOAR case."""
    events: list[Any] = []
    for alert in _case_alerts(siemplify):
        events.extend(_alert_events(alert))
    return events
