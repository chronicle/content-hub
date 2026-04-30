from ..core.base_action import BaseAction
from ..core.constants import GET_CTP_LISTS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Click Time Protection Lists!"
ERROR_MESSAGE: str = "Failed getting Click Time Protection Lists!"


class GetCTPLists(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_CTP_LISTS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.json_results = self.api_client.get_ctp_lists()


def main() -> None:
    GetCTPLists().run()


if __name__ == "__main__":
    main()
