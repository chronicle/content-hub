from ..core.base_action import BaseAction
from ..core.constants import DELETE_CTP_LIST_ITEMS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Click Time Protection List Items!"
ERROR_MESSAGE: str = "Failed deleting Click Time Protection List Items!"


class DeleteCTPListItems(BaseAction):

    def __init__(self) -> None:
        super().__init__(DELETE_CTP_LIST_ITEMS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.list_item_ids = self.soar_action.extract_action_param(
            param_name="List Item IDs",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )

    def _perform_action(self, _=None) -> None:
        list_item_ids = self.params.list_item_ids.split(",")

        self.json_results = self.api_client.delete_ctp_list_items(list_item_ids)


def main() -> None:
    DeleteCTPListItems().run()


if __name__ == "__main__":
    main()
