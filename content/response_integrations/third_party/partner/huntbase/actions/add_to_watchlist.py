from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core import constants
from ..core.base_action import HuntbaseAction
from ..core.utils import WATCHLIST_ENTITY_TYPES, entity_value

if TYPE_CHECKING:
    from typing import NoReturn


class AddToWatchlist(HuntbaseAction):
    """Add the case's IOC entities to a Huntbase watch list."""

    def __init__(self) -> None:
        super().__init__(constants.ADD_TO_WATCHLIST_SCRIPT_NAME)
        self.error_output_message = f'Error executing action "{constants.ADD_TO_WATCHLIST_SCRIPT_NAME}"'

    def _extract_action_parameters(self) -> None:
        self.params.watchlist = extract_action_param(
            self.soar_action, param_name="Watchlist", is_mandatory=True, print_value=True
        )
        self.params.additional_values = extract_action_param(
            self.soar_action, param_name="Additional Values", print_value=True
        )

    def _perform_action(self, _: object) -> None:
        values = [
            entity_value(entity)
            for entity in self.soar_action.target_entities
            if entity.entity_type in WATCHLIST_ENTITY_TYPES
        ]
        values += string_to_multi_value(self.params.additional_values)
        values = list(dict.fromkeys(values))
        if not values:
            msg = "No IP, domain, URL or hash entities in scope and no Additional Values were given."
            raise ValueError(msg)

        watchlist = self.manager.find_watchlist(self.params.watchlist)
        response = self.manager.add_watchlist_values(watchlist.watchlist_id, values)
        added = response.get("added", 0)
        existing = response.get("existing", 0)
        rejected = response.get("rejected") or []
        self.json_results = {
            "watchlist_id": watchlist.watchlist_id,
            "watchlist_name": watchlist.name,
            "submitted": values,
            "added": added,
            "existing": existing,
            "rejected": rejected,
        }
        lines = [
            f"Successfully submitted {len(values)} value(s) to the Huntbase watch list '{watchlist.name}': "
            f"{added} added, {existing} already present."
        ]
        if rejected:
            reasons = ", ".join(f"{r.get('input')} ({r.get('reason')})" for r in rejected if isinstance(r, dict))
            lines.append(f"Rejected: {reasons}")
        self.output_message = "\n".join(lines)
        self.result_value = bool(added or existing)


def main() -> NoReturn:
    AddToWatchlist().run()


if __name__ == "__main__":
    main()
