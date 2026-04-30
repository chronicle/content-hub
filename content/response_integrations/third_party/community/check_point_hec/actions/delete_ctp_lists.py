from ..core.base_action import BaseAction
from ..core.constants import DELETE_CTP_LISTS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Click Time Protection Lists!"
ERROR_MESSAGE: str = "Failed deleting Click Time Protection Lists!"


class DeleteCTPLists(BaseAction):

    def __init__(self) -> None:
        super().__init__(DELETE_CTP_LISTS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.json_results = self.api_client.delete_ctp_lists()


def main() -> None:
    DeleteCTPLists().run()


if __name__ == "__main__":
    main()
