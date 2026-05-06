"""Get CTP List Items action – retrieves all items across all CTP exception lists."""
from ..core.base_action import BaseAction
from ..core.constants import GET_CTP_LIST_ITEMS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Click Time Protection List Items!"
ERROR_MESSAGE: str = "Failed getting Click Time Protection List Items!"


class GetCTPListItems(BaseAction):
    """Retrieve all CTP exception list items in the current scope.

    Takes no additional parameters.  The full item list is stored in
    ``json_results``.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_CTP_LIST_ITEMS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        """Call the CTP API to fetch all list items and store them in ``json_results``."""
        self.json_results = self.api_client.get_ctp_list_items()


def main() -> None:
    GetCTPListItems().run()


if __name__ == "__main__":
    main()
