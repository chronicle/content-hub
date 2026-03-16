from __future__ import annotations

from TIPCommon.base.action.data_models import ExecutionState

from ..core.base_action import SignalSciencesAction

SCRIPT_NAME = "Ping"


class PingAction(SignalSciencesAction):
    def __init__(self):
        super().__init__(SCRIPT_NAME)

    def _perform_action(self, _=None) -> None:
        try:
            self.api_client.test_connectivity()
            self.output_message = (
                "Successfully connected to the Signal Sciences server with the provided "
                "connection parameters!"
            )
            self.result_value = True
        except Exception as e:
            self.output_message = f'Error executing action: "{SCRIPT_NAME}". Reason: {e}'
            self.logger.error(self.output_message)
            self.result_value = False
            self.execution_state = ExecutionState.FAILED


def main():
    PingAction().run()


if __name__ == "__main__":
    main()
