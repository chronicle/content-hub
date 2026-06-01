"""Get CTP Lists action – retrieves all Click Time Protection exception lists."""
from ..core.base_action import BaseAction
from ..core.constants import GET_CTP_LISTS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Click Time Protection Lists!"
ERROR_MESSAGE: str = "Failed getting Click Time Protection Lists!"


class GetCTPLists(BaseAction):
    """Retrieve all CTP exception lists in the current scope.

    Takes no additional parameters.  The full list of CTP lists is stored in
    ``json_results``.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_CTP_LISTS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        """Call the CTP API to fetch all exception lists and store them in ``json_results``."""
        self.json_results = self.api_client.get_ctp_lists()


def main() -> None:
    GetCTPLists().run()


if __name__ == "__main__":
    main()
