from ..core.base_action import BaseAction
from ..core.constants import GET_CTP_LIST_ITEMS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Click Time Protection List Items!"
ERROR_MESSAGE: str = "Failed getting Click Time Protection List Items!"


class GetCTPListItems(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_CTP_LIST_ITEMS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.json_results = self.api_client.get_ctp_list_items()


def main() -> None:
    GetCTPListItems().run()


if __name__ == "__main__":
    main()
