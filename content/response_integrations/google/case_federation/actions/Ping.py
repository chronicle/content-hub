from __future__ import annotations
from typing import NoReturn

from TIPCommon.base.action import Action

from ..core.constants import PING_SCRIPT_NAME


class Ping(Action):

    def _extract_parameters(self) -> None:
        pass

    def _validate_params(self) -> None:
        pass

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _=None) -> None:
        pass


def main() -> NoReturn:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
