"""Create CTP List Item action – adds an item to a Click Time Protection exception list."""
from ..core.base_action import BaseAction
from ..core.constants import CREATE_CTP_LIST_ITEM_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully created Click Time Protection List Item!"
ERROR_MESSAGE: str = "Failed creating Click Time Protection List Item!"


class CreateCTPListItem(BaseAction):
    """Add a new item to a Click Time Protection (CTP) exception list.

    The *Exception List Type* parameter determines which list receives the item:

    * ``allow-list``  (ID ``0``) – URLs that are always permitted.
    * ``block-list``  (ID ``1``) – URLs that are always blocked.
    * ``ignore-list`` (ID ``2``) – URLs excluded from CTP scanning.
    """

    def __init__(self) -> None:
        """Initialize the action with its script name and output messages."""
        super().__init__(CREATE_CTP_LIST_ITEM_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract *Exception List Type*, *List Item Name*, and *Created By* parameters."""
        self.params.list_id = self.soar_action.extract_action_param(
            param_name="Exception List Type",
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
        """Map the list type name to its numeric ID and call the CTP API to create the item."""
        list_id = self.params.list_id
        list_name_to_id = {"allow-list": "0", "block-list": "1", "ignore-list": "2"}

        list_item_name = self.params.list_item_name
        created_by = self.params.created_by

        list_item = {
            "listId": list_name_to_id[list_id],
            "listItemName": list_item_name,
            "createdBy": created_by
        }
        self.json_results = self.api_client.create_ctp_list_item(list_item=list_item)


def main() -> None:
    CreateCTPListItem().run()


if __name__ == "__main__":
    main()
