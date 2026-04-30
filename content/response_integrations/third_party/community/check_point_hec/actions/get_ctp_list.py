from ..core.base_action import BaseAction
from ..core.constants import GET_CTP_LIST_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Click Time Protection List!"
ERROR_MESSAGE: str = "Failed getting Click Time Protection List!"


class GetCTPList(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_CTP_LIST_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.list_id = self.soar_action.extract_action_param(
            param_name="List ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )

    def _perform_action(self, _=None) -> None:
        list_id = self.params.list_id
        self.json_results = self.api_client.get_ctp_list(list_id)


def main() -> None:
    GetCTPList().run()


if __name__ == "__main__":
    main()
