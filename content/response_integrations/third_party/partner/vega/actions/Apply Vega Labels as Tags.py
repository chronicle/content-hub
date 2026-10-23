from __future__ import annotations

from typing import Any

from TIPCommon.base.action import Action

from ..core.constants import APPLY_VEGA_LABELS_SCRIPT_NAME
from ..core.mapping import pending_case_tags, tags_from_events


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


def _case_events(siemplify: Any) -> list[Any]:
    events: list[Any] = []
    for alert in _case_alerts(siemplify):
        events.extend(_alert_events(alert))
    return events


def _tag_name(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, dict):
        return str(item.get("name") or item.get("Name") or "").strip()
    return str(getattr(item, "name", None) or item).strip()


def _existing_case_tags(siemplify: Any) -> list[str]:
    blobs: list[Any] = []
    case = getattr(siemplify, "case", None)
    if case is not None:
        blobs.append(getattr(case, "tags", None))
        extra = getattr(case, "additional_properties", None)
        if isinstance(extra, dict):
            blobs.append(extra.get("tags") or extra.get("Tags"))
    blobs.append(getattr(siemplify, "tags", None))
    names: list[str] = []
    for blob in blobs:
        if not blob:
            continue
        if isinstance(blob, str):
            items: list[Any] = [part.strip() for part in blob.split(",") if part.strip()]
        elif isinstance(blob, list):
            items = blob
        else:
            items = [blob]
        for item in items:
            name = _tag_name(item)
            if name:
                names.append(name)
    return names


class ApplyVegaLabelsAsTags(Action):
    """Apply Vega label names from case events as SecOps case tags."""

    def __init__(self) -> None:
        super().__init__(APPLY_VEGA_LABELS_SCRIPT_NAME)

    def _init_api_clients(self) -> None:
        """No remote API client."""

    def _perform_action(self, _=None) -> None:
        soar = self.soar_action
        events = _case_events(soar)
        names = pending_case_tags(tags_from_events(events), _existing_case_tags(soar))
        self.logger.info(
            "Found %s event(s) and %s new Vega label tag(s) on this case.",
            len(events),
            len(names),
        )
        if not names:
            self.result_value = False
            self.output_message = "No new Vega label names were found on this case."
            return
        added: list[str] = []
        for name in names:
            self._add_tag_to_case(name)
            added.append(name)
        self.json_results = {"tags": added}
        self.output_message = f"Created and assigned {len(added)} tag(s): {', '.join(added)}."


def main() -> None:
    ApplyVegaLabelsAsTags().run()


if __name__ == "__main__":
    main()
