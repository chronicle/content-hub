from __future__ import annotations

from TIPCommon.base.action import Action
from scc_enterprise.core import SCCEnterpriseConsts


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Successfully tested {SCCEnterpriseConsts.INTEGRATION_NAME}."
        )
        self.error_output_message = (
            f"Failed to test {SCCEnterpriseConsts.INTEGRATION_NAME}"
        )

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _=None) -> None:
        pass


def main() -> None:
    Ping(SCCEnterpriseConsts.PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
