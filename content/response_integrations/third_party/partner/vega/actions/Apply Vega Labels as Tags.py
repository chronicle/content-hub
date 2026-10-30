from __future__ import annotations

from typing import Any

from TIPCommon.base.action import Action

from ..core.case_events import case_events
from ..core.constants import APPLY_VEGA_LABELS_SCRIPT_NAME
from ..core.mapping import pending_case_tags, tags_from_events


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
        events = case_events(soar)
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
