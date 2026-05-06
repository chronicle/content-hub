"""Delete CTP Lists action – removes all Click Time Protection exception lists."""
from ..core.base_action import BaseAction
from ..core.constants import DELETE_CTP_LISTS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Click Time Protection Lists!"
ERROR_MESSAGE: str = "Failed deleting Click Time Protection Lists!"


class DeleteCTPLists(BaseAction):
    """Delete all CTP exception lists via the CTP exceptions API.

    This action takes no additional parameters – it removes every CTP list
    in the current scope.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(DELETE_CTP_LISTS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        """Call the CTP API to delete all exception lists."""
        self.json_results = self.api_client.delete_ctp_lists()


def main() -> None:
    DeleteCTPLists().run()


if __name__ == "__main__":
    main()
