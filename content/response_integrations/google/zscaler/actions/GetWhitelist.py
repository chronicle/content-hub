from __future__ import annotations

from TIPCommon.transformation import construct_csv

from zscaler.core.base_action import ZscalerBaseAction
from zscaler.core.constants import GET_WHITELIST_SCRIPT_NAME


class GetWhitelistAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(GET_WHITELIST_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: str = ""

    def _perform_action(self, _=None) -> None:
        """Perform the action."""
        whitelist_dict = self.api_client.get_whitelist_items()
        whitelist = whitelist_dict.get("whitelistUrls")

        if whitelist:
            self.output_message = f"Found {len(whitelist)} Unblocked URLs"
            self.result_value = ", ".join(whitelist)

            csv_output = construct_csv([{"Unblocked URL": url} for url in whitelist])
            self.soar_action.result.add_data_table("Whitelist Urls", csv_output)
            self.soar_action.result.add_result_json(whitelist_dict)
        else:
            self.output_message = "Found 0 Unblocked URLs"
            self.result_value = " "
            self.soar_action.result.add_result_json({})


def main() -> None:
    GetWhitelistAction().run()


if __name__ == "__main__":
    main()
