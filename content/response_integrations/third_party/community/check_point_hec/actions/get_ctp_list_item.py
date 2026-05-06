"""Get CTP List Item action – retrieves a single CTP list item by its item ID."""
from ..core.base_action import BaseAction
from ..core.constants import GET_CTP_LIST_ITEM_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Click Time Protection List Item!"
ERROR_MESSAGE: str = "Failed getting Click Time Protection List Item!"


class GetCTPListItem(BaseAction):
    """Retrieve a single CTP exception list item identified by its *Item ID*."""

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_CTP_LIST_ITEM_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract the mandatory *Item ID* parameter."""
        self.params.item_id = self.soar_action.extract_action_param(
            param_name="Item ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )

    def _perform_action(self, _=None) -> None:
        """Call the CTP API to fetch the item and store it in ``json_results``."""
        item_id = self.params.item_id
        self.json_results = self.api_client.get_ctp_list_item(item_id)


def main() -> None:
    GetCTPListItem().run()


if __name__ == "__main__":
    main()
