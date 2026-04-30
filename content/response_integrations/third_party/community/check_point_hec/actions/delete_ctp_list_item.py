from ..core.base_action import BaseAction
from ..core.constants import DELETE_CTP_LIST_ITEM_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Click Time Protection List Item!"
ERROR_MESSAGE: str = "Failed deleting Click Time Protection List Item!"


class DeleteCTPListItem(BaseAction):

    def __init__(self) -> None:
        super().__init__(DELETE_CTP_LIST_ITEM_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.item_id = self.soar_action.extract_action_param(
            param_name="Item ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )

    def _perform_action(self, _=None) -> None:
        item_id = self.params.item_id

        self.api_client.delete_ctp_list_item(item_id)


def main() -> None:
    DeleteCTPListItem().run()


if __name__ == "__main__":
    main()
