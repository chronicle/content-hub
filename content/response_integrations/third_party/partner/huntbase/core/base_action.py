from __future__ import annotations

from TIPCommon.base.action import Action

from .huntbase_manager import HuntbaseManager
from .utils import create_manager


class HuntbaseAction(Action):
    """Common setup for Huntbase actions: one API client built from the integration config."""

    def _init_api_clients(self) -> HuntbaseManager:
        return create_manager(self.soar_action, self.logger)

    @Action.result_value.setter
    def result_value(self, value: bool | str) -> None:
        """Allow string result values: async actions pass their state in it."""
        self._result_value = value

    @property
    def manager(self) -> HuntbaseManager:
        return self.api_client

    def _send_entities_to_update(self) -> None:
        """Send ``entities_to_update`` from inside ``_perform_action``.

        Action only sends ``entities_to_update`` from its per-entity loop, and these
        actions look entities up in batches. Sending them here, before Action adds the
        entity insights, keeps the update in step with the platform's copy of the
        entities (updating after the insights were added fails with a server error)
        and lets Action's normal error handling cover a failed update.
        """
        if self.entities_to_update:
            self.logger.info("Updating entities")
            self.soar_action.update_entities(self.entities_to_update)

    def _finalize(self) -> None:
        if self.api_client is not None:
            self.api_client.close()
