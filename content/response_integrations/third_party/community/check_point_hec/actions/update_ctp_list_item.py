from ..core.base_action import BaseAction
from ..core.constants import UPDATE_CTP_LIST_ITEM_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully updated Click Time Protection List Item!"
ERROR_MESSAGE: str = "Failed updating Click Time Protection List Item!"


class UpdateCTPListItem(BaseAction):

    def __init__(self) -> None:
        super().__init__(UPDATE_CTP_LIST_ITEM_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.item_id = self.soar_action.extract_action_param(
            param_name="Item ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )
        self.params.list_id = self.soar_action.extract_action_param(
            param_name="List ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )
        self.params.list_item_name = self.soar_action.extract_action_param(
            param_name="List Item Name",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )
        self.params.created_by = self.soar_action.extract_action_param(
            param_name="Created By",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )

    def _perform_action(self, _=None) -> None:
        item_id = self.params.item_id
        list_id = self.params.list_id
        list_item_name = self.params.list_item_name
        created_by = self.params.created_by

        list_item = {
            "listId": list_id,
            "listItemName": list_item_name,
            "createdBy": created_by
        }
        self.json_results = self.api_client.update_ctp_list_item(item_id, list_item=list_item)


def main() -> None:
    UpdateCTPListItem().run()


if __name__ == "__main__":
    main()
